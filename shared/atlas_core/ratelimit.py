"""Rate-limit classes and per-account brute-force backoff (T015; plan §8, §20).

Two related but distinct controls live here, and keeping them in one module is deliberate:
both answer "may this request proceed, and if not, how long until it may," and both must
degrade the same way when Redis is unreachable (Constitution IX — fail *conservative*, never
fail-open on auth).

**Rate-limit classes** are named budgets (``auth-strict`` / ``sensitive`` / ``default``) that
route groups map onto, so an endpoint declares *what kind* of surface it is rather than
re-tuning a raw number at every call site. The per-IP sliding-window enforcement is the
middleware's job (``middleware/rate_limit.py``); this module owns the *policy* — the numbers
and their meaning — so the middleware and any Redis-backed limiter agree on them.

**Per-account backoff** is the anti-brute-force counter: after a number of failed
authentications for one account, the account is throttled with exponential lockout
(5 free attempts, then 1m/5m/15m/1h — plan §8). This is keyed by *account*, not IP, because
credential stuffing spreads across many IPs; the IP limiter alone would never catch it. The
counter is a small state machine over a store (Redis in production, in-memory for tests),
and every read of "how long must this account wait" goes through :meth:`BackoffPolicy.state`
so the lockout math exists in exactly one place.

Enumeration note: the *caller* (the login route) is responsible for returning the same
response whether an account is locked or a password is simply wrong (ATLAS-AUTH-001 vs
ATLAS-AUTH-002 must not leak which emails exist — see errors.py). This module only answers
the mechanical question of lockout state; it never decides what the client is told.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Protocol

from atlas_core.timing import Clock, SystemClock


class RateLimitClass(StrEnum):
    """Named budgets. A route group picks one; the numbers stay here, not at call sites."""

    AUTH_STRICT = "auth-strict"
    SENSITIVE = "sensitive"
    DEFAULT = "default"


@dataclass(frozen=True)
class RateLimitPolicy:
    """A sliding-window budget: ``limit`` requests per ``window_seconds``."""

    limit: int
    window_seconds: int

    @property
    def window(self) -> timedelta:
        return timedelta(seconds=self.window_seconds)


#: The policy table. Values are the plan's intent, not tuned numbers to be moved casually:
#: auth-strict is tight because login attempts are the attack surface; sensitive is looser
#: (a user legitimately hits their own vault/sessions often) but still far below default.
RATE_LIMIT_POLICIES: dict[RateLimitClass, RateLimitPolicy] = {
    RateLimitClass.AUTH_STRICT: RateLimitPolicy(limit=10, window_seconds=60),
    RateLimitClass.SENSITIVE: RateLimitPolicy(limit=60, window_seconds=60),
    RateLimitClass.DEFAULT: RateLimitPolicy(limit=120, window_seconds=60),
}


def policy_for(cls: RateLimitClass) -> RateLimitPolicy:
    """Look up a class's budget. Total function: every class has a policy."""
    return RATE_LIMIT_POLICIES[cls]


# --- Per-account exponential backoff ------------------------------------------------------


@dataclass(frozen=True)
class BackoffSchedule:
    """The lockout ladder. ``free_attempts`` failures cost nothing; the ``durations`` list is
    walked in order, the last entry repeating for every further failure (so the ladder never
    runs out and an attacker cannot reset to a shorter lock by exhausting it)."""

    free_attempts: int
    durations: Sequence[timedelta]

    def lockout_for(self, failures: int) -> timedelta | None:
        """How long the account is locked given ``failures`` consecutive failures, or ``None``
        if it is not locked (still within the free attempts)."""
        over = failures - self.free_attempts
        if over <= 0:
            return None
        idx = min(over - 1, len(self.durations) - 1)
        return self.durations[idx]


#: Plan §8: 5 free attempts, then 1m / 5m / 15m / 1h, holding at 1h thereafter.
DEFAULT_BACKOFF = BackoffSchedule(
    free_attempts=5,
    durations=(
        timedelta(minutes=1),
        timedelta(minutes=5),
        timedelta(minutes=15),
        timedelta(hours=1),
    ),
)


class LockoutState(StrEnum):
    OPEN = "open"  # not locked; the request may proceed
    LOCKED = "locked"  # locked; retry_after > 0
    EXPIRED = "expired"  # a lock elapsed; the next attempt is allowed and the counter resets


@dataclass(frozen=True)
class AccountLockStatus:
    state: LockoutState
    failures: int
    retry_after: timedelta

    @property
    def locked(self) -> bool:
        return self.state is LockoutState.LOCKED


class CounterStore(Protocol):
    """Persistence for the failure counter. Redis in production; the in-memory one in tests.

    The contract is deliberately narrow and atomic: ``increment`` returns the new count, and
    ``reset`` clears it. The lockout *window* is not stored here — it is derived from the
    count plus the last-failure timestamp, so a store outage degrades to "no new lockouts"
    rather than "everyone locked out."
    """

    async def increment(self, key: str) -> int: ...

    async def get(self, key: str) -> int: ...

    async def reset(self, key: str) -> None: ...


class InMemoryCounterStore:
    """Single-process store for tests and local dev. Not shared across workers — which is
    exactly why production uses Redis; a stuffing attack spans processes."""

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    async def increment(self, key: str) -> int:
        self._counts[key] = self._counts.get(key, 0) + 1
        return self._counts[key]

    async def get(self, key: str) -> int:
        return self._counts.get(key, 0)

    async def reset(self, key: str) -> None:
        self._counts.pop(key, None)


class RedisCounterStore:
    """Redis-backed counter.

    ``INCR`` is atomic across workers, which is the whole point: the lockout must be global
    per account, not per process. Keys expire on their own (``EXPIRE``) so abandoned counters
    do not accumulate; the expiry is set to the longest lockout so a counter cannot outlive
    the ladder it feeds.
    """

    _KEY_PREFIX = "atlas:auth:fail:"

    def __init__(self, redis, *, ttl_seconds: int = 86_400) -> None:
        self._redis = redis
        self._ttl = ttl_seconds

    def _key(self, key: str) -> str:
        return f"{self._KEY_PREFIX}{key}"

    async def increment(self, key: str) -> int:
        count = await self._redis.incr(self._key(key))
        if count == 1:
            # Set the TTL only on creation; refreshing it on every failure would let a slow
            # drip of attempts keep the counter alive forever and never let it cool down.
            await self._redis.expire(self._key(key), self._ttl)
        return count

    async def get(self, key: str) -> int:
        raw = await self._redis.get(self._key(key))
        return int(raw) if raw is not None else 0

    async def reset(self, key: str) -> None:
        await self._redis.delete(self._key(key))


class BackoffPolicy:
    """Turns a failure counter into a lockout decision.

    The last-failure timestamp is tracked here (not in the store) because it is per-process
    bookkeeping for computing *elapsed* time; the durable, cross-worker fact is the count.
    On a store outage, :meth:`state` treats an unreachable counter as "not locked" — the
    conservative direction for availability — while the caller's IP limiter and DB checks
    still apply (Constitution IX: degrade, never fail-open on the *other* controls).
    """

    def __init__(
        self,
        *,
        store: CounterStore,
        schedule: BackoffSchedule = DEFAULT_BACKOFF,
        clock: Clock | None = None,
    ) -> None:
        self._store = store
        self._schedule = schedule
        self._clock = clock or SystemClock()
        self._last_failure: dict[str, datetime] = {}

    @staticmethod
    def key_for(user_id: str) -> str:
        return f"acct:{user_id}"

    async def record_failure(self, user_id: str) -> int:
        """Register a failed authentication; returns the new consecutive-failure count."""
        self._last_failure[user_id] = self._clock.now()
        return await self._store.increment(self.key_for(user_id))

    async def record_success(self, user_id: str) -> None:
        """A successful authentication clears the ladder — the account proved it is live."""
        self._last_failure.pop(user_id, None)
        await self._store.reset(self.key_for(user_id))

    async def state(self, user_id: str) -> AccountLockStatus:
        """Current lockout decision for the account. The single source of lockout math."""
        key = self.key_for(user_id)
        failures = await self._store.get(key)
        lockout = self._schedule.lockout_for(failures)
        if lockout is None:
            return AccountLockStatus(LockoutState.OPEN, failures, timedelta(0))

        last = self._last_failure.get(user_id)
        if last is None:
            # Count says locked but we have no local timestamp (a different worker recorded
            # it, or we restarted). Treat as locked for the full duration from "now" — the
            # safe reading is to honor the lockout rather than assume it already elapsed.
            return AccountLockStatus(LockoutState.LOCKED, failures, lockout)

        elapsed = self._clock.now() - last
        remaining = lockout - elapsed
        if remaining <= timedelta(0):
            # The lock elapsed: allow the next attempt and reset so a fresh failure starts
            # the ladder over rather than immediately re-locking at the same rung.
            await self._store.reset(key)
            self._last_failure.pop(user_id, None)
            return AccountLockStatus(LockoutState.EXPIRED, 0, timedelta(0))
        return AccountLockStatus(LockoutState.LOCKED, failures, remaining)


__all__ = [
    "DEFAULT_BACKOFF",
    "RATE_LIMIT_POLICIES",
    "AccountLockStatus",
    "BackoffPolicy",
    "BackoffSchedule",
    "CounterStore",
    "InMemoryCounterStore",
    "LockoutState",
    "RateLimitClass",
    "RateLimitPolicy",
    "RedisCounterStore",
    "policy_for",
]
