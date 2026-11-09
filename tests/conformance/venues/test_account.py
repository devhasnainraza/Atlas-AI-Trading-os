"""Conformance tests for venue adapter account operations (T059, US3).

Verifies the account behavior contract across all venue adapters:
- account_snapshot(): Returns AccountSnapshot with strict Decimal balance/equity, tz-aware venue_time
- positions(): Sequence of VenuePosition with positive Decimal quantity and price
- open_orders(): Sequence of VenueOrder with Decimal quantities
- stream_account(): AsyncIterator yielding valid account updates or raises UnsupportedCapabilityError
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from atlas_venues.adapters import (
    BINANCE_VENUE_CODE,
    BYBIT_VENUE_CODE,
    IBKR_VENUE_CODE,
    MT5_VENUE_CODE,
    OANDA_VENUE_CODE,
    PAPER_VENUE_CODE,
    BinanceAdapter,
    BybitAdapter,
    IbkrAdapter,
    Mt5Adapter,
    OandaAdapter,
    PaperAdapter,
    PaperEngine,
    PaperFillModel,
)
from atlas_venues.enums import AssetClass, VenueEnvironment
from atlas_venues.errors import UnsupportedCapabilityError
from atlas_venues.models import (
    AccountSnapshot,
    InstrumentSpec,
    QuoteTick,
    VenueOrder,
    VenuePosition,
)
from atlas_venues.precision import ZERO
from atlas_venues.protocol import VenueAdapter
from atlas_venues.registry import AdapterContext
from atlas_venues.timing import SystemClock


@pytest.fixture
def btc_spec() -> InstrumentSpec:
    return InstrumentSpec(
        venue_code=PAPER_VENUE_CODE,
        venue_symbol="BTCUSDT",
        canonical_symbol="BTC/USDT",
        asset_class=AssetClass.CRYPTO,
        base_currency="BTC",
        quote_currency="USDT",
        price_precision=2,
        quantity_precision=6,
        tick_size=Decimal("0.01"),
        quantity_step=Decimal("0.000001"),
        min_quantity=Decimal("0.000001"),
        min_notional=Decimal("10"),
    )


@pytest.fixture
def paper_engine(btc_spec: InstrumentSpec) -> PaperEngine:
    engine = PaperEngine(
        account_ref="conf-account-test",
        starting_balance=Decimal("100000.00"),
        fill_model=PaperFillModel(),
        clock=SystemClock(),
    )
    engine.set_instrument(btc_spec)
    now = SystemClock().now()
    engine.set_quote(
        QuoteTick(
            venue_code=PAPER_VENUE_CODE,
            venue_symbol="BTCUSDT",
            bid=Decimal("65000.00"),
            ask=Decimal("65001.00"),
            venue_time=now,
            received_at=now,
        )
    )
    return engine


@pytest.fixture(
    params=[
        (PAPER_VENUE_CODE, VenueEnvironment.PAPER),
        (OANDA_VENUE_CODE, VenueEnvironment.DEMO),
        (BINANCE_VENUE_CODE, VenueEnvironment.DEMO),
        (BYBIT_VENUE_CODE, VenueEnvironment.DEMO),
        (MT5_VENUE_CODE, VenueEnvironment.DEMO),
        (IBKR_VENUE_CODE, VenueEnvironment.DEMO),
    ]
)
def adapter_instance(
    request: pytest.FixtureRequest, paper_engine: PaperEngine
) -> tuple[VenueAdapter, str, VenueEnvironment]:
    venue_code, env = request.param
    ctx = AdapterContext(
        connection_id=f"conn-{venue_code}-test",
        venue_code=venue_code,
        environment=env,
        credential_id=f"cred-{venue_code}-01",
        venue_account_ref="conf-account-test",
    )

    if venue_code == PAPER_VENUE_CODE:
        adapter = PaperAdapter(ctx, paper_engine)
    elif venue_code == OANDA_VENUE_CODE:
        adapter = OandaAdapter(ctx)
    elif venue_code == BINANCE_VENUE_CODE:
        adapter = BinanceAdapter(ctx)
    elif venue_code == BYBIT_VENUE_CODE:
        adapter = BybitAdapter(ctx)
    elif venue_code == MT5_VENUE_CODE:
        adapter = Mt5Adapter(ctx)
    elif venue_code == IBKR_VENUE_CODE:
        adapter = IbkrAdapter(ctx)
    else:
        raise ValueError(f"Unknown venue {venue_code}")

    return adapter, venue_code, env


class TestVenueAccountConformance:
    """T059 Conformance Group: Account operations."""

    @pytest.mark.asyncio
    async def test_account_snapshot_returns_valid_decimal_balances(
        self, adapter_instance: tuple[VenueAdapter, str, VenueEnvironment]
    ) -> None:
        adapter, venue_code, env = adapter_instance
        snapshot = await adapter.account_snapshot()

        assert isinstance(snapshot, AccountSnapshot)
        assert snapshot.venue_code == venue_code
        assert snapshot.environment == env
        assert isinstance(snapshot.balance, Decimal)
        assert isinstance(snapshot.equity, Decimal)
        assert snapshot.balance > ZERO
        assert snapshot.equity > ZERO
        assert snapshot.venue_time.tzinfo is not None

    @pytest.mark.asyncio
    async def test_positions_returns_valid_structure(
        self, adapter_instance: tuple[VenueAdapter, str, VenueEnvironment]
    ) -> None:
        adapter, venue_code, env = adapter_instance
        positions = await adapter.positions()

        assert isinstance(positions, (list, tuple))
        for p in positions:
            assert isinstance(p, VenuePosition)
            assert p.venue_code == venue_code
            assert p.environment == env
            assert isinstance(p.quantity, Decimal)
            assert p.quantity > ZERO
            assert isinstance(p.average_entry_price, Decimal)
            assert p.average_entry_price > ZERO
            assert p.venue_time.tzinfo is not None

    @pytest.mark.asyncio
    async def test_open_orders_returns_valid_structure(
        self, adapter_instance: tuple[VenueAdapter, str, VenueEnvironment]
    ) -> None:
        adapter, venue_code, env = adapter_instance
        orders = await adapter.open_orders()

        assert isinstance(orders, (list, tuple))
        for o in orders:
            assert isinstance(o, VenueOrder)
            assert o.venue_code == venue_code
            assert o.environment == env
            assert isinstance(o.quantity, Decimal)
            assert isinstance(o.filled_quantity, Decimal)
            assert o.venue_time.tzinfo is not None

    @pytest.mark.asyncio
    async def test_stream_account_yields_or_raises_unsupported(
        self, adapter_instance: tuple[VenueAdapter, str, VenueEnvironment]
    ) -> None:
        adapter, venue_code, _ = adapter_instance
        try:
            stream = adapter.stream_account()
            async for item in stream:
                assert isinstance(item, (AccountSnapshot, VenuePosition, VenueOrder))
                break
        except UnsupportedCapabilityError as exc:
            assert exc.venue_code == venue_code
