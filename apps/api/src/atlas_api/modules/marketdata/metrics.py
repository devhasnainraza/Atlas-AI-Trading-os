"""Market data metrics and telemetry (Spec 03 US2, T058).

Tracks:
- Quote lag histogram (observation-to-receive latency in ms, SC-002)
- Stale quote counter (quotes that aged past freshness limits, FR-018)
- Stream reconnect rate (reconnect attempts and recovery events)
- Feed degraded gauge (number of feeds currently in degraded state)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class MarketDataMetrics:
    """In-memory metrics accumulator for market data telemetry."""

    quote_lags_ms: list[float] = field(default_factory=list)
    stale_quotes_count: int = 0
    stream_reconnects_count: int = 0
    degraded_feeds: set[str] = field(default_factory=set)

    def record_quote_lag(self, lag_ms: float) -> None:
        self.quote_lags_ms.append(lag_ms)
        # Keep window bounded
        if len(self.quote_lags_ms) > 10_000:
            self.quote_lags_ms = self.quote_lags_ms[-5_000:]

    def record_stale_quote(self, venue_code: str, symbol: str) -> None:
        self.stale_quotes_count += 1

    def record_stream_reconnect(self, connection_id: str) -> None:
        self.stream_reconnects_count += 1

    def set_feed_degraded(self, feed_id: str, degraded: bool) -> None:
        if degraded:
            self.degraded_feeds.add(feed_id)
        else:
            self.degraded_feeds.discard(feed_id)

    @property
    def feed_degraded_count(self) -> int:
        return len(self.degraded_feeds)

    def p95_lag_ms(self) -> float:
        if not self.quote_lags_ms:
            return 0.0
        sorted_lags = sorted(self.quote_lags_ms)
        idx = int(0.95 * len(sorted_lags))
        return sorted_lags[min(idx, len(sorted_lags) - 1)]

    def snapshot(self) -> dict[str, float | int]:
        return {
            "p95_lag_ms": self.p95_lag_ms(),
            "stale_quotes_count": self.stale_quotes_count,
            "stream_reconnects_count": self.stream_reconnects_count,
            "feed_degraded_count": self.feed_degraded_count,
        }


# Global singleton instance for easy collection
metrics = MarketDataMetrics()

__all__ = ["MarketDataMetrics", "metrics"]
