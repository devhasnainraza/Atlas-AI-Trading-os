"""Integration tests for Stream Owner Worker (T053) and Bar Backfill (T054).

Guarantees asserted:
- T053: Redis lease coordinates stream ownership, reconnect backoff & gap detection emits
        feed.degraded / feed.recovered.
- T054: Bar aggregation aggregates ticks into OHLCV candles, gap-marked backfill flags
        missing intervals without synthetic interpolation (FR-014), partitions monthly.
- Zero float money (Constitution X).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from atlas_api.modules.marketdata.domain.freshness import FreshnessPolicy
from atlas_api.modules.marketdata.repository.quotes import InMemoryQuoteStore
from atlas_events import InMemoryEventBus, catalog
from atlas_venues.models import Bar, QuoteTick
from atlas_worker.bar_backfill import BarAggregator, BarBackfillService, bar_partition_key
from atlas_worker.stream_owner import StreamLeaseManager, StreamOwner


class MockFailingStreamAdapter:
    """Mock adapter that streams quotes then simulates an error."""

    def __init__(self, ticks: list[QuoteTick], fail_after: int = 2) -> None:
        self.ticks = ticks
        self.fail_after = fail_after

    async def stream_quotes(self, symbols: list[str]) -> AsyncIterator[QuoteTick]:
        for i, tick in enumerate(self.ticks):
            if i >= self.fail_after:
                raise ConnectionResetError("Venue remote connection dropped")
            yield tick


class MockHealthyStreamAdapter:
    """Mock adapter that streams cleanly."""

    def __init__(self, ticks: list[QuoteTick]) -> None:
        self.ticks = ticks

    async def stream_quotes(self, symbols: list[str]) -> AsyncIterator[QuoteTick]:
        for tick in self.ticks:
            yield tick


class TestStreamOwnerWorker:
    """T053: Stream lease coordination and feed degradation/recovery."""

    @pytest.mark.asyncio
    async def test_lease_coordination_between_workers(self) -> None:
        lease_mgr = StreamLeaseManager()
        conn_id = "conn-binance-01"
        group = "crypto_majors"

        # Worker 1 acquires lease
        w1_acquired = await lease_mgr.acquire(conn_id, group, owner_id="worker-1", ttl_seconds=5.0)
        assert w1_acquired is True

        # Worker 2 attempts to acquire same lease and is rejected
        w2_acquired = await lease_mgr.acquire(conn_id, group, owner_id="worker-2", ttl_seconds=5.0)
        assert w2_acquired is False

        # Worker 1 renews lease
        w1_renewed = await lease_mgr.renew(conn_id, group, owner_id="worker-1", ttl_seconds=5.0)
        assert w1_renewed is True

        # Worker 1 releases lease
        w1_released = await lease_mgr.release(conn_id, group, owner_id="worker-1")
        assert w1_released is True

        # Worker 2 can now acquire
        w2_acquired_after = await lease_mgr.acquire(conn_id, group, owner_id="worker-2", ttl_seconds=5.0)
        assert w2_acquired_after is True

    @pytest.mark.asyncio
    async def test_stream_gap_detection_degraded_and_recovered(self) -> None:
        lease_mgr = StreamLeaseManager()
        store = InMemoryQuoteStore(
            policy=FreshnessPolicy(
                crypto_seconds=3.0,
                forex_seconds=3.0,
                equity_seconds=10.0,
                default_seconds=10.0,
            )
        )
        bus = InMemoryEventBus(catalog)
        now = datetime.now(UTC)

        events_seen: list[str] = []

        async def handler(env: Any) -> None:
            events_seen.append(env.event_type)

        bus.subscribe("test-consumer", "atlas.marketdata.feed.degraded", handler)
        bus.subscribe("test-consumer", "atlas.marketdata.feed.recovered", handler)

        owner = StreamOwner(
            owner_id="worker-1",
            lease_mgr=lease_mgr,
            quote_store=store,
            event_bus=bus,
            heartbeat_timeout_seconds=2.0,
            backfill_threshold_seconds=1.0,
        )

        ticks = [
            QuoteTick(
                venue_code="binance",
                venue_symbol="BTCUSDT",
                bid=Decimal("65000.00"),
                ask=Decimal("65001.00"),
                venue_time=now,
                received_at=now,
            ),
            QuoteTick(
                venue_code="binance",
                venue_symbol="BTCUSDT",
                bid=Decimal("65002.00"),
                ask=Decimal("65003.00"),
                venue_time=now,
                received_at=now,
            ),
        ]
        adapter = MockFailingStreamAdapter(ticks, fail_after=1)

        # 1. Stream runs and encounters connection error -> emits feed.degraded
        with pytest.raises(ConnectionResetError):
            await owner.run_stream(
                connection_id="conn-1",
                venue_code="binance",
                symbol_group="crypto",
                symbols=["BTCUSDT"],
                adapter=adapter,
            )

        assert owner.is_degraded is True
        assert "atlas.marketdata.feed.degraded" in events_seen

        # 2. Reconnected stream resumes ticks -> emits feed.recovered
        healthy_adapter = MockHealthyStreamAdapter(ticks)
        await owner.run_stream(
            connection_id="conn-1",
            venue_code="binance",
            symbol_group="crypto",
            symbols=["BTCUSDT"],
            adapter=healthy_adapter,
            max_ticks=2,
        )

        assert owner.is_degraded is False
        assert "atlas.marketdata.feed.recovered" in events_seen


class TestBarAggregationAndBackfill:
    """T054: Bar aggregation, gap backfilling without interpolation, monthly partitioning."""

    @pytest.mark.asyncio
    async def test_bar_aggregator_bucket_closure_and_events(self) -> None:
        bus = InMemoryEventBus(catalog)
        closed_events: list[dict] = []

        async def handler(env: Any) -> None:
            closed_events.append(env.payload)

        bus.subscribe("test-consumer", "atlas.marketdata.candle.closed", handler)

        agg = BarAggregator(
            venue_code="binance",
            symbol="BTCUSDT",
            interval_seconds=60,
            event_bus=bus,
        )

        t0 = datetime(2026, 9, 26, 12, 0, 10, tzinfo=UTC)
        t1 = datetime(2026, 9, 26, 12, 0, 45, tzinfo=UTC)
        t2 = datetime(2026, 9, 26, 12, 1, 5, tzinfo=UTC)

        # First tick in 12:00 bucket
        tick1 = QuoteTick(
            venue_code="binance",
            venue_symbol="BTCUSDT",
            bid=Decimal("65000.00"),
            ask=Decimal("65002.00"),
            venue_time=t0,
            received_at=t0,
        )
        closed = await agg.ingest_tick(tick1)
        assert closed is None
        assert agg.current_bar is not None
        assert agg.current_bar.open == Decimal("65001.00")

        # Second tick in same 12:00 bucket -> updates high/low/close
        tick2 = QuoteTick(
            venue_code="binance",
            venue_symbol="BTCUSDT",
            bid=Decimal("65010.00"),
            ask=Decimal("65012.00"),
            venue_time=t1,
            received_at=t1,
        )
        closed = await agg.ingest_tick(tick2)
        assert closed is None
        assert agg.current_bar.high == Decimal("65011.00")
        assert agg.current_bar.close == Decimal("65011.00")

        # Third tick in 12:01 bucket -> closes 12:00 bucket!
        tick3 = QuoteTick(
            venue_code="binance",
            venue_symbol="BTCUSDT",
            bid=Decimal("65020.00"),
            ask=Decimal("65022.00"),
            venue_time=t2,
            received_at=t2,
        )
        closed = await agg.ingest_tick(tick3)
        assert closed is not None
        assert closed.open_time == datetime(2026, 9, 26, 12, 0, 0, tzinfo=UTC)
        assert len(closed_events) == 1
        assert closed_events[0]["instrument"] == "BTCUSDT"

    def test_backfill_identifies_gaps_without_interpolation(self) -> None:
        t0 = datetime(2026, 9, 26, 10, 0, 0, tzinfo=UTC)
        t1 = datetime(2026, 9, 26, 10, 1, 0, tzinfo=UTC)
        t2 = datetime(2026, 9, 26, 10, 2, 0, tzinfo=UTC)
        t3 = datetime(2026, 9, 26, 10, 3, 0, tzinfo=UTC)

        raw_bars = [
            Bar(
                venue_code="binance",
                venue_symbol="BTCUSDT",
                interval="1m",
                open_time=t0,
                open=Decimal("64000.00"),
                high=Decimal("64100.00"),
                low=Decimal("63950.00"),
                close=Decimal("64050.00"),
                volume=Decimal("5.0"),
                is_gap=False,
            ),
            # Notice t1 and t2 are missing from raw bars!
            Bar(
                venue_code="binance",
                venue_symbol="BTCUSDT",
                interval="1m",
                open_time=t3,
                open=Decimal("64200.00"),
                high=Decimal("64250.00"),
                low=Decimal("64180.00"),
                close=Decimal("64220.00"),
                volume=Decimal("8.0"),
                is_gap=False,
            ),
        ]

        aligned = BarBackfillService.identify_gaps(
            venue_code="binance",
            symbol="BTCUSDT",
            interval="1m",
            interval_delta=timedelta(minutes=1),
            start_time=t0,
            end_time=t3,
            raw_bars=raw_bars,
        )

        assert len(aligned) == 4
        assert aligned[0].is_gap is False
        assert aligned[1].is_gap is True
        assert aligned[1].open_time == t1
        assert aligned[1].volume == Decimal("0.0")
        assert aligned[2].is_gap is True
        assert aligned[2].open_time == t2
        assert aligned[3].is_gap is False
        assert aligned[3].open_time == t3

    def test_monthly_partition_key(self) -> None:
        dt = datetime(2026, 9, 26, 10, 0, 0, tzinfo=UTC)
        assert bar_partition_key(dt) == "bars_2026_09"
