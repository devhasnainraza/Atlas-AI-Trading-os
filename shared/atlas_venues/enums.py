"""Vocabulary shared by every venue adapter and both trading modules (Spec 03 data-model).

These enums are the *normalized* Atlas vocabulary. Venue-native strings ("GTC", "gtc",
"GoodTillCancel", 1) are translated to and from these values inside each adapter, so no
venue's spelling ever leaks into domain code, the API surface, or the UI.
"""

from __future__ import annotations

from enum import StrEnum


class VenueEnvironment(StrEnum):
    """Which world an order actually reaches.

    Kept on connections, accounts, orders, and positions alike so that simulated and real
    activity are distinguishable on every surface (FR-048, FR-050) and can never be mixed
    inside one aggregate.
    """

    LIVE = "live"
    DEMO = "demo"
    PAPER = "paper"

    @property
    def is_real_money(self) -> bool:
        return self is VenueEnvironment.LIVE


class AssetClass(StrEnum):
    FOREX = "forex"
    CRYPTO = "crypto"
    EQUITY = "equity"
    FUTURE = "future"
    OPTION = "option"
    CFD = "cfd"
    INDEX = "index"
    COMMODITY = "commodity"


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"

    @property
    def opposite(self) -> OrderSide:
        return OrderSide.SELL if self is OrderSide.BUY else OrderSide.BUY


class PositionSide(StrEnum):
    LONG = "long"
    SHORT = "short"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class TimeInForce(StrEnum):
    GTC = "gtc"
    IOC = "ioc"
    FOK = "fok"
    DAY = "day"


class OrderState(StrEnum):
    """Order lifecycle (plan §6).

    ``UNRESOLVED`` is the load-bearing member: when a submission's outcome is unknown, the
    order is parked here and *never* auto-resubmitted (FR-030). Ambiguity is displayed as
    ambiguity — it is never rendered as a fill or as a rejection.
    """

    INTENT = "intent"
    PENDING_CONFIRMATION = "pending_confirmation"
    RISK_CHECKED = "risk_checked"
    SUBMITTING = "submitting"
    WORKING = "working"
    PARTIALLY_FILLED = "partially_filled"
    AMENDING = "amending"
    CANCELING = "canceling"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    UNRESOLVED = "unresolved"

    @property
    def is_terminal(self) -> bool:
        return self in _TERMINAL_STATES

    @property
    def is_open_at_venue(self) -> bool:
        return self in _OPEN_STATES


_TERMINAL_STATES = frozenset(
    {OrderState.FILLED, OrderState.CANCELED, OrderState.REJECTED, OrderState.EXPIRED}
)
_OPEN_STATES = frozenset(
    {
        OrderState.WORKING,
        OrderState.PARTIALLY_FILLED,
        OrderState.AMENDING,
        OrderState.CANCELING,
    }
)


class ConnectionHealth(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    EXPIRED = "expired"
    FAILED = "failed"
    QUARANTINED = "quarantined"

    @property
    def can_trade(self) -> bool:
        return self is ConnectionHealth.HEALTHY


class AccountViewState(StrEnum):
    """How much the operator should trust the account figures on screen."""

    LIVE = "live"
    STALE = "stale"
    UNKNOWN = "unknown"


class DataFreshness(StrEnum):
    FRESH = "fresh"
    STALE = "stale"


class DiscrepancyClass(StrEnum):
    MISSING_LOCALLY = "missing_locally"
    MISSING_AT_VENUE = "missing_at_venue"
    QUANTITY_MISMATCH = "quantity_mismatch"
    PRICE_MISMATCH = "price_mismatch"
    STATE_MISMATCH = "state_mismatch"
    UNKNOWN_ORDER = "unknown_order"


__all__ = [
    "AccountViewState",
    "AssetClass",
    "ConnectionHealth",
    "DataFreshness",
    "DiscrepancyClass",
    "OrderSide",
    "OrderState",
    "OrderType",
    "PositionSide",
    "TimeInForce",
    "VenueEnvironment",
]
