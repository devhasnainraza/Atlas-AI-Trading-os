"""ORM table definitions for the identity core (T022; data-model.md).

Alembic's ``env.py`` imports this module so ``--autogenerate`` sees the schema; the
repositories (T024) import the classes to query against. Nothing above the repository layer
should import from here — services speak to repository Protocols, not to tables.

Conventions, all from data-model.md / Spec 00:

* **UUIDv7 PKs, client-side** (:class:`UUIDPrimaryKeyMixin`) — the id exists before the
  INSERT so an event or audit row can reference it without a round trip.
* **Enums are VARCHAR + CHECK**, not native Postgres enums. Adding a value to a native enum
  inside a transaction is restricted and awkward to roll back; a CHECK constraint is a
  plain DDL swap, and the constraint name (``ck_<table>_<column>``) makes the violation
  readable in a pg error.
* **citext for email/username** — case-folding is the canonical-identity rule (FR-001), and
  doing it in the column means no code path can forget to normalize before comparing.
* **Hashes are bytea** where the producer is a digest (SHA-256 of a token), text where the
  producer is a hex/base64 string. Matching the storage to the producer avoids a decode
  step that could silently truncate.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, CITEXT, INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from atlas_api.modules.auth.domain.models import SessionStatus, UserStatus
from atlas_core.db import Base, TimestampMixin, UUIDPrimaryKeyMixin


def _in(values: tuple[str, ...]) -> str:
    """Render a SQL ``IN (...)`` list from a Python tuple of literals.

    The enum value sets are declared once (domain enums where T023 defines them, tuples
    here otherwise); deriving the CHECK text from them means the constraint and the state
    machine cannot drift apart — which is the failure mode where a valid domain transition
    starts raising a database error in production.
    """
    return "IN (" + ", ".join(f"'{v}'" for v in values) + ")"


# -- user -------------------------------------------------------------------------------------

#: ``pending_verification → active → (suspended | locked | deleting | deleted)``.
#: Transitions are enforced in the domain state machine (T023), not by the database —
#: the CHECK only bounds the value set. The tuple is derived from the domain enum so the
#: two cannot drift.
USER_STATUSES = tuple(s.value for s in UserStatus)

IDENTITY_VERIFICATION_LEVELS = ("none", "email", "kyc_pending", "kyc_verified")


class UserTable(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user"
    __table_args__ = (
        CheckConstraint(f"status {_in(USER_STATUSES)}", name="status"),
        CheckConstraint(
            f"identity_verification_level {_in(IDENTITY_VERIFICATION_LEVELS)}",
            name="identity_verification_level",
        ),
        CheckConstraint("failed_login_count >= 0", name="failed_login_count"),
        CheckConstraint("roles_ver >= 0", name="roles_ver"),
    )

    email: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    email_verified_at: Mapped[datetime | None]
    #: Argon2id encoded hash with embedded params; NULL = passwordless account (magic-link
    #: or OAuth-only). Never anything else — no plaintext, no reversible form, ever.
    password_hash: Mapped[str | None]
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'pending_verification'")
    )
    #: Server-driven onboarding step machine (plan §3). Free-form jsonb: the shape is owned
    #: by the service, and a step addition must not need a migration.
    onboarding_state: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    #: Bumped on any role/permission change; carried in the access token so a cached
    #: authorization decision can be invalidated without waiting for token expiry.
    roles_ver: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    #: Derived convenience flag (true iff an active MFA factor exists). Kept in sync by the
    #: MFA service; read by the auth middleware without a join.
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    identity_verification_level: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'none'")
    )
    # -- backoff state (mirrors atlas_core.ratelimit; Redis is the live counter, this is the
    # durable record so a lockout survives a Redis flush) --
    locked_until: Mapped[datetime | None]
    failed_login_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    #: Reserved for future data-residency routing (plan: explicitly out of scope this spec).
    data_region: Mapped[str | None]
    #: Soft-delete grace marker; the row is hard-erased by the privacy worker after the
    #: 14-day window (FR-045).
    deleted_at: Mapped[datetime | None]


# -- user_profile (1:1 user) -------------------------------------------------------------------

TRADING_EXPERIENCES = ("novice", "intermediate", "advanced", "professional")
RISK_PREFERENCES = ("conservative", "balanced", "aggressive")


class UserProfileTable(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """All fields optional — data minimization (FR-044)."""

    __tablename__ = "user_profile"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_profile_user_id"),
        CheckConstraint(
            f"trading_experience {_in(TRADING_EXPERIENCES)}",
            name="trading_experience",
        ),
        CheckConstraint(
            f"risk_preference {_in(RISK_PREFERENCES)}",
            name="risk_preference",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", name="fk_user_profile_user_id_user"), nullable=False
    )
    display_name: Mapped[str | None]
    #: citext unique; the 30-day change cooldown is enforced in the service (needs the
    #: previous change timestamp, which lives in the audit trail, not a column).
    username: Mapped[str | None] = mapped_column(CITEXT, unique=True)
    avatar_ref: Mapped[str | None]
    country: Mapped[str | None]
    languages: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    timezone: Mapped[str | None]
    trading_experience: Mapped[str | None]
    preferred_markets: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    risk_preference: Mapped[str | None]
    bio: Mapped[str | None]


# -- consent_record (append-only) ---------------------------------------------------------------

CONSENT_DOCUMENTS = ("terms", "privacy", "risk_disclaimer", "marketing")


class ConsentRecordTable(UUIDPrimaryKeyMixin, Base):
    """Append-only: the latest row per (user, document) is the current state; history is
    the legal record. No ``updated_at`` — a consent row is never modified."""

    __tablename__ = "consent_record"
    __table_args__ = (
        CheckConstraint(f"document {_in(CONSENT_DOCUMENTS)}", name="document"),
        Index("ix_consent_record_user_id_document", "user_id", "document"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", name="fk_consent_record_user_id_user"), nullable=False, index=True
    )
    document: Mapped[str] = mapped_column(Text, nullable=False)
    #: Version of the document text shown, e.g. "terms@2026-08". Re-consent prompts compare
    #: this against the current version.
    document_version: Mapped[str] = mapped_column(Text, nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ip: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None]
    occurred_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"))


# -- oauth_account -------------------------------------------------------------------------------

#: google|github|apple ship now; saml|oidc_enterprise are reserved values so an enterprise
#: rollout is a config change, not a CHECK-constraint migration.
OAUTH_PROVIDERS = ("google", "github", "apple", "saml", "oidc_enterprise")


class OAuthAccountTable(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "oauth_account"
    __table_args__ = (
        UniqueConstraint(
            "provider", "provider_subject", name="uq_oauth_account_provider_provider_subject"
        ),
        CheckConstraint(
            f"provider {_in(OAUTH_PROVIDERS)}",
            name="provider",
        ),
        Index("ix_oauth_account_user_id", "user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", name="fk_oauth_account_user_id_user"), nullable=False
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    #: The provider's stable user id. (provider, provider_subject) is the external identity.
    provider_subject: Mapped[str] = mapped_column(Text, nullable=False)
    #: Email as reported by the provider at link time — kept for the link-audit trail even
    #: if the user later changes their Atlas email.
    email_at_link: Mapped[str | None] = mapped_column(CITEXT)
    scopes: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    linked_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"))


# -- verification_token ---------------------------------------------------------------------------

#: Must match ``TokenPurpose`` in service/one_time_tokens.py exactly.
VERIFICATION_TOKEN_PURPOSES = ("email_verify", "password_reset", "magic_link")


class VerificationTokenTable(UUIDPrimaryKeyMixin, Base):
    """Single-use hashed tokens (T011). No ``updated_at``: state moves forward through
    ``used_at``/``invalidated_at`` only, and both flips are audited by the service."""

    __tablename__ = "verification_token"
    __table_args__ = (
        CheckConstraint(
            f"purpose {_in(VERIFICATION_TOKEN_PURPOSES)}",
            name="purpose",
        ),
        # The live-token lookup the repository runs on every consume attempt and every
        # "invalidate prior" sweep; a full scan here is an auth-latency incident.
        Index(
            "ix_verification_token_user_id_purpose_live",
            "user_id",
            "purpose",
            postgresql_where=text("used_at IS NULL AND invalidated_at IS NULL"),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", name="fk_verification_token_user_id_user"), nullable=False, index=True
    )
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    #: SHA-256 digest of the raw token (32 bytes). The raw token is never stored.
    token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    used_at: Mapped[datetime | None]
    invalidated_at: Mapped[datetime | None]
    #: Issuance context (ip, user-agent) for abuse analysis. Small and non-secret by
    #: convention — the service controls the keys.
    context: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"))


# -- device ---------------------------------------------------------------------------------------


class DeviceTable(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Browser/device fingerprint derived from a signed first-party cookie, never from
    UA sniffing alone (spoofable). ``trusted`` skips MFA only while ``trusted_until`` is
    unexpired (30-day sliding window, refreshed on use)."""

    __tablename__ = "device"
    __table_args__ = (
        UniqueConstraint("user_id", "device_key_hash", name="uq_device_user_id_device_key_hash"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", name="fk_device_user_id_user"), nullable=False, index=True
    )
    #: SHA-256 of the signed device cookie value.
    device_key_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    label: Mapped[str | None]
    platform: Mapped[str | None]
    first_seen_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"))
    last_seen_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"))
    trusted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    trusted_until: Mapped[datetime | None]
    revoked_at: Mapped[datetime | None]


# -- session ---------------------------------------------------------------------------------------

#: ``active → rotated | revoked | expired`` (data-model.md). ``rotated``/``revoked`` are
#: terminal; reuse of a rotated token revokes the whole family.
SESSION_STATUSES = tuple(s.value for s in SessionStatus)


class SessionTable(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "session"
    __table_args__ = (
        CheckConstraint(f"status {_in(SESSION_STATUSES)}", name="status"),
        # The hot query: "is this user's session still active" on every refresh, and
        # "revoke everything for this user" on password change / logout-all.
        Index("ix_session_user_id_status", "user_id", "status"),
        Index("ix_session_family_id", "family_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", name="fk_session_user_id_user"), nullable=False
    )
    #: SHA-256 (hex) of the opaque refresh token; the raw token exists only in the cookie.
    refresh_token_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    #: Rotation family: one login creates one family; every refresh chains a child.
    #: Reuse of a rotated token ⇒ the whole family is revoked (token-theft detection).
    family_id: Mapped[uuid.UUID] = mapped_column(nullable=False, default=uuid.uuid4)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("session.id", name="fk_session_parent_id_session")
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'"))
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("device.id", name="fk_session_device_id_device")
    )
    ip: Mapped[str | None] = mapped_column(INET)
    #: GeoIP resolution at creation + last refresh (login-anomaly signal, FR-021).
    geo: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    user_agent: Mapped[str | None]
    #: When this session last passed a second factor — the step-up freshness source.
    mfa_verified_at: Mapped[datetime | None]
    #: Idle-timeout basis (14 days without use).
    last_used_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"))
    #: 90-day hard stop regardless of activity.
    absolute_expires_at: Mapped[datetime] = mapped_column(nullable=False)
    #: Denylist fast-path marker: set when revoked so the middleware's Redis denylist can
    #: be rebuilt after a flush without scanning history.
    revoked_at: Mapped[datetime | None]


__all__ = [
    "CONSENT_DOCUMENTS",
    "IDENTITY_VERIFICATION_LEVELS",
    "OAUTH_PROVIDERS",
    "SESSION_STATUSES",
    "TRADING_EXPERIENCES",
    "USER_STATUSES",
    "VERIFICATION_TOKEN_PURPOSES",
    "ConsentRecordTable",
    "DeviceTable",
    "OAuthAccountTable",
    "SessionTable",
    "UserTable",
    "UserProfileTable",
    "VerificationTokenTable",
]
