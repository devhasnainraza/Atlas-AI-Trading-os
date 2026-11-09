"""Repository protocol and in-memory implementation for venue connections (Spec 03 US1)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from atlas_core.errors import ConflictError, NotFoundError
from atlas_venues.enums import VenueEnvironment

from atlas_api.modules.trading.domain.connections import (
    ConnectionHealth,
    VenueAccount,
    VenueConnection,
)


class ConnectionRepository(Protocol):
    """Storage port for user venue connections and their accounts."""

    async def create(self, connection: VenueConnection) -> VenueConnection: ...

    async def get(self, connection_id: str, *, user_id: str | None = None) -> VenueConnection | None: ...

    async def list(
        self,
        user_id: str,
        *,
        environment: VenueEnvironment | None = None,
        health: ConnectionHealth | None = None,
        include_disconnected: bool = False,
    ) -> Sequence[VenueConnection]: ...

    async def update(self, connection: VenueConnection) -> VenueConnection: ...

    async def delete(self, connection_id: str, *, user_id: str) -> bool: ...

    async def find_by_credential(self, credential_id: str) -> Sequence[VenueConnection]: ...

    async def list_accounts(
        self, connection_id: str, *, user_id: str | None = None
    ) -> Sequence[VenueAccount]: ...

    async def upsert_accounts(self, accounts: Sequence[VenueAccount]) -> None: ...


class InMemoryConnectionRepository:
    """In-memory implementation honoring table constraints in data-model.md.

    - Unique (user_id, venue_code, label) where disconnected_at is null.
    - Unique (connection_id, venue_account_ref).
    """

    def __init__(self) -> None:
        self._connections: dict[str, VenueConnection] = {}
        self._accounts: dict[str, dict[str, VenueAccount]] = {}  # connection_id -> {account_ref: account}

    async def create(self, connection: VenueConnection) -> VenueConnection:
        # Check uniqueness constraint: (user_id, venue_code, label) where active
        for existing in self._connections.values():
            if (
                existing.disconnected_at is None
                and existing.user_id == connection.user_id
                and existing.venue_code == connection.venue_code
                and existing.label.lower() == connection.label.lower()
            ):
                raise ConflictError(
                    f"A connection with label '{connection.label}' already exists for venue '{connection.venue_code}'"
                )

        self._connections[connection.id] = connection
        return connection

    async def get(self, connection_id: str, *, user_id: str | None = None) -> VenueConnection | None:
        conn = self._connections.get(connection_id)
        if conn is None:
            return None
        if user_id is not None and conn.user_id != user_id:
            return None
        return conn

    async def list(
        self,
        user_id: str,
        *,
        environment: VenueEnvironment | None = None,
        health: ConnectionHealth | None = None,
        include_disconnected: bool = False,
    ) -> Sequence[VenueConnection]:
        results: list[VenueConnection] = []
        for conn in self._connections.values():
            if conn.user_id != user_id:
                continue
            if not include_disconnected and conn.disconnected_at is not None:
                continue
            if environment is not None and conn.environment is not environment:
                continue
            if health is not None and conn.health is not health:
                continue
            results.append(conn)
        return sorted(results, key=lambda c: c.created_at, reverse=True)

    async def update(self, connection: VenueConnection) -> VenueConnection:
        if connection.id not in self._connections:
            raise NotFoundError(f"Venue connection '{connection.id}' not found")
        self._connections[connection.id] = connection
        return connection

    async def delete(self, connection_id: str, *, user_id: str) -> bool:
        conn = await self.get(connection_id, user_id=user_id)
        if conn is None:
            return False
        # Soft-disconnect
        self._connections[connection_id] = conn.disconnect()
        return True

    async def find_by_credential(self, credential_id: str) -> Sequence[VenueConnection]:
        return tuple(
            conn for conn in self._connections.values()
            if conn.credential_id == credential_id and conn.disconnected_at is None
        )

    async def list_accounts(
        self, connection_id: str, *, user_id: str | None = None
    ) -> Sequence[VenueAccount]:
        conn = await self.get(connection_id, user_id=user_id)
        if conn is None:
            return ()
        accounts_map = self._accounts.get(connection_id, {})
        return tuple(accounts_map.values())

    async def upsert_accounts(self, accounts: Sequence[VenueAccount]) -> None:
        for acc in accounts:
            if acc.connection_id not in self._accounts:
                self._accounts[acc.connection_id] = {}
            self._accounts[acc.connection_id][acc.venue_account_ref] = acc


__all__ = [
    "ConnectionRepository",
    "InMemoryConnectionRepository",
]
