"""Event bus with retry, dead-letter, re-drive, and replay semantics (FR-014..018).

``EventBus`` is the protocol application code sees. ``InMemoryEventBus`` is the reference
implementation used locally and in contract tests; a Kafka-backed adapter implements the
same protocol in deployed environments (retry topics + DLQ topics map to the same calls).
Delivery is at-least-once; handlers achieve exactly-once *effect* via the processed-event
ledger (see ledger.py).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from atlas_events.catalog import EventCatalog
from atlas_events.envelope import EventEnvelope

Handler = Callable[[EventEnvelope], Awaitable[None]]

DEFAULT_MAX_ATTEMPTS = 5


@dataclass
class Subscription:
    consumer: str
    event_type: str
    handler: Handler
    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    replay_capable: bool = True


@dataclass
class DeadLetterEntry:
    envelope: EventEnvelope
    consumer: str
    failure_reason: str
    attempts: list[dict[str, Any]] = field(default_factory=list)
    status: str = "dead"  # dead → redriven | discarded
    dead_lettered_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class EventBus(Protocol):
    async def publish(self, envelope: EventEnvelope) -> None: ...

    def subscribe(
        self,
        consumer: str,
        event_type: str,
        handler: Handler,
        *,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        replay_capable: bool = True,
    ) -> None: ...


class InMemoryEventBus:
    """Reference bus: synchronous fan-out with retry → DLQ → re-drive/replay flows."""

    def __init__(self, catalog: EventCatalog | None = None) -> None:
        self._catalog = catalog
        self._subscriptions: list[Subscription] = []
        self._history: list[EventEnvelope] = []
        self._dead_letters: list[DeadLetterEntry] = []

    # -- wiring ------------------------------------------------------------
    def subscribe(
        self,
        consumer: str,
        event_type: str,
        handler: Handler,
        *,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        replay_capable: bool = True,
    ) -> None:
        self._subscriptions.append(
            Subscription(consumer, event_type, handler, max_attempts, replay_capable)
        )

    # -- publish & deliver ---------------------------------------------------
    async def publish(self, envelope: EventEnvelope) -> None:
        if self._catalog is not None:
            self._catalog.validate_payload(envelope.event_type, envelope.payload)
        if not envelope.is_replay:
            self._history.append(envelope)
        for sub in [s for s in self._subscriptions if s.event_type == envelope.event_type]:
            if envelope.is_replay and not sub.replay_capable:
                continue
            await self._deliver(envelope, sub)

    async def _deliver(self, envelope: EventEnvelope, sub: Subscription) -> None:
        attempts: list[dict[str, Any]] = []
        for attempt in range(1, sub.max_attempts + 1):
            try:
                await sub.handler(envelope)
                return
            except Exception as exc:  # noqa: BLE001 — poison events must not crash the bus
                attempts.append(
                    {
                        "attempt": attempt,
                        "at": datetime.now(UTC).isoformat(),
                        "error": str(exc)[:500],
                    }
                )
        self._dead_letters.append(
            DeadLetterEntry(
                envelope=envelope,
                consumer=sub.consumer,
                failure_reason=attempts[-1]["error"] if attempts else "unknown",
                attempts=attempts,
            )
        )

    # -- operator surface (FR-017/018) --------------------------------------
    def dead_letters(self, status: str = "dead") -> list[DeadLetterEntry]:
        return [d for d in self._dead_letters if d.status == status]

    async def redrive(self, event_id: str, consumer: str) -> bool:
        for entry in self._dead_letters:
            if (
                entry.envelope.event_id == event_id
                and entry.consumer == consumer
                and entry.status == "dead"
            ):
                subs = [
                    s
                    for s in self._subscriptions
                    if s.consumer == consumer and s.event_type == entry.envelope.event_type
                ]
                for sub in subs:
                    await self._deliver(entry.envelope, sub)
                entry.status = "redriven"
                return True
        return False

    async def replay(
        self,
        event_type: str,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> int:
        """Re-deliver historical events (marked replay_of) to replay-capable subscribers."""
        replayed = 0
        for envelope in list(self._history):
            if envelope.event_type != event_type:
                continue
            if since and envelope.occurred_at < since:
                continue
            if until and envelope.occurred_at > until:
                continue
            await self.publish(envelope.as_replay())
            replayed += 1
        return replayed

    @property
    def history(self) -> list[EventEnvelope]:
        return list(self._history)
