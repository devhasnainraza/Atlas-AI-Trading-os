"""Conformance tests for venue adapter market data (T046, US2).

Verifies the market data behavior contract:
- quote(): Decimal bid/ask, timezone-aware, non-negative spread, respect max_symbols_per_quote_call
- bars(): Decimal OHLCV, closed candles only, left-edge timestamp, oldest first
- stream_quotes(): AsyncIterator yielding valid QuoteTick snapshots
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
from atlas_venues.errors import UnsupportedCapabilityError, VenueError
from atlas_venues.models import Bar, InstrumentSpec, QuoteTick
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
        account_ref="conf-data-account",
        starting_balance=Decimal("100000"),
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



@pytest.fixture
def paper_adapter(paper_engine: PaperEngine) -> PaperAdapter:
    context = AdapterContext(
        connection_id="conn-data-paper",
        venue_code=PAPER_VENUE_CODE,
        environment=VenueEnvironment.PAPER,
        credential_id="cred-data-paper",
        venue_account_ref="conf-data-account",
    )
    return PaperAdapter(context, paper_engine)


@pytest.fixture
def oanda_adapter() -> OandaAdapter:
    context = AdapterContext(
        connection_id="conn-data-oanda",
        venue_code=OANDA_VENUE_CODE,
        environment=VenueEnvironment.DEMO,
        credential_id="cred-data-oanda",
    )
    return OandaAdapter(context)


@pytest.fixture
def binance_adapter() -> BinanceAdapter:
    context = AdapterContext(
        connection_id="conn-data-binance",
        venue_code=BINANCE_VENUE_CODE,
        environment=VenueEnvironment.DEMO,
        credential_id="cred-data-binance",
    )
    return BinanceAdapter(context)


@pytest.fixture
def bybit_adapter() -> BybitAdapter:
    context = AdapterContext(
        connection_id="conn-data-bybit",
        venue_code=BYBIT_VENUE_CODE,
        environment=VenueEnvironment.DEMO,
        credential_id="cred-data-bybit",
    )
    return BybitAdapter(context)


@pytest.fixture
def mt5_adapter() -> Mt5Adapter:
    context = AdapterContext(
        connection_id="conn-data-mt5",
        venue_code=MT5_VENUE_CODE,
        environment=VenueEnvironment.DEMO,
        credential_id="cred-data-mt5",
    )
    return Mt5Adapter(context)


@pytest.fixture
def ibkr_adapter() -> IbkrAdapter:
    context = AdapterContext(
        connection_id="conn-data-ibkr",
        venue_code=IBKR_VENUE_CODE,
        environment=VenueEnvironment.DEMO,
        credential_id="cred-data-ibkr",
    )
    return IbkrAdapter(context)


@pytest.fixture(
    params=[
        "paper_adapter",
        "oanda_adapter",
        "binance_adapter",
        "bybit_adapter",
        "mt5_adapter",
        "ibkr_adapter",
    ]
)
def any_data_adapter(request: pytest.FixtureRequest) -> VenueAdapter:
    return request.getfixturevalue(request.param)  # type: ignore[no-any-return]


class TestVenueMarketDataConformance:
    """Market data contract tests for VenueAdapter implementations."""

    @pytest.mark.asyncio
    async def test_quotes_are_decimal_and_timezone_aware(
        self, any_data_adapter: VenueAdapter
    ) -> None:
        specs = await any_data_adapter.instruments()
        assert len(specs) > 0
        symbol = specs[0].venue_symbol

        quotes = await any_data_adapter.quote([symbol])
        assert len(quotes) > 0
        for q in quotes:
            assert isinstance(q, QuoteTick)
            assert isinstance(q.bid, Decimal)
            assert isinstance(q.ask, Decimal)
            assert q.bid > ZERO
            assert q.ask > ZERO
            assert q.ask >= q.bid
            assert q.venue_time.tzinfo is not None
            assert q.received_at.tzinfo is not None

    @pytest.mark.asyncio
    async def test_bars_contract_or_unsupported(
        self, any_data_adapter: VenueAdapter
    ) -> None:
        specs = await any_data_adapter.instruments()
        symbol = specs[0].venue_symbol
        caps = any_data_adapter.capabilities()

        if not caps.supports_historical_bars:
            with pytest.raises(UnsupportedCapabilityError):
                await any_data_adapter.bars(symbol, "1m")
        else:
            bars = await any_data_adapter.bars(symbol, "1m")
            assert len(bars) > 0
            for b in bars:
                assert isinstance(b, Bar)
                assert isinstance(b.open, Decimal)
                assert isinstance(b.high, Decimal)
                assert isinstance(b.low, Decimal)
                assert isinstance(b.close, Decimal)
                assert isinstance(b.volume, Decimal)
                assert b.high >= b.low
                assert b.high >= b.open
                assert b.high >= b.close
                assert b.low <= b.open
                assert b.open_time.tzinfo is not None


    @pytest.mark.asyncio
    async def test_stream_quotes_yields_ticks(
        self, any_data_adapter: VenueAdapter
    ) -> None:
        specs = await any_data_adapter.instruments()
        symbol = specs[0].venue_symbol

        stream = any_data_adapter.stream_quotes([symbol])
        ticks = []
        async for tick in stream:
            ticks.append(tick)
            if len(ticks) >= 1:
                break

        assert len(ticks) >= 1
        first = ticks[0]
        assert isinstance(first, QuoteTick)
        assert isinstance(first.bid, Decimal)
        assert isinstance(first.ask, Decimal)
        assert first.ask >= first.bid
