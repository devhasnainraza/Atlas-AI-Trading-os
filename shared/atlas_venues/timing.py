"""Injected clocks and venue time correction (Spec 03 plan §4, T020).

Trading domain code never calls ``datetime.now()``. It takes a :class:`Clock` so that every
freshness check, expiry, and timeout is deterministic under test — a rule that matters here
because "is this quote too old to trade on?" must be reproducible.

Venue clocks drift. :class:`VenueClock` corrects venue timestamps by a measured offset before
comparing them to Atlas time, so a venue running fast does not make fresh data look stale.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol

from atlas_venues.enums import DataFreshness
from atlas_venues.models import VenueTimeOffset

# Freshness limits by asset class (plan §4). A quote older than this is not tradable.
FRESHNESS_LIMITS_SECONDS: dict[str, float] = {
    "crypto": 3.0,
    "forex": 3.0,
    "default": 10.0,
}


class Clock(Protocol):
    """The only source of 'now' in trading code."""

    def now(self) -> datetime: ...


class SystemClock:
    """Real UTC time. The production binding."""

    __slots__ = ()

    def now(self) -> datetime:
        return datetime.now(UTC)


class FrozenClock:
    """A clock that only moves when a test moves it."""

    __slots__ = ("_now",)

    def __init__(self, now: datetime) -> None:
        self._now = _require_aware(now)

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> datetime:
        self._now = self._now + timedelta(seconds=seconds)
        return self._now

    def set(self, now: datetime) -> None:
        self._now = _require_aware(now)


class VenueClock:
    """Atlas time plus a venue's measured offset.

    ``offset_seconds`` is *venue minus Atlas*: a venue two seconds ahead has ``+2.0``, and its
    timestamps are shifted back by two seconds before any age comparison.
    """

    __slots__ = ("_clock", "_offset")

    def __init__(self, clock: Clock, offset: VenueTimeOffset | None = None) -> None:
        self._clock = clock
        self._offset = offset

    @property
    def offset_seconds(self) -> float:
        return self._offset.offset_seconds if self._offset else 0.0

    def now(self) -> datetime:
        return self._clock.now()

    def with_offset(self, offset: VenueTimeOffset) -> VenueClock:
        return VenueClock(self._clock, offset)

    def to_atlas_time(self, venue_time: datetime) -> datetime:
        """Restate a venue timestamp on the Atlas timeline."""
        return _require_aware(venue_time) - timedelta(seconds=self.offset_seconds)

    def age_seconds(self, venue_time: datetime) -> float:
        """How old a venue-stamped value is, offset-corrected. Never negative."""
        return max(0.0, (self.now() - self.to_atlas_time(venue_time)).total_seconds())


def freshness_limit_for(asset_class: str) -> float:
    return FRESHNESS_LIMITS_SECONDS.get(asset_class, FRESHNESS_LIMITS_SECONDS["default"])


def classify_freshness(age_seconds: float, asset_class: str) -> DataFreshness:
    """Fresh or stale — there is no 'probably fine' (FR-018, FR-039)."""
    limit = freshness_limit_for(asset_class)
    return DataFreshness.FRESH if age_seconds <= limit else DataFreshness.STALE


def measure_offset(
    venue_code: str,
    *,
    sent_at: datetime,
    venue_time: datetime,
    received_at: datetime,
) -> VenueTimeOffset:
    """Estimate skew from one round trip, assuming symmetric latency."""
    round_trip = (received_at - sent_at).total_seconds()
    midpoint = sent_at + timedelta(seconds=round_trip / 2)
    return VenueTimeOffset(
        venue_code=venue_code,
        offset_seconds=(venue_time - midpoint).total_seconds(),
        round_trip_seconds=round_trip,
        measured_at=received_at,
    )


def _require_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("naive datetimes are not allowed in trading code; use UTC-aware values")
    return value.astimezone(UTC)


__all__ = [
    "FRESHNESS_LIMITS_SECONDS",
    "Clock",
    "FrozenClock",
    "SystemClock",
    "VenueClock",
    "classify_freshness",
    "freshness_limit_for",
    "measure_offset",
]
