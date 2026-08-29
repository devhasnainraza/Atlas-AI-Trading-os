"""Normalized venue value objects (Spec 03 plan §2, data-model).

All of these are frozen: an adapter hands back an immutable snapshot, and no downstream
caller can mutate what a venue reported. Every price and quantity is a ``Decimal``
(:mod:`atlas_venues.precision`); floats are rejected at construction, not silently rounded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from atlas_venues.enums import (
    AccountViewState,
    AssetClass,
    OrderSide,
    OrderState,
    OrderType,
    PositionSide,
    TimeInForce,
    VenueEnvironment,
)
from atlas_venues.precision import ZERO, PrecisionError

# --------------------------------------------------------------------------------------
# Capability discovery
# --------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Capabilities:
    """What a venue can actually do, declared by its adapter (FR-002).

    Callers must consult this before offering an action. Nothing in Atlas assumes a
    capability is present because another venue has it — a UI that offers "modify order" on
    a venue whose adapter reports ``supports_amend=False`` is a bug in the caller.
    """

    venue_code: str
    display_name: str
    asset_classes: frozenset[AssetClass]
    order_types: frozenset[OrderType]
    time_in_force: frozenset[TimeInForce]
    environments: frozenset[VenueEnvironment]
    supports_amend: bool = False
    supports_cancel: bool = True
    supports_close_position: bool = False
    supports_streaming_quotes: bool = False
    supports_streaming_account: bool = False
    supports_historical_bars: bool = False
    supports_fractional_quantity: bool = False
    supports_client_order_id: bool = True
    supports_stop_loss_take_profit: bool = False
    supports_short_selling: bool = False
    max_symbols_per_quote_call: int = 1
    max_bars_per_call: int = 500
    requires_sidecar: bool = False
    notes: str = ""

    def supports(self, order_type: OrderType, tif: TimeInForce) -> bool:
        return order_type in self.order_types and tif in self.time_in_force


@dataclass(frozen=True, slots=True)
class InstrumentSpec:
    """A tradable instrument as the venue defines it, plus the Atlas canonical symbol.

    ``venue_symbol`` is what goes on the wire; ``canonical_symbol`` is what the user sees and
    what cross-venue comparisons key on (plan §5). Both are kept because they differ per
    venue ("EURUSD", "EUR_USD", "EURUSD.pro" are all the same instrument).
    """

    venue_code: str
    venue_symbol: str
    canonical_symbol: str
    asset_class: AssetClass
    base_currency: str
    quote_currency: str
    price_precision: int
    quantity_precision: int
    tick_size: Decimal
    quantity_step: Decimal
    min_quantity: Decimal
    max_quantity: Decimal | None = None
    min_notional: Decimal | None = None
    contract_size: Decimal | None = None
    is_tradable: bool = True
    spec_fingerprint: str = ""

    def __post_init__(self) -> None:
        for name in ("tick_size", "quantity_step", "min_quantity"):
            value = getattr(self, name)
            if not isinstance(value, Decimal):
                raise PrecisionError(f"InstrumentSpec.{name} must be Decimal")
            if value <= ZERO:
                raise PrecisionError(f"InstrumentSpec.{name} must be positive")


# --------------------------------------------------------------------------------------
# Market data
# --------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class QuoteTick:
    """A top-of-book snapshot stamped with the venue's own time.

    ``venue_time`` is what freshness is judged against — not our receive time — so a feed
    that silently stops updating is detected rather than trusted (FR-039).
    """

    venue_code: str
    venue_symbol: str
    bid: Decimal
    ask: Decimal
    venue_time: datetime
    received_at: datetime
    bid_size: Decimal | None = None
    ask_size: Decimal | None = None
    last: Decimal | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.bid, Decimal) or not isinstance(self.ask, Decimal):
            raise PrecisionError("QuoteTick bid/ask must be Decimal")
        if self.bid <= ZERO or self.ask <= ZERO:
            raise PrecisionError("QuoteTick bid/ask must be positive")

    @property
    def mid(self) -> Decimal:
        return (self.bid + self.ask) / Decimal(2)

    @property
    def spread(self) -> Decimal:
        return self.ask - self.bid

    def age_seconds(self, now: datetime) -> float:
        return max(0.0, (now - self.venue_time).total_seconds())


@dataclass(frozen=True, slots=True)
class Bar:
    """One OHLCV candle, left-edge stamped, always closed.

    Adapters never emit the in-progress candle: a partial bar that later changes shape would
    make a chart and a backtest disagree about the same timestamp.
    """

    venue_code: str
    venue_symbol: str
    interval: str
    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal | None = None
    is_gap: bool = False

    def __post_init__(self) -> None:
        for name in ("open", "high", "low", "close"):
            if not isinstance(getattr(self, name), Decimal):
                raise PrecisionError(f"Bar.{name} must be Decimal")
        if self.high < self.low:
            raise PrecisionError("Bar.high cannot be below Bar.low")


# --------------------------------------------------------------------------------------
# Account state
# --------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AccountSnapshot:
    """Balances as the venue reported them at ``venue_time``.

    ``view_state`` travels with the numbers so a caller cannot display a cached balance as
    though it were current (FR-017).
    """

    venue_code: str
    venue_account_ref: str
    environment: VenueEnvironment
    currency: str
    balance: Decimal
    equity: Decimal
    venue_time: datetime
    available_margin: Decimal | None = None
    used_margin: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    realized_pnl: Decimal | None = None
    margin_level: Decimal | None = None
    leverage: Decimal | None = None
    view_state: AccountViewState = AccountViewState.LIVE

    def __post_init__(self) -> None:
        for name in ("balance", "equity"):
            if not isinstance(getattr(self, name), Decimal):
                raise PrecisionError(f"AccountSnapshot.{name} must be Decimal")


@dataclass(frozen=True, slots=True)
class VenuePosition:
    """An open position as the venue reports it — the authoritative view (plan §11)."""

    venue_code: str
    venue_account_ref: str
    venue_symbol: str
    side: PositionSide
    quantity: Decimal
    average_entry_price: Decimal
    environment: VenueEnvironment
    venue_time: datetime
    venue_position_ref: str | None = None
    unrealized_pnl: Decimal | None = None
    current_price: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    opened_at: datetime | None = None

    def __post_init__(self) -> None:
        for name in ("quantity", "average_entry_price"):
            if not isinstance(getattr(self, name), Decimal):
                raise PrecisionError(f"VenuePosition.{name} must be Decimal")
        if self.quantity <= ZERO:
            raise PrecisionError("VenuePosition.quantity must be positive; use side for direction")


# --------------------------------------------------------------------------------------
# Execution
# --------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class VenueFill:
    """One execution against an order, keyed by the venue's own fill reference.

    ``venue_fill_ref`` is what makes fill ingestion idempotent: the same fill delivered twice
    by REST poll and WebSocket push must not double-count (FR-029).
    """

    venue_fill_ref: str
    venue_order_ref: str
    quantity: Decimal
    price: Decimal
    venue_time: datetime
    fee: Decimal | None = None
    fee_currency: str | None = None
    is_maker: bool | None = None

    def __post_init__(self) -> None:
        for name in ("quantity", "price"):
            if not isinstance(getattr(self, name), Decimal):
                raise PrecisionError(f"VenueFill.{name} must be Decimal")


@dataclass(frozen=True, slots=True)
class SubmitRequest:
    """A fully-resolved, risk-approved order ready for the wire.

    There is no ``skip_risk`` or ``force`` field, and there never will be: an adapter can only
    be handed a request the risk gate already produced (FR-038, guard test T027).

    ``client_order_id`` is generated *before* the first transmission attempt and reused for
    every follow-up query about that order, which is what makes at-most-once possible
    (FR-026).
    """

    venue_code: str
    venue_account_ref: str
    venue_symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    time_in_force: TimeInForce
    client_order_id: str
    environment: VenueEnvironment
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    reduce_only: bool = False
    label: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.quantity, Decimal):
            raise PrecisionError("SubmitRequest.quantity must be Decimal")
        if self.quantity <= ZERO:
            raise PrecisionError("SubmitRequest.quantity must be positive")
        if self.order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT) and self.limit_price is None:
            raise PrecisionError(f"{self.order_type} requires a limit_price")
        if self.order_type in (OrderType.STOP, OrderType.STOP_LIMIT) and self.stop_price is None:
            raise PrecisionError(f"{self.order_type} requires a stop_price")
        if self.order_type is OrderType.MARKET and self.limit_price is not None:
            raise PrecisionError("market orders must not carry a limit_price")
        if not self.client_order_id:
            raise PrecisionError("SubmitRequest.client_order_id is required for at-most-once")


@dataclass(frozen=True, slots=True)
class VenueOrder:
    """An order as the venue currently sees it — the projection source of truth (plan §11)."""

    venue_code: str
    venue_order_ref: str
    venue_symbol: str
    side: OrderSide
    order_type: OrderType
    state: OrderState
    quantity: Decimal
    filled_quantity: Decimal
    environment: VenueEnvironment
    venue_time: datetime
    client_order_id: str | None = None
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    average_fill_price: Decimal | None = None
    time_in_force: TimeInForce | None = None
    venue_account_ref: str | None = None
    reject_reason: str | None = None
    fills: tuple[VenueFill, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for name in ("quantity", "filled_quantity"):
            if not isinstance(getattr(self, name), Decimal):
                raise PrecisionError(f"VenueOrder.{name} must be Decimal")

    @property
    def remaining_quantity(self) -> Decimal:
        return self.quantity - self.filled_quantity


@dataclass(frozen=True, slots=True)
class SubmitResult:
    """The outcome of a transmission attempt.

    ``accepted=False`` with a populated ``reject_reason`` is a *known* rejection. An unknown
    outcome is never expressed here — adapters raise
    :class:`atlas_venues.errors.AmbiguousOutcomeError` instead, so a caller cannot mistake
    "we don't know" for "it didn't happen".
    """

    accepted: bool
    venue_order_ref: str | None
    client_order_id: str
    state: OrderState
    venue_time: datetime
    filled_quantity: Decimal = ZERO
    average_fill_price: Decimal | None = None
    reject_reason: str | None = None
    venue_error_code: str | None = None
    fills: tuple[VenueFill, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class AmendRequest:
    """A modification to a working order. Only the populated fields change."""

    venue_order_ref: str
    client_order_id: str
    quantity: Decimal | None = None
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None

    def __post_init__(self) -> None:
        if all(
            getattr(self, name) is None
            for name in ("quantity", "limit_price", "stop_price", "stop_loss", "take_profit")
        ):
            raise PrecisionError("AmendRequest must change at least one field")


@dataclass(frozen=True, slots=True)
class RateLimitModel:
    """How a venue meters us, so callers can pace themselves rather than discover limits.

    Weight-based venues (Binance, Bybit) report ``weight_per_window``; simple venues report
    ``requests_per_window``. The token bucket in :mod:`atlas_venues.ratelimit` consumes
    whichever the adapter declares.
    """

    venue_code: str
    window_seconds: float
    requests_per_window: int | None = None
    weight_per_window: int | None = None
    orders_per_window: int | None = None
    burst_allowance: int = 0
    notes: str = ""


@dataclass(frozen=True, slots=True)
class VenueTimeOffset:
    """Measured skew between venue clock and ours (plan §4).

    Every venue timestamp is corrected by this before comparison against Atlas time; without
    it, a venue running two seconds fast makes fresh quotes look stale.
    """

    venue_code: str
    offset_seconds: float
    round_trip_seconds: float
    measured_at: datetime

    @property
    def is_significant(self) -> bool:
        return abs(self.offset_seconds) > 1.0


__all__ = [
    "AccountSnapshot",
    "AmendRequest",
    "Bar",
    "Capabilities",
    "InstrumentSpec",
    "QuoteTick",
    "RateLimitModel",
    "SubmitRequest",
    "SubmitResult",
    "VenueFill",
    "VenueOrder",
    "VenuePosition",
    "VenueTimeOffset",
]
