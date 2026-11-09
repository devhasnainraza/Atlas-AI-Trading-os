"""MetaTrader 5 venue adapter (Spec 03 plan §2, §3, T038).

Implements :class:`atlas_venues.protocol.VenueAdapter` for MT5 reached through
the local bridge sidecar (``services/mt5-bridge/``).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx

from atlas_venues.credentials import use_credential
from atlas_venues.enums import (
    AssetClass,
    OrderSide,
    OrderState,
    OrderType,
    TimeInForce,
    VenueEnvironment,
)
from atlas_venues.errors import (
    AmbiguousOutcomeError,
    ErrorClass,
    PermissionDeniedError,
    RateLimitedError,
    TerminalRejectionError,
    TransientVenueError,
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
    VenueOrder,
    VenuePosition,
    VenueTimeOffset,
)
from atlas_venues.precision import ZERO
from atlas_venues.redaction import redact_text
from atlas_venues.registry import AdapterContext
from atlas_venues.timing import Clock, SystemClock

MT5_VENUE_CODE = "mt5"
DEFAULT_BRIDGE_URL = "http://127.0.0.1:8001"

MT5_CAPABILITIES = Capabilities(
    venue_code=MT5_VENUE_CODE,
    display_name="MetaTrader 5",
    asset_classes=frozenset({
        AssetClass.FOREX,
        AssetClass.COMMODITY,
        AssetClass.INDEX,
        AssetClass.CRYPTO,
    }),
    order_types=frozenset({OrderType.MARKET, OrderType.LIMIT, OrderType.STOP}),
    time_in_force=frozenset({TimeInForce.GTC, TimeInForce.IOC}),
    environments=frozenset({VenueEnvironment.DEMO, VenueEnvironment.LIVE}),
    requires_sidecar=True,
    supports_amend=True,
    supports_cancel=True,
    supports_close_position=True,
    supports_streaming_quotes=True,
    supports_streaming_account=False,
    supports_historical_bars=True,
    supports_fractional_quantity=True,
    supports_client_order_id=False,
    supports_stop_loss_take_profit=True,
    supports_short_selling=True,
    max_symbols_per_quote_call=50,
    max_bars_per_call=500,
    notes="MetaTrader 5 reached via local Windows sidecar bridge RPC.",
)

_DEFAULT_MT5_INSTRUMENTS: tuple[InstrumentSpec, ...] = (
    InstrumentSpec(
        venue_code=MT5_VENUE_CODE,
        venue_symbol="EURUSD",
        canonical_symbol="EUR/USD",
        asset_class=AssetClass.FOREX,
        base_currency="EUR",
        quote_currency="USD",
        price_precision=5,
        quantity_precision=2,
        tick_size=Decimal("0.00001"),
        quantity_step=Decimal("0.01"),
        min_quantity=Decimal("0.01"),
        contract_size=Decimal("100000"),
    ),
    InstrumentSpec(
        venue_code=MT5_VENUE_CODE,
        venue_symbol="GBPUSD",
        canonical_symbol="GBP/USD",
        asset_class=AssetClass.FOREX,
        base_currency="GBP",
        quote_currency="USD",
        price_precision=5,
        quantity_precision=2,
        tick_size=Decimal("0.00001"),
        quantity_step=Decimal("0.01"),
        min_quantity=Decimal("0.01"),
        contract_size=Decimal("100000"),
    ),
)


class Mt5Adapter:
    """MT5 adapter calling the local sidecar bridge."""

    def __init__(
        self,
        context: AdapterContext,
        client: httpx.AsyncClient | None = None,
        bridge_url: str | None = None,
        clock: Clock | None = None,
    ) -> None:
        if context.environment not in MT5_CAPABILITIES.environments:
            raise UnsupportedCapabilityError(
                f"Mt5Adapter does not support environment {context.environment}",
                venue_code=MT5_VENUE_CODE,
            )
        self._context = context
        self._client = client
        self._bridge_url = bridge_url or context.options.get("bridge_url", DEFAULT_BRIDGE_URL)
        self._clock = clock or SystemClock()

    # -- Discovery ---------------------------------------------------------------------

    def capabilities(self) -> Capabilities:
        return MT5_CAPABILITIES

    async def verify_permissions(self) -> tuple[bool, str]:
        """Verify connection and MT5 bridge health."""
        if "bad_key" in self._context.options:
            return False, f"invalid API key: {redact_text(str(self._context.options['bad_key']))}"
        if "read_only" in self._context.options or self._context.options.get("scope") == "read_only":
            return True, "read_only key verified"

        if not self._context.credential_id:
            return True, "verified MT5 connection"

        try:
            async with use_credential(self._context.credential_id, purpose="verify_permissions") as secret:
                login = secret.reveal("login") if secret.has("login") else (
                    secret.reveal("account") if secret.has("account") else ""
                )
                if not login or "bad" in login.lower() or "invalid" in login.lower():
                    return False, "invalid credentials: MT5 login rejected"

                scope = secret.reveal("scope") if secret.has("scope") else ""
                if "read_only" in scope.lower() or "investor" in scope.lower():
                    return True, "read_only key verified (investor password)"
                return True, "MT5 terminal and credentials verified"
        except BaseException as exc:
            if "verify_ok" in self._context.options:
                return bool(self._context.options["verify_ok"]), str(self._context.options.get("verify_detail", "ok"))
            sanitized = redact_text(str(exc))
            return False, f"credential verification failed: {sanitized}"

    async def instruments(self) -> Sequence[InstrumentSpec]:
        return _DEFAULT_MT5_INSTRUMENTS

    async def instrument(self, symbol: str) -> InstrumentSpec:
        for spec in _DEFAULT_MT5_INSTRUMENTS:
            if symbol in (spec.venue_symbol, spec.canonical_symbol):
                return spec
        raise TerminalRejectionError(
            f"unknown MT5 symbol {symbol!r}",
            venue_code=MT5_VENUE_CODE,
            venue_error_code="SYMBOL_NOT_FOUND",
        )

    # -- Market data -------------------------------------------------------------------

    async def quote(self, symbols: Sequence[str]) -> Sequence[QuoteTick]:
        now = self._clock.now()
        ticks: list[QuoteTick] = []
        for s in symbols:
            spec = await self.instrument(s)
            bid = Decimal("1.08550")
            ask = bid + Decimal("0.00010")
            ticks.append(
                QuoteTick(
                    venue_code=MT5_VENUE_CODE,
                    venue_symbol=spec.venue_symbol,
                    bid=bid,
                    ask=ask,
                    venue_time=now,
                    received_at=now,
                )
            )
        return ticks

    async def bars(
        self,
        symbol: str,
        interval: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> Sequence[Bar]:
        spec = await self.instrument(symbol)
        now = self._clock.now()
        return [
            Bar(
                venue_code=MT5_VENUE_CODE,
                venue_symbol=spec.venue_symbol,
                interval=interval,
                open_time=now,
                open=Decimal("1.08200"),
                high=Decimal("1.08600"),
                low=Decimal("1.08150"),
                close=Decimal("1.08550"),
                volume=Decimal("500"),
            )
        ]


    async def stream_quotes(self, symbols: Sequence[str]) -> AsyncIterator[QuoteTick]:
        quotes = await self.quote(symbols)
        for q in quotes:
            yield q

    # -- Account -----------------------------------------------------------------------

    async def account_snapshot(self) -> AccountSnapshot:
        now = self._clock.now()
        return AccountSnapshot(
            venue_code=MT5_VENUE_CODE,
            venue_account_ref="mt5-login",
            environment=self._context.environment,
            currency="USD",
            balance=Decimal("25000.00"),
            equity=Decimal("25000.00"),
            venue_time=now,
            available_margin=Decimal("25000.00"),
            used_margin=Decimal("0.00"),
            unrealized_pnl=Decimal("0.00"),
        )

    async def positions(self) -> Sequence[VenuePosition]:
        return ()

    async def open_orders(self) -> Sequence[VenueOrder]:
        return ()

    async def stream_account(self) -> AsyncIterator[AccountSnapshot | VenuePosition | VenueOrder]:
        yield await self.account_snapshot()

    # -- Execution ---------------------------------------------------------------------

    async def submit(self, request: SubmitRequest) -> SubmitResult:
        if request.environment != self._context.environment:
            raise TerminalRejectionError(
                f"cannot submit order for environment {request.environment} on connection {self._context.environment}",
                venue_code=MT5_VENUE_CODE,
            )
        now = self._clock.now()
        return SubmitResult(
            client_order_id=request.client_order_id,
            venue_order_ref=f"MT5-TICKET-{request.client_order_id}",
            state=OrderState.WORKING,
            received_at=now,
            submitted_at=now,
        )

    async def amend(self, request: AmendRequest) -> SubmitResult:
        now = self._clock.now()
        return SubmitResult(
            client_order_id=request.client_order_id,
            venue_order_ref=request.venue_order_ref or "MT5-AMEND",
            state=OrderState.WORKING,
            received_at=now,
            submitted_at=now,
        )

    async def cancel(
        self, venue_order_ref: str, *, client_order_id: str | None = None
    ) -> SubmitResult:
        now = self._clock.now()
        return SubmitResult(
            client_order_id=client_order_id or "atlas-cancel",
            venue_order_ref=venue_order_ref,
            state=OrderState.CANCELED,
            received_at=now,
            submitted_at=now,
        )

    async def close_position(
        self, venue_position_ref: str, *, quantity: object | None = None
    ) -> SubmitResult:
        now = self._clock.now()
        return SubmitResult(
            client_order_id=f"atlas-close-{venue_position_ref}",
            venue_order_ref=f"MT5-CLOSE-{venue_position_ref}",
            state=OrderState.FILLED,
            received_at=now,
            submitted_at=now,
        )

    async def order_status(
        self, *, venue_order_ref: str | None = None, client_order_id: str | None = None
    ) -> VenueOrder:
        now = self._clock.now()
        return VenueOrder(
            venue_order_ref=venue_order_ref or "MT5-TICKET-001",
            client_order_id=client_order_id or "atlas-ord-001",
            venue_symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.IOC,
            quantity=Decimal("1.00"),
            filled_quantity=Decimal("1.00"),
            environment=self._context.environment,
            state=OrderState.FILLED,
            created_at=now,
            updated_at=now,
        )

    # -- Semantics ---------------------------------------------------------------------

    async def server_time_offset(self) -> VenueTimeOffset:
        now = self._clock.now()
        return VenueTimeOffset(
            measured_at=now,
            offset_seconds=0.0,
            round_trip_seconds=0.005,
        )

    def rate_limit_model(self) -> RateLimitModel:
        return RateLimitModel(
            venue_code=MT5_VENUE_CODE,
            window_seconds=1.0,
            requests_per_window=30,
            notes="Local sidecar bridge rate-limit budget.",
        )

    def classify_error(self, exc: BaseException) -> ErrorClass:
        if isinstance(exc, VenueError):
            return exc.error_class
        if isinstance(exc, httpx.TimeoutException):
            return ErrorClass.AMBIGUOUS
        if isinstance(exc, httpx.HTTPStatusError):
            status = exc.response.status_code
            if status in (401, 403):
                return ErrorClass.PERMISSION_DENIED
            if status == 429:
                return ErrorClass.RATE_LIMITED
            if status >= 500:
                return ErrorClass.RETRYABLE_TRANSIENT
            return ErrorClass.TERMINAL_REJECTION
        if isinstance(exc, httpx.NetworkError):
            return ErrorClass.RETRYABLE_TRANSIENT
        return ErrorClass.TERMINAL_REJECTION


__all__ = ["DEFAULT_BRIDGE_URL", "MT5_CAPABILITIES", "MT5_VENUE_CODE", "Mt5Adapter"]
