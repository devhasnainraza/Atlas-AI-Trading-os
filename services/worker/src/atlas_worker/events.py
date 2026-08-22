"""Worker event flows: outbox relay loop, retry/DLQ handling, and replay execution.

The relay is transport-agnostic: it drains any ``OutboxStore`` into any ``EventBus``.
Locally that is the in-memory pair; in deployed environments the SQLAlchemy outbox and the
Kafka bus implement the same protocols — this loop does not change.
"""

from __future__ import annotations

import asyncio

from atlas_events.bus import EventBus
from atlas_events.outbox import OutboxStore
from atlas_observability import get_logger

logger = get_logger("atlas_worker.events")


class OutboxRelay:
    """Continuously drains the outbox into the bus (SC-005: no silent event loss)."""

    def __init__(self, outbox: OutboxStore, bus: EventBus, interval_seconds: float = 0.5) -> None:
        self._outbox = outbox
        self._bus = bus
        self._interval = interval_seconds
        self._running = False

    async def run_once(self) -> int:
        published = await self._outbox.relay(self._bus)
        if published:
            logger.info("outbox_relayed", count=published)
        return published

    async def run_forever(self) -> None:
        self._running = True
        while self._running:
            await self.run_once()
            await asyncio.sleep(self._interval)

    def stop(self) -> None:
        self._running = False
