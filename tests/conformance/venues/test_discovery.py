"""Conformance tests for venue adapter discovery (T029, US1).

Verifies the discovery behavior contract:
- capabilities(): pure, synchronous, non-empty invariants
- verify_permissions(): asynchronous, (bool, str) contract with descriptive reasoning
- instruments(): universe enumeration, Decimal precision invariants
- instrument(symbol): single lookup by canonical or venue symbol
"""

from __future__ import annotations

import inspect
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
from atlas_venues.errors import VenueError
from atlas_venues.models import Capabilities, InstrumentSpec
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
        account_ref="conf-discovery-account",
        starting_balance=Decimal("100000"),
        fill_model=PaperFillModel(),
        clock=SystemClock(),
    )
    engine.set_instrument(btc_spec)
    return engine


@pytest.fixture
def paper_adapter(paper_engine: PaperEngine) -> PaperAdapter:
    context = AdapterContext(
        connection_id="conn-discovery-paper",
        venue_code=PAPER_VENUE_CODE,
        environment=VenueEnvironment.PAPER,
        credential_id="cred-discovery-paper",
        venue_account_ref="conf-discovery-account",
    )
    return PaperAdapter(context, paper_engine)


@pytest.fixture
def oanda_adapter() -> OandaAdapter:
    context = AdapterContext(
        connection_id="conn-discovery-oanda",
        venue_code=OANDA_VENUE_CODE,
        environment=VenueEnvironment.DEMO,
        credential_id="cred-discovery-oanda",
    )
    return OandaAdapter(context)


@pytest.fixture
def binance_adapter() -> BinanceAdapter:
    context = AdapterContext(
        connection_id="conn-discovery-binance",
        venue_code=BINANCE_VENUE_CODE,
        environment=VenueEnvironment.DEMO,
        credential_id="cred-discovery-binance",
    )
    return BinanceAdapter(context)


@pytest.fixture
def bybit_adapter() -> BybitAdapter:
    context = AdapterContext(
        connection_id="conn-discovery-bybit",
        venue_code=BYBIT_VENUE_CODE,
        environment=VenueEnvironment.DEMO,
        credential_id="cred-discovery-bybit",
    )
    return BybitAdapter(context)


@pytest.fixture
def mt5_adapter() -> Mt5Adapter:
    context = AdapterContext(
        connection_id="conn-discovery-mt5",
        venue_code=MT5_VENUE_CODE,
        environment=VenueEnvironment.DEMO,
        credential_id="cred-discovery-mt5",
    )
    return Mt5Adapter(context)


@pytest.fixture
def ibkr_adapter() -> IbkrAdapter:
    context = AdapterContext(
        connection_id="conn-discovery-ibkr",
        venue_code=IBKR_VENUE_CODE,
        environment=VenueEnvironment.DEMO,
        credential_id="cred-discovery-ibkr",
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
def any_adapter(request: pytest.FixtureRequest) -> VenueAdapter:
    return request.getfixturevalue(request.param)  # type: ignore[no-any-return]


class TestVenueDiscoveryConformance:
    """Discovery behavioral contract tests for VenueAdapter implementations."""

    def test_satisfies_protocol(self, any_adapter: VenueAdapter) -> None:
        assert isinstance(any_adapter, VenueAdapter)

    def test_capabilities_is_pure_and_sync(self, any_adapter: VenueAdapter) -> None:
        assert not inspect.iscoroutinefunction(any_adapter.capabilities)
        first = any_adapter.capabilities()
        second = any_adapter.capabilities()
        assert first == second
        assert isinstance(first, Capabilities)

    def test_capabilities_invariants(self, any_adapter: VenueAdapter) -> None:
        caps = any_adapter.capabilities()
        assert caps.venue_code
        assert caps.display_name
        assert len(caps.asset_classes) > 0
        assert len(caps.order_types) > 0
        assert len(caps.time_in_force) > 0
        assert len(caps.environments) > 0

    @pytest.mark.asyncio
    async def test_verify_permissions_returns_verdict_and_detail(
        self, any_adapter: VenueAdapter
    ) -> None:
        ok, detail = await any_adapter.verify_permissions()
        assert isinstance(ok, bool)
        assert isinstance(detail, str)
        assert len(detail.strip()) > 0

    @pytest.mark.asyncio
    async def test_instruments_enumeration_invariants(
        self, any_adapter: VenueAdapter
    ) -> None:
        specs = await any_adapter.instruments()
        assert len(specs) > 0
        for spec in specs:
            assert isinstance(spec, InstrumentSpec)
            assert spec.venue_code == any_adapter.capabilities().venue_code
            assert spec.venue_symbol
            assert spec.canonical_symbol
            assert isinstance(spec.tick_size, Decimal)
            assert spec.tick_size > ZERO
            assert isinstance(spec.quantity_step, Decimal)
            assert spec.quantity_step > ZERO
            assert isinstance(spec.min_quantity, Decimal)
            assert spec.min_quantity > ZERO

    @pytest.mark.asyncio
    async def test_instrument_lookup_by_symbol(
        self, any_adapter: VenueAdapter
    ) -> None:
        specs = await any_adapter.instruments()
        first_spec = specs[0]

        by_venue_sym = await any_adapter.instrument(first_spec.venue_symbol)
        assert by_venue_sym.venue_symbol == first_spec.venue_symbol

        by_canon_sym = await any_adapter.instrument(first_spec.canonical_symbol)
        assert by_canon_sym.canonical_symbol == first_spec.canonical_symbol

    @pytest.mark.asyncio
    async def test_instrument_unknown_symbol_raises(
        self, any_adapter: VenueAdapter
    ) -> None:
        with pytest.raises(VenueError):
            await any_adapter.instrument("__NON_EXISTENT_SYMBOL_XYZ__")

