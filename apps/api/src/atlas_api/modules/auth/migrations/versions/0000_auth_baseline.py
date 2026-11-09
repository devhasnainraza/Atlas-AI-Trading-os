"""auth branch baseline

Establishes the `auth` migration branch. The revision itself is empty on purpose: its job
is to exist so later auth revisions chain onto ``auth@head`` instead of onto a shared root,
which is what lets the credentials team land a migration the same week without a
down_revision conflict.

Revision ID: auth0000
Revises:
Create Date: 2026-09-07

Branch: auth — new revisions chain with ``--head=auth@head``.
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "auth0000"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = ("auth",)
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
