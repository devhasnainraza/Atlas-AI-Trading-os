"""Paper trading as a venue adapter (Spec 03 research decision 8, plan §9, US6).

Paper trading is implemented *as* a :class:`~atlas_venues.protocol.VenueAdapter` rather than as
a branch inside the order service. That is the whole point of the decision: an order taking a
different code path in paper mode would mean paper mode never exercises the code that runs
with real money. Here, the risk gate, the confirmation step, the submission ledger, and the
projection logic are all identical — only the adapter behind them differs.

The engine is deterministic. Fills are computed from the quote the caller supplied, and there
is no randomness anywhere, so a paper run is reproducible and a test asserting a fill price is
stable. Slippage and latency are configurable but fixed.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence
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
from atlas_venues.errors import (
    ErrorClass,
    TerminalRejectionError,
    UnsupportedCapabilityError,
    VenueError,
)
from atlas_venues.models import (
    AccountSnapshot,
    AmendRequest,
    Bar,
    Capabilities,
    InstrumentSpec,
    QuoteTick,
    RateLimitModel,
    SubmitRequest,
    SubmitResult,
    VenueFill,
    VenueOrder,
    VenuePosition,
    VenueTimeOffset,
)
from atlas_venues.precision import ZERO, notional, validate_price, validate_quantity
from atlas_venues.ratelimit import DEFAULT_RATE_LIMIT_MODELS
from atlas_venues.registry import AdapterContext
from atlas_venues.timing import Clock, SystemClock

PAPER_VENUE_CODE = "paper"


@dataclass(frozen=True, slots=True)
class PaperFillModel:
    """How the simulator fills orders.

    Defaults are deliberately pessimistic — crossing the spread and paying slippage — because
    a simulator that is kinder than reality teaches a strategy the wrong lesson.
    """

    slippage_bps: Decimal = Decimal("1")
    commission_bps: Decimal = Decimal("0")
    latency_seconds: float = 0.0
    reject_when_quote_missing: bool = True
    partial_fill_ratio: Decimal | None = None

    def fill_price(self, side: OrderSide, quote: QuoteTick) -> Decimal:
        """Cross the spread, then add slippage against the taker."""
        base = quote.ask if side is OrderSide.BUY else quote.bid
        slip = base * self.slippage_bps / Decimal("10000")
        return base + slip if side is OrderSide.BUY else base - slip


@dataclass
class _PaperOrder:
    request: SubmitRequest
    venue_order_ref: str
    state: OrderState
    filled_quantity: Decimal
    created_at: datetime
    updated_at: datetime
    fills: list[VenueFill] = field(default_factory=list)
    reject_reason: str | None = None

    @property
    def average_fill_price(self) -> Decimal | None:
        if not self.fills:
            return None
        gross = sum((f.price * f.quantity for f in self.fills), ZERO)
        return gross / self.filled_quantity if self.filled_quantity > ZERO else None


@dataclass
class _PaperPosition:
    venue_symbol: str
    side: PositionSide
    quantity: Decimal
    average_entry_price: Decimal
    opened_at: datetime
    venue_position_ref: str


class PaperEngine:
    """The simulated venue's books.

    One engine per paper account. Holds cash, positions, and orders; applies fills against a
    quote source supplied by the caller. Shared by every :class:`PaperAdapter` bound to the
    same account so two connections see one consistent book.
    """

    def __init__(
        self,
        *,
        account_ref: str,
        starting_balance: Decimal,
        currency: str = "USD",
        fill_model: PaperFillModel | None = None,
        clock: Clock | None = None,
    ) -> None:
        if not isinstance(starting_balance, Decimal):
            raise TypeError("starting_balance must be Decimal")
        self.account_ref = account_ref
        self.currency = currency
        self.fill_model = fill_model or PaperFillModel()
        self._clock = clock or SystemClock()
        self._starting_balance = starting_balance
        self._balance = starting_balance
        self._realized_pnl = ZERO
        self._orders: dict[str, _PaperOrder] = {}
        self._by_client_id: dict[str, str] = {}
        self._positions: dict[str, _PaperPosition] = {}
        self._quotes: dict[str, QuoteTick] = {}
        self._instruments: dict[str, InstrumentSpec] = {}
        self._seq = 0

    # -- Wiring ------------------------------------------------------------------------

    def set_quote(self, quote: QuoteTick) -> None:
        self._quotes[quote.venue_symbol] = quote

    def set_instrument(self, spec: InstrumentSpec) -> None:
        self._instruments[spec.venue_symbol] = spec

    def reset(self, *, starting_balance: Decimal | None = None) -> None:
        """Clear the book (FR-051). Audit history lives outside the engine and survives this."""
        self._balance = starting_balance if starting_balance is not None else self._starting_balance
        if starting_balance is not None:
            self._starting_balance = starting_balance
        self._realized_pnl = ZERO
        self._orders.clear()
        self._by_client_id.clear()
        self._positions.clear()
        self._seq = 0

    # -- Reads -------------------------------------------------------------------------

    def instruments(self) -> tuple[InstrumentSpec, ...]:
        return tuple(self._instruments.values())

    def quote(self, venue_symbol: str) -> QuoteTick | None:
        return self._quotes.get(venue_symbol)

    def order(self, *, venue_order_ref: str | None, client_order_id: str | None) -> _PaperOrder:
        if venue_order_ref and venue_order_ref in self._orders:
            return self._orders[venue_order_ref]
        if client_order_id and client_order_id in self._by_client_id:
            return self._orders[self._by_client_id[client_order_id]]
        raise TerminalRejectionError(
            "unknown order", venue_code=PAPER_VENUE_CODE, venue_error_code="PAPER_UNKNOWN_ORDER"
        )

    def open_orders(self) -> tuple[_PaperOrder, ...]:
        return tuple(o for o in self._orders.values() if o.state.is_open_at_venue)

    def positions(self) -> tuple[_PaperPosition, ...]:
        return tuple(self._positions.values())

    def equity(self) -> Decimal:
        """Cash plus unrealized P&L, marked against the latest quote we were given."""
        return self._balance + sum((self._unrealized(p) for p in self._positions.values()), ZERO)

    @property
    def balance(self) -> Decimal:
        return self._balance

    @property
    def realized_pnl(self) -> Decimal:
        return self._realized_pnl

    # -- Writes ------------------------------------------------------------------------

    def submit(self, request: SubmitRequest) -> _PaperOrder:
        """Accept and (for market orders) immediately fill.

        A duplicate ``client_order_id`` returns the *existing* order rather than creating a
        second one. Real venues behave this way, and the conformance suite asserts it, so the
        simulator cannot be the reason a duplicate-submission bug goes unnoticed (FR-026).
        """
        now = self._clock.now()
        existing = self._by_client_id.get(request.client_order_id)
        if existing is not None:
            return self._orders[existing]

        spec = self._instruments.get(request.venue_symbol)
        if spec is not None:
            validate_quantity(
                request.quantity,
                minimum=spec.min_quantity,
                maximum=spec.max_quantity,
                step=spec.quantity_step,
            )
            if request.limit_price is not None:
                validate_price(
                    request.limit_price,
                    tick_size=spec.tick_size,
                    precision=spec.price_precision,
                    field="limit_price",
                )

        self._seq += 1
        order = _PaperOrder(
            request=request,
            venue_order_ref=f"PAPER-{self._seq:08d}",
            state=OrderState.WORKING,
            filled_quantity=ZERO,
            created_at=now,
            updated_at=now,
        )
        self._orders[order.venue_order_ref] = order
        self._by_client_id[request.client_order_id] = order.venue_order_ref

        quote = self._quotes.get(request.venue_symbol)
        if quote is None:
            if self.fill_model.reject_when_quote_missing:
                order.state = OrderState.REJECTED
                order.reject_reason = "no quote available for instrument in the simulator"
                order.updated_at = now
            return order

        if request.order_type is OrderType.MARKET:
            self._apply_fill(order, quote, now)
        elif request.order_type is OrderType.LIMIT and self._limit_is_crossable(request, quote):
            self._apply_fill(order, quote, now, price=request.limit_price)
        # Stop and non-crossable limit orders stay working until a later quote triggers them.
        return order

    def on_quote(self, quote: QuoteTick) -> tuple[_PaperOrder, ...]:
        """Feed a new quote in and fill whatever it triggers. Returns the orders that changed."""
        self.set_quote(quote)
        now = self._clock.now()
        changed: list[_PaperOrder] = []
        for order in list(self._orders.values()):
            if not order.state.is_open_at_venue:
                continue
            if order.request.venue_symbol != quote.venue_symbol:
                continue
            req = order.request
            if req.order_type is OrderType.LIMIT and self._limit_is_crossable(req, quote):
                self._apply_fill(order, quote, now, price=req.limit_price)
                changed.append(order)
            elif req.order_type in (OrderType.STOP, OrderType.STOP_LIMIT) and self._stop_triggered(
                req, quote
            ):
                price = req.limit_price if req.order_type is OrderType.STOP_LIMIT else None
                self._apply_fill(order, quote, now, price=price)
                changed.append(order)
        return tuple(changed)

    def cancel(self, order: _PaperOrder) -> _PaperOrder:
        """Cancel a working order. Cancelling a terminal order is a no-op, not an error."""
        if order.state.is_terminal:
            return order
        order.state = OrderState.CANCELED
        order.updated_at = self._clock.now()
        return order

    def amend(self, order: _PaperOrder, changes: AmendRequest) -> _PaperOrder:
        if order.state.is_terminal:
            raise TerminalRejectionError(
                f"cannot amend an order in state {order.state}",
                venue_code=PAPER_VENUE_CODE,
                venue_error_code="PAPER_ORDER_TERMINAL",
            )
        req = order.request
        order.request = SubmitRequest(
            venue_code=req.venue_code,
            venue_account_ref=req.venue_account_ref,
            venue_symbol=req.venue_symbol,
            side=req.side,
            order_type=req.order_type,
            quantity=changes.quantity if changes.quantity is not None else req.quantity,
            time_in_force=req.time_in_force,
            client_order_id=req.client_order_id,
            environment=req.environment,
            limit_price=changes.limit_price if changes.limit_price is not None else req.limit_price,
            stop_price=changes.stop_price if changes.stop_price is not None else req.stop_price,
            stop_loss=changes.stop_loss if changes.stop_loss is not None else req.stop_loss,
            take_profit=(
                changes.take_profit if changes.take_profit is not None else req.take_profit
            ),
            reduce_only=req.reduce_only,
            label=req.label,
        )
        order.updated_at = self._clock.now()
        quote = self._quotes.get(req.venue_symbol)
        if quote is not None and self._limit_is_crossable(order.request, quote):
            self._apply_fill(order, quote, order.updated_at, price=order.request.limit_price)
        return order

    def close_position(self, venue_position_ref: str, quantity: Decimal | None) -> _PaperOrder:
        position = next(
            (p for p in self._positions.values() if p.venue_position_ref == venue_position_ref),
            None,
        )
        if position is None:
            raise TerminalRejectionError(
                "unknown position",
                venue_code=PAPER_VENUE_CODE,
                venue_error_code="PAPER_UNKNOWN_POSITION",
            )
        close_qty = quantity if quantity is not None else position.quantity
        self._seq += 1
        request = SubmitRequest(
            venue_code=PAPER_VENUE_CODE,
            venue_account_ref=self.account_ref,
            venue_symbol=position.venue_symbol,
            side=(OrderSide.SELL if position.side is PositionSide.LONG else OrderSide.BUY),
            order_type=OrderType.MARKET,
            quantity=close_qty,
            time_in_force=TimeInForce.IOC,
            client_order_id=f"paper-close-{self._seq:08d}",
            environment=VenueEnvironment.PAPER,
            reduce_only=True,
        )
        return self.submit(request)

    # -- Internals ---------------------------------------------------------------------

    def _limit_is_crossable(self, req: SubmitRequest, quote: QuoteTick) -> bool:
        if req.limit_price is None:
            return False
        if req.side is OrderSide.BUY:
            return quote.ask <= req.limit_price
        return quote.bid >= req.limit_price

    def _stop_triggered(self, req: SubmitRequest, quote: QuoteTick) -> bool:
        if req.stop_price is None:
            return False
        if req.side is OrderSide.BUY:
            return quote.ask >= req.stop_price
        return quote.bid <= req.stop_price

    def _apply_fill(
        self,
        order: _PaperOrder,
        quote: QuoteTick,
        now: datetime,
        *,
        price: Decimal | None = None,
    ) -> None:
        req = order.request
        remaining = req.quantity - order.filled_quantity
        if remaining <= ZERO:
            return
        ratio = self.fill_model.partial_fill_ratio
        fill_qty = remaining if ratio is None else min(remaining, req.quantity * ratio)
        fill_price = price if price is not None else self.fill_model.fill_price(req.side, quote)
        spec = self._instruments.get(req.venue_symbol)
        contract_size = spec.contract_size if spec else None
        gross = notional(fill_qty, fill_price, contract_size=contract_size)
        fee = gross * self.fill_model.commission_bps / Decimal("10000")

        self._seq += 1
        order.fills.append(
            VenueFill(
                venue_fill_ref=f"PAPERFILL-{self._seq:08d}",
                venue_order_ref=order.venue_order_ref,
                quantity=fill_qty,
                price=fill_price,
                venue_time=now,
                fee=fee,
                fee_currency=self.currency,
                is_maker=price is not None,
            )
        )
        order.filled_quantity += fill_qty
        order.state = (
            OrderState.FILLED
            if order.filled_quantity >= req.quantity
            else OrderState.PARTIALLY_FILLED
        )
        order.updated_at = now
        self._balance -= fee
        self._apply_to_position(req, fill_qty, fill_price, now, contract_size)

    def _apply_to_position(
        self,
        req: SubmitRequest,
        quantity: Decimal,
        price: Decimal,
        now: datetime,
        contract_size: Decimal | None,
    ) -> None:
        key = req.venue_symbol
        incoming = PositionSide.LONG if req.side is OrderSide.BUY else PositionSide.SHORT
        existing = self._positions.get(key)

        if existing is None:
            self._seq += 1
            self._positions[key] = _PaperPosition(
                venue_symbol=key,
                side=incoming,
                quantity=quantity,
                average_entry_price=price,
                opened_at=now,
                venue_position_ref=f"PAPERPOS-{self._seq:08d}",
            )
            return

        if existing.side is incoming:
            total = existing.quantity + quantity
            existing.average_entry_price = (
                existing.average_entry_price * existing.quantity + price * quantity
            ) / total
            existing.quantity = total
            return

        # Opposing fill: realize P&L on the closed portion, then flip if it over-closes.
        closed = min(existing.quantity, quantity)
        direction = Decimal(1) if existing.side is PositionSide.LONG else Decimal(-1)
        pnl = (price - existing.average_entry_price) * closed * direction
        if contract_size is not None:
            pnl *= contract_size
        self._realized_pnl += pnl
        self._balance += pnl
        remainder = quantity - closed

        if existing.quantity > closed:
            existing.quantity -= closed
        elif remainder > ZERO:
            existing.side = incoming
            existing.quantity = remainder
            existing.average_entry_price = price
            existing.opened_at = now
        else:
            del self._positions[key]

    def _unrealized(self, position: _PaperPosition) -> Decimal:
        quote = self._quotes.get(position.venue_symbol)
        if quote is None:
            return ZERO
        mark = quote.bid if position.side is PositionSide.LONG else quote.ask
        direction = Decimal(1) if position.side is PositionSide.LONG else Decimal(-1)
        spec = self._instruments.get(position.venue_symbol)
        value = (mark - position.average_entry_price) * position.quantity * direction
        return value * spec.contract_size if spec and spec.contract_size else value


PAPER_CAPABILITIES = Capabilities(
    venue_code=PAPER_VENUE_CODE,
    display_name="Atlas Paper Trading",
    asset_classes=frozenset(AssetClass),
    order_types=frozenset(OrderType),
    time_in_force=frozenset(TimeInForce),
    environments=frozenset({VenueEnvironment.PAPER}),
    supports_amend=True,
    supports_cancel=True,
    supports_close_position=True,
    supports_streaming_quotes=True,
    supports_streaming_account=False,
    supports_historical_bars=False,
    supports_fractional_quantity=True,
    supports_client_order_id=True,
    supports_stop_loss_take_profit=True,
    supports_short_selling=True,
    max_symbols_per_quote_call=100,
    notes="Deterministic local simulator. Never reaches a real venue.",
)


class PaperAdapter:
    """:class:`~atlas_venues.protocol.VenueAdapter` over a :class:`PaperEngine`.

    Requires no credentials, so :meth:`verify_permissions` always succeeds — the one place
    paper mode legitimately differs, because there is nothing to authenticate against.
    """

    def __init__(self, context: AdapterContext, engine: PaperEngine, clock: Clock | None = None):
        if context.environment is not VenueEnvironment.PAPER:
            raise UnsupportedCapabilityError(
                "PaperAdapter only serves the paper environment", venue_code=PAPER_VENUE_CODE
            )
        self._context = context
        self._engine = engine
        self._clock = clock or SystemClock()

    # -- Discovery ---------------------------------------------------------------------

    def capabilities(self) -> Capabilities:
        return PAPER_CAPABILITIES

    async def verify_permissions(self) -> tuple[bool, str]:
        return True, "paper trading requires no venue credentials"

    async def instruments(self) -> Sequence[InstrumentSpec]:
        return self._engine.instruments()

    async def instrument(self, symbol: str) -> InstrumentSpec:
        for spec in self._engine.instruments():
            if symbol in (spec.venue_symbol, spec.canonical_symbol):
                return spec
        raise TerminalRejectionError(
            f"unknown instrument {symbol}",
            venue_code=PAPER_VENUE_CODE,
            venue_error_code="PAPER_UNKNOWN_INSTRUMENT",
        )

    # -- Market data -------------------------------------------------------------------

    async def quote(self, symbols: Sequence[str]) -> Sequence[QuoteTick]:
        return tuple(q for s in symbols if (q := self._engine.quote(s)) is not None)

    async def bars(
        self,
        symbol: str,
        interval: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> Sequence[Bar]:
        raise UnsupportedCapabilityError(
            "the paper simulator does not serve historical bars; use a real venue's history",
            venue_code=PAPER_VENUE_CODE,
        )

    async def stream_quotes(self, symbols: Sequence[str]) -> AsyncIterator[QuoteTick]:
        """Re-emit whatever quotes have been fed into the engine, once per poll interval."""
        wanted = set(symbols)
        seen: dict[str, datetime] = {}
        while True:
            for symbol in wanted:
                tick = self._engine.quote(symbol)
                if tick is not None and seen.get(symbol) != tick.venue_time:
                    seen[symbol] = tick.venue_time
                    yield tick
            await asyncio.sleep(0.1)

    # -- Account -----------------------------------------------------------------------

    async def account_snapshot(self) -> AccountSnapshot:
        return AccountSnapshot(
            venue_code=PAPER_VENUE_CODE,
            venue_account_ref=self._engine.account_ref,
            environment=VenueEnvironment.PAPER,
            currency=self._engine.currency,
            balance=self._engine.balance,
            equity=self._engine.equity(),
            venue_time=self._clock.now(),
            realized_pnl=self._engine.realized_pnl,
            unrealized_pnl=self._engine.equity() - self._engine.balance,
            view_state=AccountViewState.LIVE,
        )

    async def positions(self) -> Sequence[VenuePosition]:
        now = self._clock.now()
        out = []
        for p in self._engine.positions():
            quote = self._engine.quote(p.venue_symbol)
            out.append(
                VenuePosition(
                    venue_code=PAPER_VENUE_CODE,
                    venue_account_ref=self._engine.account_ref,
                    venue_symbol=p.venue_symbol,
                    side=p.side,
                    quantity=p.quantity,
                    average_entry_price=p.average_entry_price,
                    environment=VenueEnvironment.PAPER,
                    venue_time=now,
                    venue_position_ref=p.venue_position_ref,
                    current_price=quote.mid if quote else None,
                    opened_at=p.opened_at,
                )
            )
        return tuple(out)

    async def open_orders(self) -> Sequence[VenueOrder]:
        return tuple(self._to_venue_order(o) for o in self._engine.open_orders())

    async def stream_account(self) -> AsyncIterator[AccountSnapshot]:
        """Not offered. An async generator so ``async for`` raises the capability error."""
        raise UnsupportedCapabilityError(
            "the paper simulator has no account push channel; poll account_snapshot",
            venue_code=PAPER_VENUE_CODE,
        )
        yield  # pragma: no cover - unreachable, makes this an async generator

    # -- Execution ---------------------------------------------------------------------

    async def submit(self, request: SubmitRequest) -> SubmitResult:
        if request.environment is not VenueEnvironment.PAPER:
            raise UnsupportedCapabilityError(
                f"PaperAdapter refused a {request.environment} order",
                venue_code=PAPER_VENUE_CODE,
            )
        if self._engine.fill_model.latency_seconds:
            await asyncio.sleep(self._engine.fill_model.latency_seconds)
        order = self._engine.submit(request)
        return self._to_result(order)

    async def amend(self, request: AmendRequest) -> SubmitResult:
        order = self._engine.order(
            venue_order_ref=request.venue_order_ref, client_order_id=request.client_order_id
        )
        return self._to_result(self._engine.amend(order, request))

    async def cancel(
        self, venue_order_ref: str, *, client_order_id: str | None = None
    ) -> SubmitResult:
        order = self._engine.order(venue_order_ref=venue_order_ref, client_order_id=client_order_id)
        return self._to_result(self._engine.cancel(order))

    async def close_position(
        self, venue_position_ref: str, *, quantity: object | None = None
    ) -> SubmitResult:
        qty = quantity if quantity is None or isinstance(quantity, Decimal) else None
        if quantity is not None and qty is None:
            raise TerminalRejectionError(
                "close_position quantity must be Decimal", venue_code=PAPER_VENUE_CODE
            )
        return self._to_result(self._engine.close_position(venue_position_ref, qty))

    async def order_status(
        self, *, venue_order_ref: str | None = None, client_order_id: str | None = None
    ) -> VenueOrder:
        return self._to_venue_order(
            self._engine.order(venue_order_ref=venue_order_ref, client_order_id=client_order_id)
        )

    # -- Semantics ---------------------------------------------------------------------

    async def server_time_offset(self) -> VenueTimeOffset:
        now = self._clock.now()
        return VenueTimeOffset(
            venue_code=PAPER_VENUE_CODE,
            offset_seconds=0.0,
            round_trip_seconds=0.0,
            measured_at=now,
        )

    def rate_limit_model(self) -> RateLimitModel:
        return DEFAULT_RATE_LIMIT_MODELS[PAPER_VENUE_CODE]

    def classify_error(self, exc: BaseException) -> ErrorClass:
        if isinstance(exc, VenueError):
            return exc.error_class
        # The simulator is in-process: nothing here can be genuinely ambiguous, so an
        # unexpected exception is a bug in Atlas, not an unknown venue outcome.
        return ErrorClass.TERMINAL_REJECTION

    # -- Mapping -----------------------------------------------------------------------

    def _to_venue_order(self, order: _PaperOrder) -> VenueOrder:
        req = order.request
        return VenueOrder(
            venue_code=PAPER_VENUE_CODE,
            venue_order_ref=order.venue_order_ref,
            venue_symbol=req.venue_symbol,
            side=req.side,
            order_type=req.order_type,
            state=order.state,
            quantity=req.quantity,
            filled_quantity=order.filled_quantity,
            environment=VenueEnvironment.PAPER,
            venue_time=order.updated_at,
            client_order_id=req.client_order_id,
            limit_price=req.limit_price,
            stop_price=req.stop_price,
            average_fill_price=order.average_fill_price,
            time_in_force=req.time_in_force,
            venue_account_ref=req.venue_account_ref,
            reject_reason=order.reject_reason,
            fills=tuple(order.fills),
        )

    def _to_result(self, order: _PaperOrder) -> SubmitResult:
        return SubmitResult(
            accepted=order.state is not OrderState.REJECTED,
            venue_order_ref=order.venue_order_ref,
            client_order_id=order.request.client_order_id,
            state=order.state,
            venue_time=order.updated_at,
            filled_quantity=order.filled_quantity,
            average_fill_price=order.average_fill_price,
            reject_reason=order.reject_reason,
            fills=tuple(order.fills),
        )


__all__ = [
    "PAPER_CAPABILITIES",
    "PAPER_VENUE_CODE",
    "PaperAdapter",
    "PaperEngine",
    "PaperFillModel",
]
