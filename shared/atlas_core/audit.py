"""Audit trail contract (FR-047; extended for Spec 02 auth actions, T018).

The entry shape and repository port live here, not in a module, because every module writes
audit entries and the composition root must be able to hold one without depending on
whichever module implements storage. The platform module owns the implementation and the
operator read API; anything that merely *records* an action needs only this file.

Spec 02 adds two things: a named taxonomy for the sensitive auth actions FR-017 requires to
be auditable (so the action strings are constants, not free text that drifts per call site),
and a secret-redaction guard that scrubs secret-shaped *values* as well as rejecting
secret-shaped *keys* — an audit trail that logs a plaintext token is a second breach waiting
to happen, and the whole point of the vault is that secrets never reach a log surface.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol


@dataclass(frozen=True)
class AuditLogEntry:
    actor: str
    action: str  # verb.noun, e.g. "dlq.redrive", "flag.change", "replay.start"
    target: str
    correlation_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class AuditAction(StrEnum):
    """FR-017 sensitive auth actions. Constants so the taxonomy is one auditable list and a
    call site cannot invent a near-duplicate string ("login.success" vs "auth.login_ok") that
    breaks later queries. Values follow the existing ``verb.noun`` convention."""

    LOGIN_SUCCESS = "auth.login_success"
    LOGIN_FAILED = "auth.login_failed"
    LOGOUT = "auth.logout"
    PASSWORD_CHANGED = "auth.password_changed"
    PASSWORD_RESET_REQUESTED = "auth.password_reset_requested"
    PASSWORD_RESET_COMPLETED = "auth.password_reset_completed"
    ACCOUNT_LOCKED = "auth.account_locked"
    ACCOUNT_UNLOCKED = "auth.account_unlocked"
    MFA_ENROLLED = "auth.mfa_enrolled"
    MFA_DISABLED = "auth.mfa_disabled"
    RECOVERY_CODE_USED = "auth.recovery_code_used"
    SESSION_REVOKED = "auth.session_revoked"
    SESSIONS_REVOKED_ALL = "auth.sessions_revoked_all"
    EMAIL_VERIFIED = "auth.email_verified"
    ACCOUNT_LINKED = "auth.account_linked"
    ACCOUNT_UNLINKED = "auth.account_unlinked"
    ROLE_ASSIGNED = "auth.role_assigned"
    ROLE_REVOKED = "auth.role_revoked"
    CREDENTIAL_STORED = "credentials.credential_stored"
    CREDENTIAL_ROTATED = "credentials.credential_rotated"
    CREDENTIAL_REVOKED = "credentials.credential_revoked"
    CREDENTIAL_RETRIEVED = "credentials.credential_retrieved"
    PRIVACY_EXPORT_REQUESTED = "privacy.export_requested"
    PRIVACY_ERASURE_REQUESTED = "privacy.erasure_requested"
    PRIVACY_ERASURE_COMPLETED = "privacy.erasure_completed"


class AuditLogRepository(Protocol):
    """Append-only by contract: no update or delete operation is exposed."""

    def append(self, entry: AuditLogEntry) -> None: ...

    def query(
        self,
        actor: str | None = None,
        action: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditLogEntry]: ...


#: Metadata keys that name a secret. A caller passing one of these is a bug — the value must
#: never have been in scope to record — so we reject rather than redact, to surface it loudly.
_SECRET_MARKERS = ("secret", "password", "token", "api_key", "credential", "private_key")

#: Values that *look* like a secret even under a benign key (a raw key pasted into a
#: ``detail`` field, a bearer string, a PEM header). These are redacted in place: the entry is
#: still useful, the secret is not. Patterns are deliberately conservative — false positives
#: cost a redaction, false negatives cost a leak.
_REDACT_VALUE_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),  # PEM private key material
    # JWT: header.payload.signature, all base64url.
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    re.compile(r"\bbearer\s+[A-Za-z0-9._~+/-]+=*\b", re.IGNORECASE),  # Authorization value
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),  # AWS access key id
    re.compile(r"\b[0-9a-f]{32,}\b"),  # long hex blobs (DEK/hashed-secret shaped)
)

_REDACTED = "***REDACTED***"


def _key_is_secret(key: str) -> bool:
    lowered = key.lower()
    return any(marker in lowered for marker in _SECRET_MARKERS)


def _value_is_secret(value: str) -> bool:
    return any(pattern.search(value) for pattern in _REDACT_VALUE_PATTERNS)


def redact_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy of ``metadata`` safe to persist.

    Raises on a secret-shaped *key* (a programming error — the value should never have been
    handed to the audit layer) and replaces a secret-shaped *string value* with a redaction
    marker (a data hazard — the key is fine, the content is not). Nested mappings and lists
    are walked so a secret buried one level deep is still caught.
    """
    out: dict[str, Any] = {}
    for key, value in metadata.items():
        if _key_is_secret(key):
            raise ValueError(f"Audit metadata may not contain secret-shaped key '{key}'")
        out[key] = _redact_value(value)
    return out


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return _REDACTED if _value_is_secret(value) else value
    if isinstance(value, Mapping):
        return redact_metadata(value)
    if isinstance(value, (list, tuple)):
        return [_redact_value(item) for item in value]
    return value


class InMemoryAuditLog:
    """Reference implementation, alongside the other in-memory adapters. The Postgres
    implementation (no UPDATE/DELETE grants) lands with the first persistent deployment.

    Append-only: no update or delete methods exist, by design. Every entry is passed through
    :func:`redact_metadata` on the way in, so the guard applies to all writers, not only the
    ones that remember to call it.
    """

    def __init__(self) -> None:
        self._entries: list[AuditLogEntry] = []

    def append(self, entry: AuditLogEntry) -> None:
        safe_metadata = redact_metadata(entry.metadata)
        # Rebuild with redacted metadata rather than mutating: the entry is frozen and the
        # caller may still hold a reference to the original.
        self._entries.append(
            AuditLogEntry(
                actor=entry.actor,
                action=entry.action,
                target=entry.target,
                correlation_id=entry.correlation_id,
                metadata=safe_metadata,
                id=entry.id,
                occurred_at=entry.occurred_at,
            )
        )

    def query(
        self,
        actor: str | None = None,
        action: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditLogEntry]:
        results = [
            e
            for e in self._entries
            if (actor is None or e.actor == actor)
            and (action is None or e.action == action)
            and (since is None or e.occurred_at >= since)
            and (until is None or e.occurred_at <= until)
        ]
        return results[-limit:]
