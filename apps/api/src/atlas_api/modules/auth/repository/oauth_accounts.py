"""OAuth-account persistence (T024).

One row links one external identity (``provider`` + ``provider_subject``) to one Atlas user.
The unique constraint on ``(provider, provider_subject)`` is the whole account-linking rule:
a Google account maps to exactly one Atlas user, and the OAuth service (T027) relies on
"look up by provider+subject, create if absent" being the atomic identity resolution.

These are passive records — no state machine — so the value object lives here rather than in
``domain/models.py`` (which holds the entities that *have* transitions). The one rule worth
naming: :meth:`OAuthAccountRepository.count_for_user` exists because of the data-model
constraint *"cannot delete the last sign-in method of a user"* — unlinking the only OAuth
account of a passwordless user would lock them out, and the service checks the count (plus
``has_password``) before allowing it.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from atlas_api.modules.auth.repository.tables import OAuthAccountTable


@dataclass(frozen=True)
class OAuthAccount:
    id: uuid.UUID
    user_id: uuid.UUID
    provider: str
    provider_subject: str
    email_at_link: str | None = None
    scopes: tuple[str, ...] = ()
    linked_at: datetime | None = None


def _to_domain(row: OAuthAccountTable) -> OAuthAccount:
    return OAuthAccount(
        id=row.id,
        user_id=row.user_id,
        provider=row.provider,
        provider_subject=row.provider_subject,
        email_at_link=row.email_at_link,
        scopes=tuple(row.scopes or ()),
        linked_at=row.linked_at,
    )


class OAuthAccountRepository(Protocol):
    """Port for external-identity links."""

    async def get_by_provider_subject(
        self, *, provider: str, provider_subject: str
    ) -> OAuthAccount | None: ...

    async def list_for_user(self, user_id: uuid.UUID) -> list[OAuthAccount]: ...

    async def count_for_user(self, user_id: uuid.UUID) -> int: ...

    async def link(self, account: OAuthAccount) -> OAuthAccount: ...

    async def unlink(self, *, provider: str, provider_subject: str) -> bool: ...


class InMemoryOAuthAccountRepository:
    def __init__(self) -> None:
        self._by_id: dict[uuid.UUID, OAuthAccount] = {}
        self._ps_index: dict[tuple[str, str], uuid.UUID] = {}

    async def get_by_provider_subject(
        self, *, provider: str, provider_subject: str
    ) -> OAuthAccount | None:
        account_id = self._ps_index.get((provider, provider_subject))
        return self._by_id.get(account_id) if account_id is not None else None

    async def list_for_user(self, user_id: uuid.UUID) -> list[OAuthAccount]:
        return [a for a in self._by_id.values() if a.user_id == user_id]

    async def count_for_user(self, user_id: uuid.UUID) -> int:
        return sum(1 for a in self._by_id.values() if a.user_id == user_id)

    async def link(self, account: OAuthAccount) -> OAuthAccount:
        key = (account.provider, account.provider_subject)
        if key in self._ps_index:
            raise ValueError(f"oauth identity {key} already linked")
        self._by_id[account.id] = account
        self._ps_index[key] = account.id
        return account

    async def unlink(self, *, provider: str, provider_subject: str) -> bool:
        account_id = self._ps_index.pop((provider, provider_subject), None)
        if account_id is None:
            return False
        self._by_id.pop(account_id, None)
        return True


class SqlOAuthAccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_provider_subject(
        self, *, provider: str, provider_subject: str
    ) -> OAuthAccount | None:
        result = await self._session.execute(
            select(OAuthAccountTable).where(
                OAuthAccountTable.provider == provider,
                OAuthAccountTable.provider_subject == provider_subject,
            )
        )
        row = result.scalar_one_or_none()
        return _to_domain(row) if row is not None else None

    async def list_for_user(self, user_id: uuid.UUID) -> list[OAuthAccount]:
        result = await self._session.execute(
            select(OAuthAccountTable)
            .where(OAuthAccountTable.user_id == user_id)
            .order_by(OAuthAccountTable.linked_at)
        )
        return [_to_domain(row) for row in result.scalars().all()]

    async def count_for_user(self, user_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(OAuthAccountTable)
            .where(OAuthAccountTable.user_id == user_id)
        )
        return int(result.scalar_one())

    async def link(self, account: OAuthAccount) -> OAuthAccount:
        row = OAuthAccountTable(
            id=account.id,
            user_id=account.user_id,
            provider=account.provider,
            provider_subject=account.provider_subject,
            email_at_link=account.email_at_link,
            scopes=list(account.scopes),
            linked_at=account.linked_at,
        )
        self._session.add(row)
        await self._session.flush()
        return account

    async def unlink(self, *, provider: str, provider_subject: str) -> bool:
        result = await self._session.execute(
            select(OAuthAccountTable).where(
                OAuthAccountTable.provider == provider,
                OAuthAccountTable.provider_subject == provider_subject,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.flush()
        return True


__all__ = [
    "InMemoryOAuthAccountRepository",
    "OAuthAccount",
    "OAuthAccountRepository",
    "SqlOAuthAccountRepository",
]
