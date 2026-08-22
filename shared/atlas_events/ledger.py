"""Processed-event ledger — exactly-once *effect* on at-least-once delivery.

Consumers call ``already_processed`` / ``mark_processed`` around their handler body (or
use the ``idempotent`` decorator). Duplicate deliveries (retries, replays of already-seen
events) become no-ops.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol

from atlas_events.bus import Handler
from atlas_events.envelope import EventEnvelope


class ProcessedEventLedger(Protocol):
    async def already_processed(self, consumer: str, event_id: str) -> bool: ...

    async def mark_processed(self, consumer: str, event_id: str) -> None: ...


class InMemoryProcessedLedger:
    def __init__(self) -> None:
        self._seen: set[tuple[str, str]] = set()

    async def already_processed(self, consumer: str, event_id: str) -> bool:
        return (consumer, event_id) in self._seen

    async def mark_processed(self, consumer: str, event_id: str) -> None:
        self._seen.add((consumer, event_id))


def idempotent(consumer: str, ledger: ProcessedEventLedger) -> Callable[[Handler], Handler]:
    """Wrap a handler so duplicate (consumer, event_id) deliveries are skipped."""

    def decorator(
        handler: Callable[[EventEnvelope], Awaitable[None]],
    ) -> Callable[[EventEnvelope], Awaitable[None]]:
        async def wrapper(envelope: EventEnvelope) -> None:
            if await ledger.already_processed(consumer, envelope.event_id):
                return
            await handler(envelope)
            await ledger.mark_processed(consumer, envelope.event_id)

        return wrapper

    return decorator
