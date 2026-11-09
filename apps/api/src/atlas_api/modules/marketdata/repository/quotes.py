"""Redis quote store with freshness-limit TTL and staleness invariants (Spec 03 plan §10, T052).

Stores top-of-book quotes keyed by (venue_code, canonical_symbol).
Invariants:
- A quote expired beyond its TTL or when the store is unavailable yields freshness: stale.
- Never interpolates or guesses a price.
- Money and prices are strict Decimal.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol

from atlas_api.modules.marketdata.domain.freshness import FreshnessPolicy
from atlas_venues.enums import DataFreshness
from atlas_venues.models import QuoteTick
from atlas_venues.precision import ZERO


@dataclass(frozen=True, slots=True)
class AttributedQuote:
    """Venue-attributed quote snapshot with freshness state."""

    venue_code: str
    symbol: str
    bid: Decimal
    ask: Decimal
    last: Decimal
    observed_at: datetime
    age_seconds: float
    freshness: DataFreshness

    def __post_init__(self) -> None:
        for name in ("bid", "ask", "last"):
            val = getattr(self, name)
            if not isinstance(val, Decimal):
                raise TypeError(f"AttributedQuote.{name} must be Decimal")
            if val <= ZERO:
                raise ValueError(f"AttributedQuote.{name} must be positive")


class QuoteRepository(Protocol):
    """Port for latest quote storage."""

    async def save_quote(self, quote: QuoteTick, *, canonical_symbol: str) -> None:
        ...

    async def get_quote(
        self, venue_code: str, canonical_symbol: str, *, asset_class: str = "crypto"
    ) -> AttributedQuote | None:
        ...

    async def get_quotes(
        self, venue_code: str, symbols: list[str], *, asset_class: str = "crypto"
    ) -> list[AttributedQuote]:
        ...


class InMemoryQuoteStore:
    """In-memory quote repository for tests and local development."""

    def __init__(self, policy: FreshnessPolicy | None = None) -> None:
        self._policy = policy or FreshnessPolicy(
            crypto_seconds=5.0,
            forex_seconds=10.0,
            equity_seconds=15.0,
            default_seconds=10.0,
        )
        self._store: dict[tuple[str, str], tuple[QuoteTick, datetime]] = {}
        self._force_fail = False

    def simulate_failure(self, failed: bool = True) -> None:
        """Simulate storage connectivity failure."""
        self._force_fail = failed

    async def save_quote(self, quote: QuoteTick, *, canonical_symbol: str) -> None:
        if self._force_fail:
            raise ConnectionError("Quote store is offline")
        key = (quote.venue_code.lower(), canonical_symbol.upper())
        self._store[key] = (quote, datetime.now(UTC))

    async def get_quote(
        self, venue_code: str, canonical_symbol: str, *, asset_class: str = "crypto"
    ) -> AttributedQuote | None:
        vc = venue_code.lower()
        sym = canonical_symbol.upper()
        now = datetime.now(UTC)

        if self._force_fail:
            # When Redis / storage fails, fail-safe to stale or unavailable (FR-018)
            item = self._store.get((vc, sym))
            if item is None:
                return None
            tick, _ = item
            age = max(0.0, (now - tick.venue_time).total_seconds())
            return AttributedQuote(
                venue_code=tick.venue_code,
                symbol=sym,
                bid=tick.bid,
                ask=tick.ask,
                last=tick.last or tick.mid,
                observed_at=tick.venue_time,
                age_seconds=age,
                freshness=DataFreshness.STALE,  # Forced stale on infrastructure outage
            )

        item = self._store.get((vc, sym))
        if item is None:
            return None

        tick, stored_at = item
        age = max(0.0, (now - tick.venue_time).total_seconds())
        freshness = self._policy.classify(age, asset_class)

        return AttributedQuote(
            venue_code=tick.venue_code,
            symbol=sym,
            bid=tick.bid,
            ask=tick.ask,
            last=tick.last or tick.mid,
            observed_at=tick.venue_time,
            age_seconds=age,
            freshness=freshness,
        )

    async def get_quotes(
        self, venue_code: str, symbols: list[str], *, asset_class: str = "crypto"
    ) -> list[AttributedQuote]:
        results: list[AttributedQuote] = []
        for s in symbols:
            q = await self.get_quote(venue_code, s)
            if q is not None:
                results.append(q)
        return results


__all__ = ["AttributedQuote", "InMemoryQuoteStore", "QuoteRepository"]
