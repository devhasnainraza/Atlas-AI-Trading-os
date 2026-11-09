"""Injected clocks (Spec 01 plan §7; the same seam Spec 03 uses for venues).

Security code never calls ``datetime.now()`` directly. It takes a :class:`Clock` so that
token expiry, lockout backoff, step-up freshness, and session age are all deterministic
under test. This matters more here than anywhere else in the platform: a test that cannot
freeze time cannot prove that a refresh token expires at 90 days rather than asserting it
and hoping the clock agrees.

:class:`Clock` is a structural Protocol, so it is interchangeable with the identically-shaped
clock in ``atlas_venues.timing`` — a :class:`SystemClock` satisfies both. The two live apart
because auth must not import the trading package (import-linter enforces that), not because
they mean different things.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    """The only source of "now" in security code."""

    def now(self) -> datetime: ...


class SystemClock:
    """Real UTC time. The production binding."""

    __slots__ = ()

    def now(self) -> datetime:
        return datetime.now(UTC)


class FrozenClock:
    """A clock that only moves when a test moves it.

    Every returned datetime is UTC-aware: a naive "now" compared against a ``timestamptz``
    read back from Postgres raises, and the failure looks like a timezone bug in the service
    rather than a test artifact.
    """

    __slots__ = ("_now",)

    def __init__(self, now: datetime) -> None:
        self._now = _require_aware(now)

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> datetime:
        """Move forward by ``seconds`` (may be fractional or negative) and return the new now."""
        self._now = self._now + timedelta(seconds=seconds)
        return self._now

    def set(self, now: datetime) -> None:
        self._now = _require_aware(now)


def _require_aware(moment: datetime) -> datetime:
    if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        raise ValueError("FrozenClock requires a timezone-aware datetime")
    return moment.astimezone(UTC)


__all__ = ["Clock", "FrozenClock", "SystemClock"]
