"""Sample service layer — the only layer that touches repositories and publishes events."""

from __future__ import annotations

from atlas_core.correlation import get_correlation_id
from atlas_events import EventEnvelope, InMemoryEventBus, InMemoryOutbox


class SampleService:
    def __init__(self, outbox: InMemoryOutbox, bus: InMemoryEventBus) -> None:
        self._outbox = outbox
        self._bus = bus

    async def echo(self, message: str) -> str:
        """Echo the message and publish the proof event through the outbox → relay path."""
        self._outbox.add(
            EventEnvelope(
                event_type="atlas.sample.echo.requested",
                producer="atlas-api.sample",
                payload={"message_length": len(message)},
            )
        )
        # In deployed environments the worker relays the outbox; locally we relay inline
        # so the pipeline is observable without a separate process.
        await self._outbox.relay(self._bus)
        return get_correlation_id()
