"""Clock injection, venue time correction, and freshness classification (T020).

Freshness is a safety control, not a display nicety: FR-039 requires refusal when risk inputs
are stale, so "how old is this quote?" must be exact and deterministic.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from atlas_venues.enums import DataFreshness
from atlas_venues.models import VenueTimeOffset
from atlas_venues.timing import (
    FrozenClock,
    SystemClock,
    VenueClock,
    classify_freshness,
    freshness_limit_for,
    measure_offset,
)

T0 = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)


class TestClocks:
    def test_system_clock_is_utc_aware(self) -> None:
        assert SystemClock().now().tzinfo is not None

    def test_frozen_clock_only_moves_when_told(self) -> None:
        clock = FrozenClock(T0)
        assert clock.now() == T0
        assert clock.now() == T0
        clock.advance(5)
        assert clock.now() == T0 + timedelta(seconds=5)

    def test_frozen_clock_rejects_naive_datetimes(self) -> None:
        """A naive datetime silently compares as UTC and hides a timezone bug."""
        with pytest.raises(ValueError, match="naive datetimes"):
            FrozenClock(datetime(2026, 8, 25, 12, 0, 0))


class TestVenueClock:
    def test_zero_offset_passes_through(self) -> None:
        vc = VenueClock(FrozenClock(T0))
        assert vc.age_seconds(T0 - timedelta(seconds=2)) == pytest.approx(2.0)

    def test_venue_running_fast_does_not_make_data_look_stale(self) -> None:
        """A venue 2s ahead stamps 'now' as T0+2; without correction that reads as future data."""
        offset = VenueTimeOffset(
            venue_code="x", offset_seconds=2.0, round_trip_seconds=0.05, measured_at=T0
        )
        vc = VenueClock(FrozenClock(T0), offset)
        assert vc.age_seconds(T0 + timedelta(seconds=2)) == pytest.approx(0.0)

    def test_venue_running_slow_is_corrected_too(self) -> None:
        offset = VenueTimeOffset(
            venue_code="x", offset_seconds=-3.0, round_trip_seconds=0.05, measured_at=T0
        )
        vc = VenueClock(FrozenClock(T0), offset)
        assert vc.age_seconds(T0 - timedelta(seconds=3)) == pytest.approx(0.0)

    def test_age_is_never_negative(self) -> None:
        vc = VenueClock(FrozenClock(T0))
        assert vc.age_seconds(T0 + timedelta(seconds=30)) == 0.0

    def test_offset_is_flagged_as_significant_past_one_second(self) -> None:
        assert VenueTimeOffset("x", 1.5, 0.1, T0).is_significant
        assert not VenueTimeOffset("x", 0.4, 0.1, T0).is_significant


class TestFreshness:
    def test_limits_by_asset_class(self) -> None:
        assert freshness_limit_for("crypto") == 3.0
        assert freshness_limit_for("forex") == 3.0
        assert freshness_limit_for("equity") == 10.0

    @pytest.mark.parametrize(
        ("age", "asset_class", "expected"),
        [
            (0.5, "crypto", DataFreshness.FRESH),
            (3.0, "crypto", DataFreshness.FRESH),
            (3.1, "crypto", DataFreshness.STALE),
            (9.9, "equity", DataFreshness.FRESH),
            (10.1, "equity", DataFreshness.STALE),
        ],
    )
    def test_boundary_is_inclusive_then_stale(
        self, age: float, asset_class: str, expected: DataFreshness
    ) -> None:
        assert classify_freshness(age, asset_class) is expected

    def test_there_is_no_third_state(self) -> None:
        """Fresh or stale. 'Probably fine' is how a stale price becomes a real loss."""
        assert set(DataFreshness) == {DataFreshness.FRESH, DataFreshness.STALE}


class TestMeasureOffset:
    def test_symmetric_latency_midpoint(self) -> None:
        sent = T0
        received = T0 + timedelta(seconds=0.100)
        venue_time = T0 + timedelta(seconds=2.050)  # midpoint is T0+0.05, so offset is 2.0
        offset = measure_offset("x", sent_at=sent, venue_time=venue_time, received_at=received)
        assert offset.offset_seconds == pytest.approx(2.0)
        assert offset.round_trip_seconds == pytest.approx(0.100)
