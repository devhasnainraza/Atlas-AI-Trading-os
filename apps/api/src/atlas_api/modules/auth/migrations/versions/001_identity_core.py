"""identity core tables

Creates the seven tables of the identity core (data-model.md): ``user``, ``user_profile``,
``consent_record``, ``oauth_account``, ``verification_token``, ``session``, ``device``.

Notes for the reviewer:

* ``citext`` is created here because ``user.email`` / ``user_profile.username`` /
  ``oauth_account.email_at_link`` depend on it. ``IF NOT EXISTS`` keeps the migration
  re-runnable on databases where a DBA pre-created the extension.
* Enums are VARCHAR + CHECK, not native Postgres types (tables.py module docstring explains
  why). The CHECK names follow the metadata naming convention so autogenerate sees them as
  matching.
* ``session`` carries the rotation-family columns (``family_id``, ``parent_id``) and both
  hot-path indexes from day one; a partition-by-month plan is documented in data-model.md
  for SC-008 scale but not applied — partitioning a table with a unique constraint on
  ``refresh_token_hash`` requires the partition key in the constraint, which is a
  deliberate later migration, not an oversight here.
* The partial index on ``verification_token`` covers only live tokens; spent/invalidated
  rows are dead weight for every query the service runs.

Revision ID: auth0001
Revises: auth0000
Create Date: 2026-09-07

Branch: auth
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "auth0001"
down_revision: str | None = "auth0000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TZTIMESTAMP = postgresql.TIMESTAMP(timezone=True)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    op.create_table(
        "user",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("email_verified_at", TZTIMESTAMP, nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Text(),
            server_default=sa.text("'pending_verification'"),
            nullable=False,
        ),
        sa.Column(
            "onboarding_state",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("roles_ver", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("mfa_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "identity_verification_level",
            sa.Text(),
            server_default=sa.text("'none'"),
            nullable=False,
        ),
        sa.Column("locked_until", TZTIMESTAMP, nullable=True),
        sa.Column("failed_login_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("data_region", sa.Text(), nullable=True),
        sa.Column("deleted_at", TZTIMESTAMP, nullable=True),
        sa.Column("created_at", TZTIMESTAMP, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TZTIMESTAMP, server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending_verification', 'active', 'suspended', 'locked', "
            "'deleting', 'deleted')",
            name="status",
        ),
        sa.CheckConstraint(
            "identity_verification_level IN ('none', 'email', 'kyc_pending', 'kyc_verified')",
            name="identity_verification_level",
        ),
        sa.CheckConstraint("failed_login_count >= 0", name="failed_login_count"),
        sa.CheckConstraint("roles_ver >= 0", name="roles_ver"),
        sa.PrimaryKeyConstraint("id", name="pk_user"),
        sa.UniqueConstraint("email", name="uq_user_email"),
    )

    op.create_table(
        "user_profile",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("username", postgresql.CITEXT(), nullable=True),
        sa.Column("avatar_ref", sa.Text(), nullable=True),
        sa.Column("country", sa.Text(), nullable=True),
        sa.Column("languages", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("timezone", sa.Text(), nullable=True),
        sa.Column("trading_experience", sa.Text(), nullable=True),
        sa.Column("preferred_markets", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("risk_preference", sa.Text(), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("created_at", TZTIMESTAMP, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TZTIMESTAMP, server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "trading_experience IN ('novice', 'intermediate', 'advanced', 'professional')",
            name="trading_experience",
        ),
        sa.CheckConstraint(
            "risk_preference IN ('conservative', 'balanced', 'aggressive')",
            name="risk_preference",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name="fk_user_profile_user_id_user"),
        sa.PrimaryKeyConstraint("id", name="pk_user_profile"),
        sa.UniqueConstraint("user_id", name="uq_user_profile_user_id"),
        sa.UniqueConstraint("username", name="uq_user_profile_username"),
    )

    op.create_table(
        "consent_record",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("document", sa.Text(), nullable=False),
        sa.Column("document_version", sa.Text(), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("ip", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("occurred_at", TZTIMESTAMP, server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "document IN ('terms', 'privacy', 'risk_disclaimer', 'marketing')",
            name="document",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name="fk_consent_record_user_id_user"),
        sa.PrimaryKeyConstraint("id", name="pk_consent_record"),
    )
    op.create_index("ix_consent_record_user_id", "consent_record", ["user_id"], unique=False)
    op.create_index(
        "ix_consent_record_user_id_document",
        "consent_record",
        ["user_id", "document"],
        unique=False,
    )

    op.create_table(
        "oauth_account",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("provider_subject", sa.Text(), nullable=False),
        sa.Column("email_at_link", postgresql.CITEXT(), nullable=True),
        sa.Column("scopes", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("linked_at", TZTIMESTAMP, server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", TZTIMESTAMP, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TZTIMESTAMP, server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "provider IN ('google', 'github', 'apple', 'saml', 'oidc_enterprise')",
            name="provider",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name="fk_oauth_account_user_id_user"),
        sa.PrimaryKeyConstraint("id", name="pk_oauth_account"),
        sa.UniqueConstraint(
            "provider", "provider_subject", name="uq_oauth_account_provider_provider_subject"
        ),
    )
    op.create_index("ix_oauth_account_user_id", "oauth_account", ["user_id"], unique=False)

    op.create_table(
        "verification_token",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("token_hash", postgresql.BYTEA(length=32), nullable=False),
        sa.Column("expires_at", TZTIMESTAMP, nullable=False),
        sa.Column("used_at", TZTIMESTAMP, nullable=True),
        sa.Column("invalidated_at", TZTIMESTAMP, nullable=True),
        sa.Column(
            "context",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", TZTIMESTAMP, server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "purpose IN ('email_verify', 'password_reset', 'magic_link')",
            name="purpose",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"], name="fk_verification_token_user_id_user"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_verification_token"),
        sa.UniqueConstraint("token_hash", name="uq_verification_token_token_hash"),
    )
    op.create_index(
        "ix_verification_token_user_id", "verification_token", ["user_id"], unique=False
    )
    op.create_index(
        "ix_verification_token_user_id_purpose_live",
        "verification_token",
        ["user_id", "purpose"],
        unique=False,
        postgresql_where=sa.text("used_at IS NULL AND invalidated_at IS NULL"),
    )

    op.create_table(
        "device",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("device_key_hash", postgresql.BYTEA(length=32), nullable=False),
        sa.Column("label", sa.Text(), nullable=True),
        sa.Column("platform", sa.Text(), nullable=True),
        sa.Column("first_seen_at", TZTIMESTAMP, server_default=sa.text("now()"), nullable=False),
        sa.Column("last_seen_at", TZTIMESTAMP, server_default=sa.text("now()"), nullable=False),
        sa.Column("trusted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("trusted_until", TZTIMESTAMP, nullable=True),
        sa.Column("revoked_at", TZTIMESTAMP, nullable=True),
        sa.Column("created_at", TZTIMESTAMP, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TZTIMESTAMP, server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name="fk_device_user_id_user"),
        sa.PrimaryKeyConstraint("id", name="pk_device"),
        sa.UniqueConstraint("user_id", "device_key_hash", name="uq_device_user_id_device_key_hash"),
    )
    op.create_index("ix_device_user_id", "device", ["user_id"], unique=False)

    op.create_table(
        "session",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("refresh_token_hash", sa.Text(), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'active'"), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=True),
        sa.Column("ip", postgresql.INET(), nullable=True),
        sa.Column("geo", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("mfa_verified_at", TZTIMESTAMP, nullable=True),
        sa.Column("last_used_at", TZTIMESTAMP, server_default=sa.text("now()"), nullable=False),
        sa.Column("absolute_expires_at", TZTIMESTAMP, nullable=False),
        sa.Column("revoked_at", TZTIMESTAMP, nullable=True),
        sa.Column("created_at", TZTIMESTAMP, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TZTIMESTAMP, server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('active', 'rotated', 'revoked', 'expired')",
            name="status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name="fk_session_user_id_user"),
        sa.ForeignKeyConstraint(["parent_id"], ["session.id"], name="fk_session_parent_id_session"),
        sa.ForeignKeyConstraint(["device_id"], ["device.id"], name="fk_session_device_id_device"),
        sa.PrimaryKeyConstraint("id", name="pk_session"),
        sa.UniqueConstraint("refresh_token_hash", name="uq_session_refresh_token_hash"),
    )
    op.create_index("ix_session_user_id_status", "session", ["user_id", "status"], unique=False)
    op.create_index("ix_session_family_id", "session", ["family_id"], unique=False)


def downgrade() -> None:
    # Reverse dependency order: session references device and user; device,
    # verification_token, oauth_account, consent_record, user_profile reference user.
    op.drop_index("ix_session_family_id", table_name="session")
    op.drop_index("ix_session_user_id_status", table_name="session")
    op.drop_table("session")
    op.drop_index("ix_device_user_id", table_name="device")
    op.drop_table("device")
    op.drop_index("ix_verification_token_user_id_purpose_live", table_name="verification_token")
    op.drop_index("ix_verification_token_user_id", table_name="verification_token")
    op.drop_table("verification_token")
    op.drop_index("ix_oauth_account_user_id", table_name="oauth_account")
    op.drop_table("oauth_account")
    op.drop_index("ix_consent_record_user_id_document", table_name="consent_record")
    op.drop_index("ix_consent_record_user_id", table_name="consent_record")
    op.drop_table("consent_record")
    op.drop_table("user_profile")
    op.drop_table("user")
    # The extension is deliberately left in place: other branches (credentials) may come
    # to depend on it, and dropping a shared extension in a module downgrade is a
    # cross-module side effect.
