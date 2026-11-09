"""Bar aggregation and gap-marked historical backfill service (Spec 03 US2, T054).

Aggregates ticks into interval candles and emits candle.closed events.
Fills missing historical intervals with is_gap=True markers without price interpolation (FR-014).
Partitions bar storage monthly for scalable partitioning.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from atlas_events import EventBus, EventEnvelope
from atlas_observability import get_logger
from atlas_venues.models import Bar, QuoteTick

logger = get_logger("atlas_worker.bar_backfill")


def bar_partition_key(dt: datetime) -> str:
    """Format monthly partition table identifier."""
    return dt.strftime("bars_%Y_%m")


class BarAggregator:
    """Aggregates streaming ticks into OHLCV candles."""

    def __init__(
        self,
        venue_code: str,
        symbol: str,
        interval_seconds: int = 60,
        event_bus: EventBus | None = None,
    ) -> None:
        self.venue_code = venue_code
        self.symbol = symbol
        self.interval_seconds = interval_seconds
        self._bus = event_bus
        self.current_bar: Bar | None = None
        self.current_bucket_start: datetime | None = None

    def _bucket_start(self, dt: datetime) -> datetime:
        total_sec = int(dt.timestamp())
        bucket_sec = total_sec - (total_sec % self.interval_seconds)
        return datetime.fromtimestamp(bucket_sec, tz=UTC)

    async def ingest_tick(self, tick: QuoteTick) -> Bar | None:
        """Ingest a tick and return closed bar if bucket boundary is crossed."""
        closed_bar: Bar | None = None
        tick_time = tick.venue_time or tick.received_at
        bucket_start = self._bucket_start(tick_time)
        price = (
            tick.last
            if tick.last is not None and tick.last > Decimal("0")
            else (tick.bid + tick.ask) / Decimal("2")
        )

        if self.current_bar is None:
            self.current_bucket_start = bucket_start
            self.current_bar = Bar(
                venue_code=self.venue_code,
                venue_symbol=self.symbol,
                interval=f"{self.interval_seconds // 60}m" if self.interval_seconds >= 60 else f"{self.interval_seconds}s",
                open_time=bucket_start,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=Decimal("1.0"),
                is_gap=False,
            )
        elif bucket_start > self.current_bucket_start:  # type: ignore[operator]
            closed_bar = self.current_bar
            if self._bus is not None:
                envelope = EventEnvelope(
                    event_type="atlas.marketdata.candle.closed",
                    producer="worker",
                    payload={
                        "instrument": self.symbol,
                        "timeframe": closed_bar.interval,
                        "open_time": closed_bar.open_time.isoformat(),
                    },
                )
                await self._bus.publish(envelope)

            # Start new bar
            self.current_bucket_start = bucket_start
            self.current_bar = Bar(
                venue_code=self.venue_code,
                venue_symbol=self.symbol,
                interval=closed_bar.interval,
                open_time=bucket_start,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=Decimal("1.0"),
                is_gap=False,
            )
        else:
            # Update existing bar
            b = self.current_bar
            self.current_bar = Bar(
                venue_code=b.venue_code,
                venue_symbol=b.venue_symbol,
                interval=b.interval,
                open_time=b.open_time,
                open=b.open,
                high=max(b.high, price),
                low=min(b.low, price),
                close=price,
                volume=b.volume + Decimal("1.0"),
                is_gap=False,
            )

        return closed_bar


class BarBackfillService:
    """Detects historical interval gaps and writes gap-marked records without interpolation."""

    @staticmethod
    def identify_gaps(
        venue_code: str,
        symbol: str,
        interval: str,
        interval_delta: timedelta,
        start_time: datetime,
        end_time: datetime,
        raw_bars: Sequence[Bar],
    ) -> list[Bar]:
        """Align bars to regular intervals, inserting is_gap=True bars for missing intervals."""
        bars_by_time = {b.open_time: b for b in raw_bars}
        aligned_bars: list[Bar] = []

        curr = start_time
        last_known_price = Decimal("0")
        if raw_bars:
            last_known_price = raw_bars[0].close

        while curr <= end_time:
            if curr in bars_by_time:
                b = bars_by_time[curr]
                aligned_bars.append(b)
                last_known_price = b.close
            else:
                # Missing interval: explicit gap bar with zero volume (FR-014)
                gap_bar = Bar(
                    venue_code=venue_code,
                    venue_symbol=symbol,
                    interval=interval,
                    open_time=curr,
                    open=last_known_price,
                    high=last_known_price,
                    low=last_known_price,
                    close=last_known_price,
                    volume=Decimal("0.0"),
                    is_gap=True,
                )
                aligned_bars.append(gap_bar)
            curr += interval_delta

        return aligned_bars


__all__ = ["BarAggregator", "BarBackfillService", "bar_partition_key"]
