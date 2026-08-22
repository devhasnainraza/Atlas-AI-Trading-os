"""Transactional outbox (plan §7 — no lost or phantom events, SC-005).

Services write events to the outbox in the same transaction as their state change; the
relay (worker) publishes pending entries to the bus and marks them published. The in-memory
store is the reference; a SQLAlchemy-backed store lands with the first persistent module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from atlas_events.bus import EventBus
from atlas_events.envelope import EventEnvelope


@dataclass
class OutboxEntry:
    envelope: EventEnvelope
    status: str = "pending"  # pending → published | failed
    published_at: datetime | None = None
    failure_reason: str | None = None
    added_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class OutboxStore(Protocol):
    def add(self, envelope: EventEnvelope) -> None: ...

    def pending(self) -> list[OutboxEntry]: ...

    async def relay(self, bus: EventBus) -> int: ...


class InMemoryOutbox:
    def __init__(self) -> None:
        self._entries: list[OutboxEntry] = []

    def add(self, envelope: EventEnvelope) -> None:
        self._entries.append(OutboxEntry(envelope=envelope))

    def pending(self) -> list[OutboxEntry]:
        return [e for e in self._entries if e.status == "pending"]

    def all_entries(self) -> list[OutboxEntry]:
        return list(self._entries)

    async def relay(self, bus: EventBus) -> int:
        """Publish pending entries; failures stay pending for the next relay pass."""
        published = 0
        for entry in self.pending():
            try:
                await bus.publish(entry.envelope)
            except Exception as exc:  # noqa: BLE001 — relay must survive bad entries
                entry.failure_reason = str(exc)[:500]
                continue
            entry.status = "published"
            entry.published_at = datetime.now(UTC)
            published += 1
        return published
