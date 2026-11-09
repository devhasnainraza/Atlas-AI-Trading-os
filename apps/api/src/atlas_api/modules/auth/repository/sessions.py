"""Session persistence (T024) — the refresh-token rotation store.

A session row is the durable half of a refresh token: the raw token lives only in the
client's cookie, the ``SHA-256`` hash lives here, and the rotation ``family_id`` ties every
chained refresh back to the one interactive login that started it. The queries on this port
are exactly the ones the session service (T026) runs on the hot path:

* :meth:`SessionRepository.get_by_token_hash` — every refresh. A rotated row is *returned*,
  not hidden: reuse of a rotated token is the theft signal, so the service must be able to
  see it to revoke the family.
* :meth:`SessionRepository.revoke_family` — the reuse-detection kill switch.
* :meth:`SessionRepository.revoke_all_for_user` — logout-everywhere / password change.

The atomicity rule that matters: **rotation is two writes in one unit of work** (parent →
``rotated``, child inserted). The repository exposes them as separate calls and relies on the
caller's session-scoped transaction (``atlas_core.db.session_scope``) to make them atomic —
half-rotating is precisely the state that defeats reuse detection, and a service that commits
between the two would create it.
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime
from typing import Protocol

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from atlas_api.modules.auth.domain.models import Session, SessionStatus
from atlas_api.modules.auth.repository.tables import SessionTable


def _to_domain(row: SessionTable) -> Session:
    return Session(
        id=row.id,
        user_id=row.user_id,
        family_id=row.family_id,
        status=SessionStatus(row.status),
        parent_id=row.parent_id,
        device_id=row.device_id,
        mfa_verified_at=row.mfa_verified_at,
        last_used_at=row.last_used_at,
        absolute_expires_at=row.absolute_expires_at,
    )


class SessionRepository(Protocol):
    """Port for refresh-session rows."""

    async def create(self, session: Session, *, refresh_token_hash: str) -> Session: ...

    async def get_by_id(self, session_id: uuid.UUID) -> Session | None: ...

    async def get_by_token_hash(self, refresh_token_hash: str) -> Session | None: ...

    async def list_active_for_user(self, user_id: uuid.UUID) -> list[Session]: ...

    async def update(self, session: Session, *, now: datetime) -> Session: ...

    async def set_token_hash(self, session_id: uuid.UUID, refresh_token_hash: str) -> None: ...

    async def touch(self, session_id: uuid.UUID, *, now: datetime) -> None: ...

    async def revoke_family(self, family_id: uuid.UUID, *, now: datetime) -> int: ...

    async def revoke_all_for_user(self, user_id: uuid.UUID, *, now: datetime) -> int: ...


class InMemorySessionRepository:
    """Dict-backed store mirroring the family-revocation semantics the table enforces."""

    def __init__(self) -> None:
        self._by_id: dict[uuid.UUID, Session] = {}
        self._hash_index: dict[str, uuid.UUID] = {}

    async def create(self, session: Session, *, refresh_token_hash: str) -> Session:
        self._by_id[session.id] = session
        self._hash_index[refresh_token_hash] = session.id
        return session

    async def get_by_id(self, session_id: uuid.UUID) -> Session | None:
        return self._by_id.get(session_id)

    async def get_by_token_hash(self, refresh_token_hash: str) -> Session | None:
        session_id = self._hash_index.get(refresh_token_hash)
        return self._by_id.get(session_id) if session_id is not None else None

    async def list_active_for_user(self, user_id: uuid.UUID) -> list[Session]:
        return [
            s
            for s in self._by_id.values()
            if s.user_id == user_id and s.status is SessionStatus.ACTIVE
        ]

    async def update(self, session: Session, *, now: datetime) -> Session:
        if session.id not in self._by_id:
            raise KeyError(f"no session {session.id} to update")
        self._by_id[session.id] = session
        return session

    async def set_token_hash(self, session_id: uuid.UUID, refresh_token_hash: str) -> None:
        self._hash_index[refresh_token_hash] = session_id

    async def touch(self, session_id: uuid.UUID, *, now: datetime) -> None:
        session = self._by_id.get(session_id)
        if session is not None:
            self._by_id[session_id] = replace(session, last_used_at=now)

    async def revoke_family(self, family_id: uuid.UUID, *, now: datetime) -> int:
        count = 0
        for session in list(self._by_id.values()):
            if session.family_id == family_id and session.status in (
                SessionStatus.ACTIVE,
                SessionStatus.ROTATED,
            ):
                self._by_id[session.id] = session.revoke()
                count += 1
        return count

    async def revoke_all_for_user(self, user_id: uuid.UUID, *, now: datetime) -> int:
        count = 0
        for session in list(self._by_id.values()):
            if session.user_id == user_id and session.status is SessionStatus.ACTIVE:
                self._by_id[session.id] = session.revoke()
                count += 1
        return count


class SqlSessionRepository:
    """Postgres/SQLAlchemy implementation over :class:`SessionTable`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, session: Session, *, refresh_token_hash: str) -> Session:
        row = SessionTable(
            id=session.id,
            user_id=session.user_id,
            refresh_token_hash=refresh_token_hash,
            family_id=session.family_id,
            parent_id=session.parent_id,
            status=session.status.value,
            device_id=session.device_id,
            mfa_verified_at=session.mfa_verified_at,
            last_used_at=session.last_used_at,
            absolute_expires_at=session.absolute_expires_at,
        )
        self._session.add(row)
        await self._session.flush()
        return session

    async def get_by_id(self, session_id: uuid.UUID) -> Session | None:
        row = await self._session.get(SessionTable, session_id)
        return _to_domain(row) if row is not None else None

    async def get_by_token_hash(self, refresh_token_hash: str) -> Session | None:
        result = await self._session.execute(
            select(SessionTable).where(SessionTable.refresh_token_hash == refresh_token_hash)
        )
        row = result.scalar_one_or_none()
        return _to_domain(row) if row is not None else None

    async def list_active_for_user(self, user_id: uuid.UUID) -> list[Session]:
        result = await self._session.execute(
            select(SessionTable)
            .where(
                SessionTable.user_id == user_id,
                SessionTable.status == SessionStatus.ACTIVE.value,
            )
            .order_by(SessionTable.last_used_at.desc())
        )
        return [_to_domain(row) for row in result.scalars().all()]

    async def update(self, session: Session, *, now: datetime) -> Session:
        await self._session.execute(
            update(SessionTable)
            .where(SessionTable.id == session.id)
            .values(
                status=session.status.value,
                last_used_at=session.last_used_at,
                mfa_verified_at=session.mfa_verified_at,
                revoked_at=now if session.status is SessionStatus.REVOKED else None,
            )
        )
        return session

    async def set_token_hash(self, session_id: uuid.UUID, refresh_token_hash: str) -> None:
        await self._session.execute(
            update(SessionTable)
            .where(SessionTable.id == session_id)
            .values(refresh_token_hash=refresh_token_hash)
        )

    async def touch(self, session_id: uuid.UUID, *, now: datetime) -> None:
        await self._session.execute(
            update(SessionTable).where(SessionTable.id == session_id).values(last_used_at=now)
        )

    async def revoke_family(self, family_id: uuid.UUID, *, now: datetime) -> int:
        # active AND rotated: a rotated row is the theft evidence, and the family-wide kill
        # must reach it too — the attacker's live token is a child of the rotated parent.
        result = await self._session.execute(
            update(SessionTable)
            .where(
                SessionTable.family_id == family_id,
                SessionTable.status.in_([SessionStatus.ACTIVE.value, SessionStatus.ROTATED.value]),
            )
            .values(status=SessionStatus.REVOKED.value, revoked_at=now)
        )
        return int(result.rowcount or 0)

    async def revoke_all_for_user(self, user_id: uuid.UUID, *, now: datetime) -> int:
        result = await self._session.execute(
            update(SessionTable)
            .where(
                SessionTable.user_id == user_id,
                SessionTable.status == SessionStatus.ACTIVE.value,
            )
            .values(status=SessionStatus.REVOKED.value, revoked_at=now)
        )
        return int(result.rowcount or 0)


__all__ = [
    "InMemorySessionRepository",
    "SessionRepository",
    "SqlSessionRepository",
]
