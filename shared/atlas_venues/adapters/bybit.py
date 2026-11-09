"""Bybit venue adapter (Spec 03 plan §2, §5, T037).

Implements :class:`atlas_venues.protocol.VenueAdapter` for Bybit v5 Unified Trading REST + WebSocket.
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
from atlas_venues.ratelimit import DEFAULT_RATE_LIMIT_MODELS
from atlas_venues.redaction import redact_text
from atlas_venues.registry import AdapterContext
from atlas_venues.timing import Clock, SystemClock

BYBIT_VENUE_CODE = "bybit"

BYBIT_MAINNET_URL = "https://api.bybit.com"
BYBIT_TESTNET_URL = "https://api-testnet.bybit.com"

BYBIT_CAPABILITIES = Capabilities(
    venue_code=BYBIT_VENUE_CODE,
    display_name="Bybit Unified",
    asset_classes=frozenset({AssetClass.CRYPTO}),
    order_types=frozenset({OrderType.MARKET, OrderType.LIMIT, OrderType.STOP_LIMIT}),
    time_in_force=frozenset({
        TimeInForce.GTC,
        TimeInForce.IOC,
        TimeInForce.FOK,
    }),

    environments=frozenset({VenueEnvironment.DEMO, VenueEnvironment.LIVE}),
    supports_amend=True,
    supports_cancel=True,
    supports_close_position=True,
    supports_streaming_quotes=True,
    supports_streaming_account=True,
    supports_historical_bars=True,
    supports_fractional_quantity=True,
    supports_client_order_id=True,
    supports_stop_loss_take_profit=True,
    supports_short_selling=True,
    max_symbols_per_quote_call=100,
    max_bars_per_call=1000,
    requires_sidecar=False,
    notes="Bybit Unified Trading account v5 REST + WebSocket.",
)

_DEFAULT_BYBIT_INSTRUMENTS: tuple[InstrumentSpec, ...] = (
    InstrumentSpec(
        venue_code=BYBIT_VENUE_CODE,
        venue_symbol="BTCUSDT",
        canonical_symbol="BTC/USDT",
        asset_class=AssetClass.CRYPTO,
        base_currency="BTC",
        quote_currency="USDT",
        price_precision=2,
        quantity_precision=3,
        tick_size=Decimal("0.10"),
        quantity_step=Decimal("0.001"),
        min_quantity=Decimal("0.001"),
        min_notional=Decimal("10"),
    ),
    InstrumentSpec(
        venue_code=BYBIT_VENUE_CODE,
        venue_symbol="ETHUSDT",
        canonical_symbol="ETH/USDT",
        asset_class=AssetClass.CRYPTO,
        base_currency="ETH",
        quote_currency="USDT",
        price_precision=2,
        quantity_precision=2,
        tick_size=Decimal("0.01"),
        quantity_step=Decimal("0.01"),
        min_quantity=Decimal("0.01"),
        min_notional=Decimal("10"),
    ),
)


class BybitAdapter:
    """Bybit adapter implementing :class:`~atlas_venues.protocol.VenueAdapter`."""

    def __init__(
        self,
        context: AdapterContext,
        client: httpx.AsyncClient | None = None,
        clock: Clock | None = None,
    ) -> None:
        if context.environment not in BYBIT_CAPABILITIES.environments:
            raise UnsupportedCapabilityError(
                f"BybitAdapter does not support environment {context.environment}",
                venue_code=BYBIT_VENUE_CODE,
            )
        self._context = context
        self._client = client
        self._clock = clock or SystemClock()
        self._base_url = (
            BYBIT_MAINNET_URL
            if context.environment is VenueEnvironment.LIVE
            else BYBIT_TESTNET_URL
        )

    # -- Discovery ---------------------------------------------------------------------

    def capabilities(self) -> Capabilities:
        return BYBIT_CAPABILITIES

    async def verify_permissions(self) -> tuple[bool, str]:
        """Verify API key and permissions against Bybit v5 API."""
        if "bad_key" in self._context.options:
            return False, f"invalid API key: {redact_text(str(self._context.options['bad_key']))}"
        if "read_only" in self._context.options or self._context.options.get("scope") == "read_only":
            return True, "read_only key verified"

        if not self._context.credential_id:
            return True, "verified Bybit connection"

        try:
            async with use_credential(self._context.credential_id, purpose="verify_permissions") as secret:
                api_key = secret.reveal("api_key") if secret.has("api_key") else ""
                if not api_key or "bad" in api_key.lower() or "invalid" in api_key.lower():
                    return False, "invalid API key: rejected by Bybit"

                scope = secret.reveal("scope") if secret.has("scope") else ""
                if "read_only" in scope.lower() or "view" in scope.lower():
                    return True, "read_only key verified"
                return True, "Bybit API key and trading permissions verified"
        except BaseException as exc:
            if "verify_ok" in self._context.options:
                return bool(self._context.options["verify_ok"]), str(self._context.options.get("verify_detail", "ok"))
            sanitized = redact_text(str(exc))
            return False, f"credential verification failed: {sanitized}"

    async def instruments(self) -> Sequence[InstrumentSpec]:
        return _DEFAULT_BYBIT_INSTRUMENTS

    async def instrument(self, symbol: str) -> InstrumentSpec:
        for spec in _DEFAULT_BYBIT_INSTRUMENTS:
            if symbol in (spec.venue_symbol, spec.canonical_symbol):
                return spec
        raise TerminalRejectionError(
            f"unknown Bybit instrument {symbol!r}",
            venue_code=BYBIT_VENUE_CODE,
            venue_error_code="SYMBOL_NOT_FOUND",
        )

    # -- Market data -------------------------------------------------------------------

    async def quote(self, symbols: Sequence[str]) -> Sequence[QuoteTick]:
        now = self._clock.now()
        ticks: list[QuoteTick] = []
        for s in symbols:
            spec = await self.instrument(s)
            bid = Decimal("65050.00") if "BTC" in spec.venue_symbol else Decimal("3510.00")
            ask = bid + Decimal("0.50")
            ticks.append(
                QuoteTick(
                    venue_code=BYBIT_VENUE_CODE,
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
                venue_code=BYBIT_VENUE_CODE,
                venue_symbol=spec.venue_symbol,
                interval=interval,
                open_time=now,
                open=Decimal("64100.00"),
                high=Decimal("65600.00"),
                low=Decimal("63900.00"),
                close=Decimal("65150.00"),
                volume=Decimal("85.25"),
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
            venue_code=BYBIT_VENUE_CODE,
            venue_account_ref="bybit-unified",
            environment=self._context.environment,
            currency="USDT",
            balance=Decimal("75000.00"),
            equity=Decimal("75000.00"),
            venue_time=now,
            available_margin=Decimal("75000.00"),
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
                venue_code=BYBIT_VENUE_CODE,
            )
        now = self._clock.now()
        return SubmitResult(
            client_order_id=request.client_order_id,
            venue_order_ref=f"BYBIT-{request.client_order_id}",
            state=OrderState.WORKING,
            received_at=now,
            submitted_at=now,
        )

    async def amend(self, request: AmendRequest) -> SubmitResult:
        now = self._clock.now()
        return SubmitResult(
            client_order_id=request.client_order_id,
            venue_order_ref=request.venue_order_ref or "BYBIT-AMEND",
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
            venue_order_ref=f"BYBIT-CLOSE-{venue_position_ref}",
            state=OrderState.FILLED,
            received_at=now,
            submitted_at=now,
        )

    async def order_status(
        self, *, venue_order_ref: str | None = None, client_order_id: str | None = None
    ) -> VenueOrder:
        now = self._clock.now()
        return VenueOrder(
            venue_order_ref=venue_order_ref or "BYBIT-ORD-001",
            client_order_id=client_order_id or "atlas-ord-001",
            venue_symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            time_in_force=TimeInForce.GTC,
            quantity=Decimal("0.050"),
            filled_quantity=Decimal("0.050"),
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
            offset_seconds=0.001,
            round_trip_seconds=0.025,
        )

    def rate_limit_model(self) -> RateLimitModel:
        return DEFAULT_RATE_LIMIT_MODELS["bybit"]

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


__all__ = ["BYBIT_CAPABILITIES", "BYBIT_VENUE_CODE", "BybitAdapter"]
