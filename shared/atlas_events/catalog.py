"""Event catalog (Spec 00 FR-019).

Every event type must be registered with its current schema version before first publish.
The catalog is the machine-readable twin of contracts/platform-events.md; CI compat checks
diff against it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from atlas_core.errors import ValidationError


@dataclass(frozen=True)
class EventTypeDef:
    event_type: str
    schema_version: str
    producer: str
    description: str
    required_payload_fields: tuple[str, ...] = field(default=())


class EventCatalog:
    def __init__(self) -> None:
        self._types: dict[str, EventTypeDef] = {}

    def register(self, definition: EventTypeDef) -> None:
        existing = self._types.get(definition.event_type)
        if existing and existing.schema_version != definition.schema_version:
            raise ValidationError(
                f"Event type '{definition.event_type}' already registered with a "
                f"different schema version; breaking changes require a new .v2 type."
            )
        self._types[definition.event_type] = definition

    def get(self, event_type: str) -> EventTypeDef:
        try:
            return self._types[event_type]
        except KeyError as exc:
            raise ValidationError(f"Unknown event type '{event_type}' — register it first") from exc

    def validate_payload(self, event_type: str, payload: dict[str, Any]) -> None:
        definition = self.get(event_type)
        missing = [f for f in definition.required_payload_fields if f not in payload]
        if missing:
            raise ValidationError(
                f"Event '{event_type}' payload missing required fields: {missing}"
            )

    def types(self) -> list[str]:
        return sorted(self._types)


#: Process-wide catalog, seeded with the foundation event types.
catalog = EventCatalog()

_FOUNDATION_EVENTS = [
    EventTypeDef(
        "atlas.platform.module.registered",
        "1.0.0",
        "api",
        "Module composed into the platform at startup",
        ("name", "version"),
    ),
    EventTypeDef(
        "atlas.platform.event.dead_lettered",
        "1.0.0",
        "worker",
        "An event exhausted retries and moved to the DLQ",
        ("event_id", "consumer"),
    ),
    EventTypeDef(
        "atlas.platform.event.redriven",
        "1.0.0",
        "api",
        "A dead-lettered event was re-driven by an operator",
        ("event_id", "consumer"),
    ),
    EventTypeDef(
        "atlas.platform.replay.started",
        "1.0.0",
        "api",
        "An event replay was initiated",
        ("replay_id", "event_type"),
    ),
    EventTypeDef(
        "atlas.platform.replay.completed",
        "1.0.0",
        "worker",
        "An event replay finished",
        ("replay_id", "events_replayed"),
    ),
    EventTypeDef(
        "atlas.platform.flag.changed",
        "1.0.0",
        "api",
        "A feature flag definition changed",
        ("flag_key",),
    ),
    EventTypeDef(
        "atlas.sample.echo.requested",
        "1.0.0",
        "api",
        "Throwaway sample-module proof event",
        ("message_length",),
    ),
]

for _definition in _FOUNDATION_EVENTS:
    catalog.register(_definition)


# -- Spec 03: trading (contracts/trading-events.md) ------------------------------------------
#
# ``required_payload_fields`` is deliberately narrow: the identifiers a consumer cannot act
# without. Listing every optional field here would make an additive payload change a breaking
# one, which is the opposite of what the catalog is for.
_TRADING_EVENTS = [
    EventTypeDef(
        "atlas.trading.venue.connected",
        "1.0.0",
        "api",
        "A venue connection was established and stored",
        ("connection_id", "venue_code", "environment"),
    ),
    EventTypeDef(
        "atlas.trading.venue.verified",
        "1.0.0",
        "api",
        "Connection credentials verified; granted capabilities recorded",
        ("connection_id", "capability_version"),
    ),
    EventTypeDef(
        "atlas.trading.venue.degraded",
        "1.0.0",
        "api",
        "Connection health dropped below healthy",
        ("connection_id", "health", "reason_code"),
    ),
    EventTypeDef(
        "atlas.trading.venue.quarantined",
        "1.0.0",
        "api",
        "Connection quarantined; routing stopped pending operator action",
        ("connection_id", "cause"),
    ),
    EventTypeDef(
        "atlas.trading.venue.disconnected",
        "1.0.0",
        "api",
        "Connection removed by its owner or an operator",
        ("connection_id", "actor_type"),
    ),
    EventTypeDef(
        "atlas.trading.account.synced",
        "1.0.0",
        "worker",
        "Venue account balances/equity refreshed from the venue",
        ("venue_account_id", "view_state", "synced_at"),
    ),
    EventTypeDef(
        "atlas.trading.order.intent_created",
        "1.0.0",
        "api",
        "An order intent passed the risk gate and awaits confirmation",
        ("intent_id", "decision", "expires_at"),
    ),
    EventTypeDef(
        "atlas.trading.order.intent_invalidated",
        "1.0.0",
        "api",
        "An intent can no longer be confirmed",
        ("intent_id", "reason"),
    ),
    EventTypeDef(
        "atlas.trading.order.rejected_by_risk",
        "1.0.0",
        "api",
        "The risk gate refused an intent",
        ("intent_id", "breached_rules", "decision"),
    ),
    EventTypeDef(
        "atlas.trading.order.confirmed",
        "1.0.0",
        "api",
        "A human (or an in-scope mandate) authorized submission",
        ("intent_id", "order_id", "client_order_id"),
    ),
    EventTypeDef(
        "atlas.trading.order.submitted",
        "1.0.0",
        "api",
        "The order was handed to the venue adapter",
        ("order_id", "client_order_id", "submitted_at"),
    ),
    EventTypeDef(
        "atlas.trading.order.accepted",
        "1.0.0",
        "api",
        "The venue acknowledged the order",
        ("order_id", "venue_order_id"),
    ),
    EventTypeDef(
        "atlas.trading.order.partially_filled",
        "1.0.0",
        "worker",
        "A partial fill was applied",
        ("order_id", "filled_quantity", "remaining_quantity"),
    ),
    EventTypeDef(
        "atlas.trading.order.filled",
        "1.0.0",
        "worker",
        "The order filled completely",
        ("order_id", "filled_quantity", "average_fill_price"),
    ),
    EventTypeDef(
        "atlas.trading.order.amended",
        "1.0.0",
        "api",
        "An amendment was attempted; accepted flag carries the outcome",
        ("order_id", "changes", "accepted"),
    ),
    EventTypeDef(
        "atlas.trading.order.canceled",
        "1.0.0",
        "api",
        "The order was canceled",
        ("order_id", "actor"),
    ),
    EventTypeDef(
        "atlas.trading.order.rejected",
        "1.0.0",
        "api",
        "The venue rejected the order; reason is sanitized",
        ("order_id", "error_class"),
    ),
    EventTypeDef(
        "atlas.trading.order.expired",
        "1.0.0",
        "worker",
        "The order expired under its time-in-force",
        ("order_id", "time_in_force"),
    ),
    EventTypeDef(
        "atlas.trading.order.unresolved",
        "1.0.0",
        "api",
        "Submission outcome is unknown; never auto-retried, reconciliation decides",
        ("order_id", "client_order_id", "unresolved_since"),
    ),
    EventTypeDef(
        "atlas.trading.order.resolved",
        "1.0.0",
        "worker",
        "Reconciliation determined the true state of an unresolved order",
        ("order_id", "resolved_state", "reconciliation_run_id"),
    ),
    EventTypeDef(
        "atlas.trading.position.opened",
        "1.0.0",
        "worker",
        "A position appeared, from our fill or from outside Atlas",
        ("position_id", "side", "quantity"),
    ),
    EventTypeDef(
        "atlas.trading.position.updated",
        "1.0.0",
        "worker",
        "Position quantity, entry price, or protective levels changed",
        ("position_id", "quantity"),
    ),
    EventTypeDef(
        "atlas.trading.position.closed",
        "1.0.0",
        "worker",
        "The position went flat",
        ("position_id", "realized_pnl", "closed_at"),
    ),
    EventTypeDef(
        "atlas.trading.risk.limit_breached",
        "1.0.0",
        "api",
        "A risk rule blocked an order",
        ("rule", "limit_value", "actual_value"),
    ),
    EventTypeDef(
        "atlas.trading.risk.policy_changed",
        "1.0.0",
        "api",
        "A risk policy was edited",
        ("scope", "version", "effective_from"),
    ),
    EventTypeDef(
        "atlas.trading.risk.kill_switch_engaged",
        "1.0.0",
        "api",
        "Trading stopped for a scope; every order path must invalidate its cache",
        ("scope", "reason", "actor_type"),
    ),
    EventTypeDef(
        "atlas.trading.risk.kill_switch_released",
        "1.0.0",
        "api",
        "A kill switch was lifted",
        ("scope", "target", "actor_type"),
    ),
    EventTypeDef(
        "atlas.trading.mandate.granted",
        "1.0.0",
        "api",
        "A bounded automation mandate was granted",
        ("mandate_id", "expires_at"),
    ),
    EventTypeDef(
        "atlas.trading.mandate.consumed",
        "1.0.0",
        "api",
        "Mandate allowance was drawn down",
        ("mandate_id", "committed_notional", "orders_used"),
    ),
    EventTypeDef(
        "atlas.trading.mandate.revoked",
        "1.0.0",
        "api",
        "A mandate is no longer usable",
        ("mandate_id", "reason"),
    ),
    EventTypeDef(
        "atlas.trading.reconciliation.completed",
        "1.0.0",
        "worker",
        "A reconciliation run finished",
        ("run_id", "connection_id", "trigger", "outcome"),
    ),
    EventTypeDef(
        "atlas.trading.reconciliation.discrepancy_found",
        "1.0.0",
        "worker",
        "Local state disagreed with the venue",
        ("run_id", "entity_type", "discrepancy_class"),
    ),
    EventTypeDef(
        "atlas.trading.reconciliation.escalated",
        "1.0.0",
        "worker",
        "A discrepancy could not be resolved automatically; routing is held",
        ("run_id", "discrepancy_id", "routing_hold"),
    ),
    EventTypeDef(
        "atlas.trading.paper.reset",
        "1.0.0",
        "api",
        "A paper account was reset to its starting balance",
        ("connection_id", "starting_balance", "reset_count"),
    ),
]

# -- Spec 03: market data --------------------------------------------------------------------
_MARKETDATA_EVENTS = [
    EventTypeDef(
        "atlas.marketdata.subscription.created",
        "1.0.0",
        "api",
        "A user subscribed an instrument for streaming",
        ("subscription_id", "instrument"),
    ),
    EventTypeDef(
        "atlas.marketdata.subscription.removed",
        "1.0.0",
        "api",
        "A subscription was released",
        ("subscription_id",),
    ),
    EventTypeDef(
        "atlas.marketdata.quote.stale",
        "1.0.0",
        "worker",
        "A quote aged past its freshness limit; the risk gate must fail closed",
        ("venue_code", "instrument", "age_seconds"),
    ),
    EventTypeDef(
        "atlas.marketdata.feed.degraded",
        "1.0.0",
        "worker",
        "A market data feed stopped delivering",
        ("connection_id", "venue_code", "reason_code"),
    ),
    EventTypeDef(
        "atlas.marketdata.feed.recovered",
        "1.0.0",
        "worker",
        "A feed reconnected; gap length says whether backfill is needed",
        ("connection_id", "gap_seconds", "backfill_required"),
    ),
    EventTypeDef(
        "atlas.marketdata.candle.closed",
        "1.0.0",
        "worker",
        "A bar closed and was persisted",
        ("instrument", "timeframe", "open_time"),
    ),
    EventTypeDef(
        "atlas.marketdata.instrument.spec_changed",
        "1.0.0",
        "worker",
        "Venue instrument specs moved; trading must re-validate working orders",
        ("instrument_id", "spec_version", "changed_fields"),
    ),
]

for _definition in (*_TRADING_EVENTS, *_MARKETDATA_EVENTS):
    catalog.register(_definition)
