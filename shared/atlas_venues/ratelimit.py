"""Weight-aware token buckets, one per venue connection (Spec 03 plan §15, T022).

Venues meter differently: OANDA counts requests, Binance and Bybit count *weight* where one
call can cost 40 units. A single request counter would either throttle us far below the real
limit or blow past it. So the bucket consumes whatever the adapter's
:class:`~atlas_venues.models.RateLimitModel` declares.

Buckets are keyed per connection, not per venue: two users' credentials have independent
quotas at the venue, and sharing a bucket would let one user's polling starve another's order.

The local implementation here is the reference. In deployed environments the same interface is
backed by Redis so the budget is shared across API replicas and workers.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Protocol

from atlas_venues.errors import RateLimitedError
from atlas_venues.models import RateLimitModel
from atlas_venues.timing import Clock, SystemClock


class RateLimiter(Protocol):
    """Acquire budget before a venue call; raise or wait if there is none."""

    async def acquire(self, key: str, *, cost: int = 1, wait: bool = True) -> None: ...

    def available(self, key: str) -> float: ...


@dataclass
class _Bucket:
    capacity: float
    refill_per_second: float
    tokens: float
    last_refill: float

    def refill(self, now: float) -> None:
        elapsed = max(0.0, now - self.last_refill)
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_per_second)
        self.last_refill = now

    def seconds_until(self, cost: float) -> float:
        if self.tokens >= cost:
            return 0.0
        if self.refill_per_second <= 0:
            return float("inf")
        return (cost - self.tokens) / self.refill_per_second


class TokenBucketRateLimiter:
    """In-process token buckets keyed by connection.

    ``order_bucket_suffix`` gives order-placement calls their own budget where a venue meters
    them separately, so a burst of quote polling cannot consume the allowance an order needs.
    """

    ORDER_SUFFIX = ":orders"

    def __init__(self, clock: Clock | None = None) -> None:
        self._clock = clock or SystemClock()
        self._buckets: dict[str, _Bucket] = {}
        self._models: dict[str, RateLimitModel] = {}
        self._lock = asyncio.Lock()

    def register(self, key: str, model: RateLimitModel) -> None:
        """Declare a connection's budget. Idempotent; re-registering resets the bucket."""
        window = model.window_seconds if model.window_seconds > 0 else 1.0
        general = model.weight_per_window or model.requests_per_window or 1
        self._models[key] = model
        self._buckets[key] = _Bucket(
            capacity=float(general + model.burst_allowance),
            refill_per_second=float(general) / window,
            tokens=float(general),
            last_refill=self._monotonic(),
        )
        if model.orders_per_window:
            self._buckets[key + self.ORDER_SUFFIX] = _Bucket(
                capacity=float(model.orders_per_window),
                refill_per_second=float(model.orders_per_window) / window,
                tokens=float(model.orders_per_window),
                last_refill=self._monotonic(),
            )

    async def acquire(self, key: str, *, cost: int = 1, wait: bool = True) -> None:
        """Consume ``cost`` units, waiting for refill when permitted.

        With ``wait=False`` an exhausted bucket raises immediately — used on the order path,
        where silently sleeping would make a submission arrive at a price the user never saw.
        """
        bucket = self._buckets.get(key)
        if bucket is None:
            return  # Unregistered keys are unmetered; adapters register at connect time.
        while True:
            async with self._lock:
                now = self._monotonic()
                bucket.refill(now)
                if bucket.tokens >= cost:
                    bucket.tokens -= cost
                    return
                delay = bucket.seconds_until(cost)
            if not wait or delay == float("inf"):
                raise RateLimitedError(
                    "local rate limit budget exhausted",
                    venue_code=self._models.get(key, _UNKNOWN_MODEL).venue_code,
                    retry_after_seconds=None if delay == float("inf") else delay,
                )
            await asyncio.sleep(min(delay, 5.0))

    def available(self, key: str) -> float:
        bucket = self._buckets.get(key)
        if bucket is None:
            return float("inf")
        bucket.refill(self._monotonic())
        return bucket.tokens

    def penalize(self, key: str, *, seconds: float) -> None:
        """Drain a bucket after the venue told us we were over quota.

        Trusting the venue's own 429 over our local estimate keeps a mis-declared
        ``RateLimitModel`` from producing a retry storm.
        """
        bucket = self._buckets.get(key)
        if bucket is None:
            return
        bucket.tokens = 0.0
        bucket.last_refill = self._monotonic() + max(0.0, seconds)

    def _monotonic(self) -> float:
        return self._clock.now().timestamp()


_UNKNOWN_MODEL = RateLimitModel(venue_code="unknown", window_seconds=1.0, requests_per_window=1)

# Venue-declared budgets, deliberately set below published limits so Atlas throttles itself
# before a venue does (a venue-side ban costs far more than a local wait).
DEFAULT_RATE_LIMIT_MODELS: dict[str, RateLimitModel] = {
    "binance": RateLimitModel(
        venue_code="binance",
        window_seconds=60.0,
        weight_per_window=1000,
        orders_per_window=90,
        notes="Published 1200 weight/min; we budget 1000. Order cap 100/10s -> 90/min.",
    ),
    "bybit": RateLimitModel(
        venue_code="bybit",
        window_seconds=60.0,
        requests_per_window=500,
        orders_per_window=90,
        notes="Per-endpoint limits vary; conservative aggregate budget.",
    ),
    "oanda": RateLimitModel(
        venue_code="oanda",
        window_seconds=1.0,
        requests_per_window=90,
        notes="Published 120 req/s; we budget 90.",
    ),
    "ibkr": RateLimitModel(
        venue_code="ibkr",
        window_seconds=1.0,
        requests_per_window=40,
        orders_per_window=5,
        notes="Gateway pacing violation at 50 msg/s; we budget 40.",
    ),
    "mt5": RateLimitModel(
        venue_code="mt5",
        window_seconds=1.0,
        requests_per_window=20,
        notes="Terminal-bound via sidecar; conservative to protect the bridge.",
    ),
    "paper": RateLimitModel(
        venue_code="paper",
        window_seconds=1.0,
        requests_per_window=1000,
        notes="Local simulator; limit exists only to keep runaway loops visible.",
    ),
}


def connection_key(venue_code: str, connection_id: str) -> str:
    return f"{venue_code}:{connection_id}"


__all__ = [
    "DEFAULT_RATE_LIMIT_MODELS",
    "RateLimiter",
    "TokenBucketRateLimiter",
    "connection_key",
]
