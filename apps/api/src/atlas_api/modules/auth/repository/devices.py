"""Device persistence (T024).

A device row is a remembered browser, keyed by the SHA-256 of a signed first-party cookie
(never by UA sniffing alone — that is spoofable). Its whole purpose is the MFA-trust skip
(FR-011): a trusted device within its sliding window lets a login pass without a second
factor. That makes the *lookup* the security-critical operation — get it wrong and either
every login challenges (annoyance) or an untrusted browser is treated as trusted (the bug
that matters).

The domain :class:`Device` deliberately does not carry ``device_key_hash``: it is a lookup
credential, not a property services reason about, so it stays at the repository boundary.
:meth:`DeviceRepository.find_or_create` takes the hash and returns the domain object; the
hash never round-trips through the domain.
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from atlas_api.modules.auth.domain.models import Device
from atlas_api.modules.auth.repository.tables import DeviceTable


def _to_domain(row: DeviceTable) -> Device:
    return Device(
        id=row.id,
        user_id=row.user_id,
        label=row.label,
        platform=row.platform,
        trusted=row.trusted,
        trusted_until=row.trusted_until,
        revoked_at=row.revoked_at,
        first_seen_at=row.first_seen_at,
        last_seen_at=row.last_seen_at,
    )


class DeviceRepository(Protocol):
    """Port for remembered-device rows."""

    async def find_or_create(
        self,
        *,
        user_id: uuid.UUID,
        device_key_hash: bytes,
        label: str | None,
        platform: str | None,
        now: datetime,
    ) -> Device: ...

    async def get_by_id(self, device_id: uuid.UUID) -> Device | None: ...

    async def list_for_user(self, user_id: uuid.UUID) -> list[Device]: ...

    async def update(self, device: Device) -> Device: ...


class InMemoryDeviceRepository:
    """Dict-backed store keyed by ``(user_id, device_key_hash)`` like the unique constraint."""

    def __init__(self) -> None:
        self._by_id: dict[uuid.UUID, Device] = {}
        self._key_index: dict[tuple[uuid.UUID, bytes], uuid.UUID] = {}

    async def find_or_create(
        self,
        *,
        user_id: uuid.UUID,
        device_key_hash: bytes,
        label: str | None,
        platform: str | None,
        now: datetime,
    ) -> Device:
        key = (user_id, device_key_hash)
        existing_id = self._key_index.get(key)
        if existing_id is not None:
            device = self._by_id[existing_id]
            # Seeing a device again slides last_seen_at; trust is *not* silently extended here
            # (the service decides whether a sighting refreshes the window).
            self._by_id[existing_id] = _seen(device, now)
            return self._by_id[existing_id]
        device = Device(
            id=uuid.uuid4(),
            user_id=user_id,
            label=label,
            platform=platform,
            first_seen_at=now,
            last_seen_at=now,
        )
        self._by_id[device.id] = device
        self._key_index[key] = device.id
        return device

    async def get_by_id(self, device_id: uuid.UUID) -> Device | None:
        return self._by_id.get(device_id)

    async def list_for_user(self, user_id: uuid.UUID) -> list[Device]:
        return [d for d in self._by_id.values() if d.user_id == user_id]

    async def update(self, device: Device) -> Device:
        if device.id not in self._by_id:
            raise KeyError(f"no device {device.id} to update")
        self._by_id[device.id] = device
        return device


def _seen(device: Device, now: datetime) -> Device:
    return replace(device, last_seen_at=now)


class SqlDeviceRepository:
    """Postgres/SQLAlchemy implementation over :class:`DeviceTable`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_or_create(
        self,
        *,
        user_id: uuid.UUID,
        device_key_hash: bytes,
        label: str | None,
        platform: str | None,
        now: datetime,
    ) -> Device:
        result = await self._session.execute(
            select(DeviceTable).where(
                DeviceTable.user_id == user_id,
                DeviceTable.device_key_hash == device_key_hash,
            )
        )
        row = result.scalar_one_or_none()
        if row is not None:
            row.last_seen_at = now
            await self._session.flush()
            return _to_domain(row)
        new_row = DeviceTable(
            id=uuid.uuid4(),
            user_id=user_id,
            device_key_hash=device_key_hash,
            label=label,
            platform=platform,
            first_seen_at=now,
            last_seen_at=now,
        )
        self._session.add(new_row)
        await self._session.flush()
        return _to_domain(new_row)

    async def get_by_id(self, device_id: uuid.UUID) -> Device | None:
        row = await self._session.get(DeviceTable, device_id)
        return _to_domain(row) if row is not None else None

    async def list_for_user(self, user_id: uuid.UUID) -> list[Device]:
        result = await self._session.execute(
            select(DeviceTable)
            .where(DeviceTable.user_id == user_id)
            .order_by(DeviceTable.last_seen_at.desc())
        )
        return [_to_domain(row) for row in result.scalars().all()]

    async def update(self, device: Device) -> Device:
        row = await self._session.get(DeviceTable, device.id)
        if row is None:
            raise KeyError(f"no device {device.id} to update")
        row.label = device.label
        row.platform = device.platform
        row.trusted = device.trusted
        row.trusted_until = device.trusted_until
        row.revoked_at = device.revoked_at
        row.last_seen_at = device.last_seen_at or row.last_seen_at
        await self._session.flush()
        return device


__all__ = [
    "DeviceRepository",
    "InMemoryDeviceRepository",
    "SqlDeviceRepository",
]
