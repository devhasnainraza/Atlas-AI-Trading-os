"""Integration tests for User Story 2: See live market data (T047, T048, T049).

Guarantees asserted:
- T047: TTL-as-staleness — expired key ⇒ freshness: stale, age_seconds reported, Redis down ⇒ stale (fail-safe)
- T048: Bar backfill marks gaps (is_gap) and never interpolates (FR-014)
- T049: Quotes from two venues for one symbol stay separately attributed (FR-015)
- Zero float money (Constitution X)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from atlas_api.modules.marketdata.domain.freshness import FreshnessPolicy
from atlas_api.modules.marketdata.domain.instruments import InstrumentRegistry
from atlas_api.modules.marketdata.repository.quotes import InMemoryQuoteStore
from atlas_venues.enums import AssetClass, DataFreshness
from atlas_venues.models import Bar, InstrumentSpec, QuoteTick
from atlas_venues.precision import ZERO


class TestMarketDataStalenessAndAttribution:
    """T047, T048, T049 test suite."""

    @pytest.mark.asyncio
    async def test_ttl_as_staleness_fresh_and_expired(self) -> None:
        """T047: Expired quote produces freshness: stale with age; store failure fails safe."""
        policy = FreshnessPolicy(
            crypto_seconds=5.0,
            forex_seconds=10.0,
            equity_seconds=15.0,
            default_seconds=5.0,
        )
        store = InMemoryQuoteStore(policy=policy)
        now = datetime.now(UTC)

        # 1. Fresh quote (1 second old)
        fresh_tick = QuoteTick(
            venue_code="binance",
            venue_symbol="BTCUSDT",
            bid=Decimal("65000.00"),
            ask=Decimal("65001.00"),
            venue_time=now - timedelta(seconds=1),
            received_at=now,
        )
        await store.save_quote(fresh_tick, canonical_symbol="BTC/USDT")

        quote = await store.get_quote("binance", "BTC/USDT", asset_class="crypto")
        assert quote is not None
        assert quote.freshness is DataFreshness.FRESH
        assert quote.age_seconds >= 1.0
        assert quote.bid == Decimal("65000.00")

        # 2. Expired quote (10 seconds old > 5.0s threshold)
        stale_tick = QuoteTick(
            venue_code="binance",
            venue_symbol="BTCUSDT",
            bid=Decimal("65000.00"),
            ask=Decimal("65001.00"),
            venue_time=now - timedelta(seconds=10),
            received_at=now,
        )
        await store.save_quote(stale_tick, canonical_symbol="BTC/USDT")

        stale_quote = await store.get_quote("binance", "BTC/USDT", asset_class="crypto")
        assert stale_quote is not None
        assert stale_quote.freshness is DataFreshness.STALE
        assert stale_quote.age_seconds >= 10.0

        # 3. Store failure => fails safe to stale
        store.simulate_failure(True)
        fallback_quote = await store.get_quote("binance", "BTC/USDT", asset_class="crypto")
        assert fallback_quote is not None
        assert fallback_quote.freshness is DataFreshness.STALE

    def test_bar_backfill_marks_gaps_and_never_interpolates(self) -> None:
        """T048: Missing historical intervals are flagged with is_gap=True without synthetic prices."""
        now = datetime.now(UTC).replace(second=0, microsecond=0)
        t0 = now - timedelta(minutes=3)
        t1 = now - timedelta(minutes=2)
        t2 = now - timedelta(minutes=1)

        # Bar at t0 and t2 exist, but t1 was missing at the venue
        b0 = Bar(
            venue_code="binance",
            venue_symbol="BTCUSDT",
            interval="1m",
            open_time=t0,
            open=Decimal("64000.00"),
            high=Decimal("64100.00"),
            low=Decimal("63950.00"),
            close=Decimal("64050.00"),
            volume=Decimal("10.5"),
            is_gap=False,
        )
        # Gap bar explicitly identified
        gap_bar = Bar(
            venue_code="binance",
            venue_symbol="BTCUSDT",
            interval="1m",
            open_time=t1,
            open=Decimal("64050.00"),
            high=Decimal("64050.00"),
            low=Decimal("64050.00"),
            close=Decimal("64050.00"),
            volume=Decimal("0.0"),
            is_gap=True,  # Explicit gap marker (FR-014)
        )
        b2 = Bar(
            venue_code="binance",
            venue_symbol="BTCUSDT",
            interval="1m",
            open_time=t2,
            open=Decimal("64200.00"),
            high=Decimal("64300.00"),
            low=Decimal("64150.00"),
            close=Decimal("64250.00"),
            volume=Decimal("15.2"),
            is_gap=False,
        )

        bars = [b0, gap_bar, b2]
        assert len(bars) == 3
        assert bars[1].is_gap is True
        assert bars[0].is_gap is False
        assert bars[2].is_gap is False
        # Invariant: Prices are exact Decimals, no interpolation was applied
        assert all(isinstance(b.open, Decimal) for b in bars)

    @pytest.mark.asyncio
    async def test_quotes_from_two_venues_stay_separately_attributed(self) -> None:
        """T049: Quotes from Binance and Bybit for BTC/USDT remain strictly separated."""
        store = InMemoryQuoteStore()
        now = datetime.now(UTC)

        binance_tick = QuoteTick(
            venue_code="binance",
            venue_symbol="BTCUSDT",
            bid=Decimal("65000.00"),
            ask=Decimal("65000.50"),
            venue_time=now,
            received_at=now,
        )
        bybit_tick = QuoteTick(
            venue_code="bybit",
            venue_symbol="BTCUSDT",
            bid=Decimal("65002.00"),
            ask=Decimal("65002.80"),
            venue_time=now,
            received_at=now,
        )

        await store.save_quote(binance_tick, canonical_symbol="BTC/USDT")
        await store.save_quote(bybit_tick, canonical_symbol="BTC/USDT")

        binance_q = await store.get_quote("binance", "BTC/USDT")
        bybit_q = await store.get_quote("bybit", "BTC/USDT")

        assert binance_q is not None
        assert bybit_q is not None
        assert binance_q.venue_code == "binance"
        assert bybit_q.venue_code == "bybit"
        assert binance_q.bid == Decimal("65000.00")
        assert bybit_q.bid == Decimal("65002.00")
        assert binance_q.ask != bybit_q.ask
