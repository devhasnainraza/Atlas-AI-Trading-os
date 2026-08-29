"""Trading event handlers.

Handlers are idempotent by construction: every one runs under
:func:`atlas_events.ledger.idempotent` so a redelivered event cannot double-apply. That matters
more here than anywhere else in the platform — an at-least-once fill event applied twice would
double a position, and the position is what the next risk check reads.
"""

from __future__ import annotations

from atlas_events import EventEnvelope
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


__all__ = ["on_kill_switch_engaged", "on_order_unresolved", "on_paper_reset"]
