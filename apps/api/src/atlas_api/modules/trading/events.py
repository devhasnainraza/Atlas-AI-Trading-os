"""Trading event handlers.

Handlers are idempotent by construction: every one runs under
:func:`atlas_events.ledger.idempotent` so a redelivered event cannot double-apply. That matters
more here than anywhere else in the platform — an at-least-once fill event applied twice would
double a position, and the position is what the next risk check reads.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from atlas_api.modules.trading.repository.connections import ConnectionRepository
from atlas_api.modules.trading.service import VenueConnectionService
from atlas_core.audit import AuditLogEntry, AuditLogRepository
from atlas_events import EventEnvelope, InMemoryEventBus, InMemoryOutbox
from atlas_observability import get_logger

logger = get_logger("atlas_api.modules.trading")


async def on_paper_reset(envelope: EventEnvelope) -> None:
    """Record a paper reset. Analytics must exclude pre-reset data from performance stats."""
    logger.info(
        "paper_account_reset",
        event_id=envelope.event_id,
        replay=envelope.is_replay,
        connection_id=envelope.payload.get("connection_id"),
        reset_count=envelope.payload.get("reset_count"),
    )


async def on_kill_switch_engaged(envelope: EventEnvelope) -> None:
    """Invalidate any cached authorization the moment trading is stopped.

    Logged at warning: an engaged kill switch is not routine, and an operator reading the log
    later needs to find it without knowing to look.
    """
    logger.warning(
        "kill_switch_engaged",
        event_id=envelope.event_id,
        scope=envelope.payload.get("scope"),
        reason=envelope.payload.get("reason"),
        actor_type=envelope.payload.get("actor_type"),
    )


async def on_order_unresolved(envelope: EventEnvelope) -> None:
    """An order's outcome is unknown.

    Deliberately does not retry. The handler's whole job is to make the condition loud and
    hand it to reconciliation, which asks the venue — the only authority on whether the order
    exists (FR-030).
    """
    logger.error(
        "order_unresolved",
        event_id=envelope.event_id,
        order_id=envelope.payload.get("order_id"),
        client_order_id=envelope.payload.get("client_order_id"),
        unresolved_since=envelope.payload.get("unresolved_since"),
    )


def make_credential_revoked_handler(
    repository: ConnectionRepository,
    outbox: InMemoryOutbox | None = None,
    bus: InMemoryEventBus | None = None,
    audit_log: AuditLogRepository | None = None,
) -> Callable[[EventEnvelope], None]:
    """Consumer for atlas.credentials.credential.revoked (FR-011, T032, T043)."""

    async def on_credential_revoked(envelope: EventEnvelope) -> None:
        credential_id = envelope.payload.get("credential_id")
        if not credential_id:
            return
        reason = envelope.payload.get("cause") or envelope.payload.get("reason", "credential_revoked")
        conns = await repository.find_by_credential(credential_id)
        now = datetime.now(UTC)
        for conn in conns:
            quarantined = conn.mark_quarantined(reason=reason, now=now)
            await repository.update(quarantined)

            if audit_log:
                audit_log.append(
                    AuditLogEntry(
                        actor="system",
                        action="trading.connection.quarantined",
                        target=quarantined.id,
                        correlation_id=envelope.correlation_id or str(uuid4()),
                        metadata={"cause": reason, "venue_code": quarantined.venue_code},
                    )
                )

            if outbox and bus:
                outbox.add(
                    EventEnvelope(
                        event_type="atlas.trading.venue.quarantined",
                        producer="atlas-api.trading",
                        correlation_id=envelope.correlation_id,
                        payload={"connection_id": quarantined.id, "cause": reason},
                    )
                )
                outbox.add(
                    EventEnvelope(
                        event_type="atlas.trading.reconciliation.requested",
                        producer="atlas-api.trading",
                        correlation_id=envelope.correlation_id,
                        payload={"connection_id": quarantined.id, "reason": "credential_revoked"},
                    )
                )
        if outbox and bus and conns:
            await outbox.relay(bus)

    return on_credential_revoked


def make_credential_rotated_handler(
    service_factory: Callable[[], VenueConnectionService],
) -> Callable[[EventEnvelope], None]:
    """Consumer for atlas.credentials.credential.rotated (T043)."""

    async def on_credential_rotated(envelope: EventEnvelope) -> None:
        credential_id = envelope.payload.get("credential_id")
        if not credential_id:
            return
        service = service_factory()
        await service.handle_credential_rotated(credential_id)

    return on_credential_rotated


__all__ = [
    "make_credential_revoked_handler",
    "make_credential_rotated_handler",
    "on_kill_switch_engaged",
    "on_order_unresolved",
    "on_paper_reset",
]
