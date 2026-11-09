"""credentials branch baseline

Establishes the `credentials` migration branch. Like the auth baseline, this revision is
empty: its job is to define a branch point so the credentials team can migrate
independently.

The credentials module depends on auth (a ``credential`` row references ``user.id``), so
this baseline declares ``depends_on = ("auth",)``. Alembic guarantees the auth branch
migrates first, preventing a ``credential_version`` migration from landing before the
``user`` table exists.

Revision ID: cred0000
Revises:
Create Date: 2026-09-07

Branch: credentials — new revisions chain with ``--head=credentials@head``.
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "cred0000"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = ("credentials",)
depends_on: str | Sequence[str] | None = ("auth",)


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass