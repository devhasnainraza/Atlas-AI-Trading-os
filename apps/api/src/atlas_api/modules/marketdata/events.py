"""Market data event handlers.

The two that matter are the *bad news* handlers. A quote going stale and a feed degrading are
both inputs the risk gate fails closed on, so they are logged loudly enough that an operator
correlating a burst of order refusals finds the cause without being told where to look.
"""

from __future__ import annotations

from atlas_events import EventEnvelope
from atlas_observability import get_logger

logger = get_logger("atlas_api.modules.marketdata")


async def on_quote_stale(envelope: EventEnvelope) -> None:
    """A symbol's latest quote aged out of its freshness window (FR-018).

    Warning, not error: a quiet market is a legitimate cause. It becomes an error only if the
    feed itself is down, which arrives as ``feed.degraded``.
    """
    logger.warning(
        "quote_stale",
        event_id=envelope.event_id,
        replay=envelope.is_replay,
        venue_code=envelope.payload.get("venue_code"),
        canonical_symbol=envelope.payload.get("canonical_symbol"),
        age_seconds=envelope.payload.get("age_seconds"),
    )


async def on_feed_degraded(envelope: EventEnvelope) -> None:
    """A feed stopped delivering. Every quote it owns is now unusable for pricing."""
    logger.error(
        "feed_degraded",
        event_id=envelope.event_id,
        venue_code=envelope.payload.get("venue_code"),
        reason=envelope.payload.get("reason"),
        degraded_since=envelope.payload.get("degraded_since"),
    )


async def on_feed_recovered(envelope: EventEnvelope) -> None:
    """A feed came back.

    Recovery is logged at info but is never itself treated as proof that prices are current —
    the next quote's own timestamp decides that. A reconnect says the socket is open, not that
    the gap it left has been filled.
    """
    logger.info(
        "feed_recovered",
        event_id=envelope.event_id,
        venue_code=envelope.payload.get("venue_code"),
        downtime_seconds=envelope.payload.get("downtime_seconds"),
    )


__all__ = ["on_feed_degraded", "on_feed_recovered", "on_quote_stale"]
