"""Async database engine, session factory, and declarative base.

One engine per process, created at startup and disposed at shutdown. Modules never build
their own engine — a second pool in the same process doubles the connection count Postgres
sees while halving the pool each half believes it owns, and the resulting "too many
connections" only shows up under load.

Session scope is the unit of work: one session per request (or per job), committed once at
the end, rolled back on any exception. ``session_scope`` enforces that; nothing in a module
should call ``session.commit()`` in the middle of a service method, because a half-committed
multi-step operation is exactly the state auditing cannot explain afterwards.

Test/local note: ``Database.configure`` accepts no URL and stays unconfigured, so importing
this module never opens a socket. Code that needs a session in a test either passes an
explicit engine or uses the in-memory repository implementations instead.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import NullPool

from atlas_core.ids import uuid7

#: Explicit constraint naming. Alembic autogenerate emits `DROP CONSTRAINT <name>` and
#: without a convention the name is whatever Postgres invented on the machine where the
#: table was first created — so a downgrade that works locally fails in staging.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    """Declarative base for every Atlas table.

    A single ``MetaData`` across modules is deliberate: Alembic autogenerate compares one
    metadata object against the live schema, and a foreign key from ``credential`` to
    ``user`` has to resolve at mapper-configuration time. Module boundaries are enforced by
    import-linter at the *code* level (services may only cross via ``public.py``); they are
    not enforced by giving each module a private schema registry.
    """

    metadata = metadata

    type_annotation_map = {  # noqa: RUF012 - SQLAlchemy reads this as a plain dict
        datetime: DateTime(timezone=True),
    }


def utcnow() -> datetime:
    """Timezone-aware now. Naive datetimes in a database are a bug waiting for a DST change."""
    return datetime.now(UTC)


class UUIDPrimaryKeyMixin:
    """UUIDv7 primary key, generated client-side.

    Client-side generation (rather than a database default) means the id exists before the
    INSERT, so an event or an audit record can reference the row without a round trip, and
    a multi-row graph can be built in memory and flushed once.
    """

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)


class TimestampMixin:
    """``created_at`` / ``updated_at``, both server-side.

    ``server_default``/``onupdate`` rather than Python defaults so a row written by a
    migration, a psql session, or a future service in another language still gets correct
    timestamps. Audit trails that depend on application code being the only writer are the
    ones that turn out to have gaps.
    """

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Database:
    """Holds the process-wide engine and session factory.

    Deliberately not a module-level global that self-initializes on import: composition
    happens in ``create_app``, and an engine that springs into existence on import cannot be
    torn down deterministically in tests.
    """

    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._sessionmaker: async_sessionmaker[AsyncSession] | None = None

    @property
    def is_configured(self) -> bool:
        return self._engine is not None

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            raise RuntimeError(
                "database is not configured — ATLAS_DATABASE_URL is unset. "
                "Persistence-backed code paths require a database; in-memory "
                "repositories are the supported alternative for local/test runs."
            )
        return self._engine

    def configure(
        self,
        url: str,
        *,
        echo: bool = False,
        pool_size: int = 10,
        max_overflow: int = 5,
        pool_timeout: float = 10.0,
        pool_recycle: int = 1800,
        use_null_pool: bool = False,
        connect_args: dict[str, Any] | None = None,
    ) -> None:
        """Create the engine. Idempotent per URL; re-configuring with a new URL is an error.

        ``pool_recycle`` defaults to 30 minutes because managed Postgres and pgbouncer both
        close idle server connections silently; a recycled connection is cheaper than the
        first query of the day failing with "server closed the connection unexpectedly".
        """
        if self._engine is not None:
            raise RuntimeError("database already configured — call dispose() first")

        self._engine = create_async_engine(
            _normalize_url(url),
            echo=echo,
            future=True,
            pool_pre_ping=True,
            connect_args=connect_args or {},
            **(
                {"poolclass": NullPool}
                if use_null_pool
                else {
                    "pool_size": pool_size,
                    "max_overflow": max_overflow,
                    "pool_timeout": pool_timeout,
                    "pool_recycle": pool_recycle,
                }
            ),
        )
        self._sessionmaker = async_sessionmaker(
            self._engine,
            expire_on_commit=False,
            autoflush=False,
        )

    def configure_engine(self, engine: AsyncEngine) -> None:
        """Adopt an externally built engine (tests, migrations, a throwaway sqlite file)."""
        if self._engine is not None:
            raise RuntimeError("database already configured — call dispose() first")
        self._engine = engine
        self._sessionmaker = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

    async def dispose(self) -> None:
        """Close the pool. Safe to call when unconfigured, so shutdown paths stay simple."""
        if self._engine is not None:
            await self._engine.dispose()
        self._engine = None
        self._sessionmaker = None

    def session(self) -> AsyncSession:
        """A new session. The caller owns commit/rollback — prefer ``session_scope``."""
        if self._sessionmaker is None:
            raise RuntimeError("database is not configured — call configure() first")
        return self._sessionmaker()

    @asynccontextmanager
    async def session_scope(self) -> AsyncIterator[AsyncSession]:
        """One unit of work: commit on success, roll back on any exception.

        The rollback is unconditional on error and the exception is re-raised. Swallowing it
        would let a caller believe a write succeeded, and for this codebase that means a
        session, a role grant, or a credential version that the client thinks exists.
        """
        session = self.session()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


#: Process-wide instance. Configured by the composition root, never on import.
database = Database()


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped unit of work."""
    async with database.session_scope() as session:
        yield session


def _normalize_url(url: str) -> str:
    """Force an async driver.

    ``ATLAS_DATABASE_URL`` is also read by psql-style tooling and Alembic, so the value in
    ``.env`` is the plain ``postgresql://`` form. Handing that to ``create_async_engine``
    raises a driver error at startup; rewriting it here means one URL serves both worlds.
    """
    if url.startswith("postgresql+"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):  # heroku-style alias
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("sqlite://") and "+aiosqlite" not in url:
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


def sync_url(url: str) -> str:
    """The synchronous form of a database URL, for tools that cannot speak asyncio."""
    return (
        url.replace("+asyncpg", "")
        .replace("+aiosqlite", "")
        .replace("postgres://", "postgresql://", 1)
    )


__all__ = [
    "Base",
    "Database",
    "NAMING_CONVENTION",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    "database",
    "get_session",
    "metadata",
    "sync_url",
    "utcnow",
]
