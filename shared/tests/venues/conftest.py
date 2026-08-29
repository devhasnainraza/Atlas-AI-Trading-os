"""Shared fixtures for venue tests."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from atlas_venues.adapters.paper import PaperAdapter, PaperEngine, PaperFillModel
from atlas_venues.enums import AssetClass, VenueEnvironment
from atlas_venues.models import InstrumentSpec, QuoteTick
from atlas_venues.registry import AdapterContext
from atlas_venues.timing import FrozenClock

T0 = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _isolate_credential_provider():
    """Restore the process-wide provider after each test.

    ``set_credential_provider`` is global by design (Spec 01 installs the real vault once at
    startup), so tests that swap it must not leak that swap into the next test.
    """
    from atlas_venues.credentials import get_credential_provider, set_credential_provider

    original = get_credential_provider()
    yield
    set_credential_provider(original)


@pytest.fixture
def clock() -> FrozenClock:
    return FrozenClock(T0)


@pytest.fixture
def btc_spec() -> InstrumentSpec:
    return InstrumentSpec(
        venue_code="paper",
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
def btc_quote() -> QuoteTick:
    return QuoteTick(
        venue_code="paper",
        venue_symbol="BTCUSDT",
        bid=Decimal("60000.00"),
        ask=Decimal("60010.00"),
        venue_time=T0,
        received_at=T0,
    )


@pytest.fixture
def engine(clock: FrozenClock, btc_spec: InstrumentSpec, btc_quote: QuoteTick) -> PaperEngine:
    engine = PaperEngine(
        account_ref="paper-acct-1",
        starting_balance=Decimal("100000"),
        fill_model=PaperFillModel(slippage_bps=Decimal("0")),
        clock=clock,
    )
    engine.set_instrument(btc_spec)
    engine.set_quote(btc_quote)
    return engine


@pytest.fixture
def paper_context() -> AdapterContext:
    return AdapterContext(
        connection_id="conn-1",
        venue_code="paper",
        environment=VenueEnvironment.PAPER,
        venue_account_ref="paper-acct-1",
    )


@pytest.fixture
def paper_adapter(
    paper_context: AdapterContext, engine: PaperEngine, clock: FrozenClock
) -> PaperAdapter:
    return PaperAdapter(paper_context, engine, clock=clock)
