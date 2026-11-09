"""User persistence (T024).

Three layers in one file, mirroring the ``one_time_tokens`` pattern the codebase already
uses: a :class:`UserRepository` Protocol (the port services speak to), an in-memory
implementation (the supported local/test store — ``atlas_core.db`` documents that
persistence-backed code has an in-memory alternative), and a SQLAlchemy implementation for
Postgres.

The security-relevant shape:

* **The password hash never enters the domain object.** :class:`User` carries
  ``has_password`` (a bool) but not the hash. Login fetches the hash through a dedicated
  :meth:`UserRepository.get_password_hash` so no code path can accidentally serialize a
  ``User`` (into a log line, an event payload, a response) and leak a credential. The
  separation is the point, not an inconvenience.
* **Lookups are by canonical email.** ``email`` is ``citext`` in the database, so the
  comparison is case-folded by the column; the repository does no lowercasing of its own
  (a second normalization that disagrees with the column's is how duplicate accounts are
  born).
* **Updates go through the whole object.** :meth:`update` writes the mutable status/backoff
  fields from a domain :class:`User`. It does not accept a partial dict — a caller that
  wants to change ``status`` must have produced a new ``User`` through the state machine
  (T023), which is what keeps an illegal transition from reaching the database.
"""

from __future__ import annotations

import uuid
from typing import Protocol

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from atlas_api.modules.auth.domain.models import User, UserStatus
from atlas_api.modules.auth.repository.tables import UserTable


class EmailAlreadyExistsError(Exception):
    """Raised by :meth:`UserRepository.create` when the email is taken.

    A distinct exception (rather than a returned ``None``) so the registration service can
    catch exactly this and still answer with the enumeration-safe "if that email is new, a
    verification link is on its way" — while a *different* integrity failure (a CHECK
    violation, say) propagates as the bug it is instead of being masked.
    """


def _to_domain(row: UserTable) -> User:
    return User(
        id=row.id,
        email=row.email,
        status=UserStatus(row.status),
        email_verified_at=row.email_verified_at,
        has_password=row.password_hash is not None,
        roles_ver=row.roles_ver,
        mfa_enabled=row.mfa_enabled,
        locked_until=row.locked_until,
        failed_login_count=row.failed_login_count,
        created_at=row.created_at,
    )


class UserRepository(Protocol):
    """Port for identity-core user rows."""

    async def create(self, user: User, *, password_hash: str | None) -> User: ...

    async def get_by_id(self, user_id: uuid.UUID) -> User | None: ...

    async def get_by_email(self, email: str) -> User | None: ...

    async def get_password_hash(self, user_id: uuid.UUID) -> str | None: ...

    async def update(self, user: User) -> User: ...

    async def set_password_hash(self, user_id: uuid.UUID, password_hash: str | None) -> None: ...


class InMemoryUserRepository:
    """Dict-backed store with the same email-uniqueness rule the table enforces."""

    def __init__(self) -> None:
        # Keyed case-insensitively to mirror the citext column: two callers that disagree on
        # case must collide here exactly as they would in Postgres.
        self._by_id: dict[uuid.UUID, User] = {}
        self._email_index: dict[str, uuid.UUID] = {}
        self._password_hash: dict[uuid.UUID, str] = {}

    async def create(self, user: User, *, password_hash: str | None) -> User:
        key = user.email.lower()
        if key in self._email_index:
            raise EmailAlreadyExistsError(user.email)
        self._by_id[user.id] = user
        self._email_index[key] = user.id
        if password_hash is not None:
            self._password_hash[user.id] = password_hash
        return user

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self._by_id.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        user_id = self._email_index.get(email.lower())
        return self._by_id.get(user_id) if user_id is not None else None

    async def get_password_hash(self, user_id: uuid.UUID) -> str | None:
        return self._password_hash.get(user_id)

    async def update(self, user: User) -> User:
        if user.id not in self._by_id:
            raise KeyError(f"no user {user.id} to update")
        self._by_id[user.id] = user
        return user

    async def set_password_hash(self, user_id: uuid.UUID, password_hash: str | None) -> None:
        if password_hash is None:
            self._password_hash.pop(user_id, None)
        else:
            self._password_hash[user_id] = password_hash


class SqlUserRepository:
    """Postgres/SQLAlchemy implementation over :class:`UserTable`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user: User, *, password_hash: str | None) -> User:
        row = UserTable(
            id=user.id,
            email=user.email,
            email_verified_at=user.email_verified_at,
            password_hash=password_hash,
            status=user.status.value,
            roles_ver=user.roles_ver,
            mfa_enabled=user.mfa_enabled,
            locked_until=user.locked_until,
            failed_login_count=user.failed_login_count,
        )
        self._session.add(row)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            # Only the email-unique violation is an expected outcome; anything else (a CHECK
            # on status, say) is a programming error and must not be swallowed as "taken".
            if _is_email_unique_violation(exc):
                raise EmailAlreadyExistsError(user.email) from exc
            raise
        return user

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        row = await self._session.get(UserTable, user_id)
        return _to_domain(row) if row is not None else None

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(UserTable).where(UserTable.email == email))
        row = result.scalar_one_or_none()
        return _to_domain(row) if row is not None else None

    async def get_password_hash(self, user_id: uuid.UUID) -> str | None:
        result = await self._session.execute(
            select(UserTable.password_hash).where(UserTable.id == user_id)
        )
        return result.scalar_one_or_none()

    async def update(self, user: User) -> User:
        await self._session.execute(
            update(UserTable)
            .where(UserTable.id == user.id)
            .values(
                status=user.status.value,
                email_verified_at=user.email_verified_at,
                roles_ver=user.roles_ver,
                mfa_enabled=user.mfa_enabled,
                locked_until=user.locked_until,
                failed_login_count=user.failed_login_count,
            )
        )
        return user

    async def set_password_hash(self, user_id: uuid.UUID, password_hash: str | None) -> None:
        await self._session.execute(
            update(UserTable).where(UserTable.id == user_id).values(password_hash=password_hash)
        )


def _is_email_unique_violation(exc: IntegrityError) -> bool:
    """Best-effort discrimination of the email-unique violation from other integrity errors.

    Postgres reports a unique violation with SQLSTATE 23505 and names the constraint; the
    ``uq_user_email`` name is what we care about. If the driver surfaces neither, we treat it
    as *not* the expected collision and let it propagate — a false "email taken" would turn a
    real bug into a silent, wrong user-facing message.
    """
    orig = getattr(exc, "orig", None)
    sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
    if sqlstate != "23505":
        return False
    message = str(orig)
    return "uq_user_email" in message or "user_email_key" in message


__all__ = [
    "EmailAlreadyExistsError",
    "InMemoryUserRepository",
    "SqlUserRepository",
    "UserRepository",
]
