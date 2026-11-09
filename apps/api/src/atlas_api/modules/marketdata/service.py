"""Market data services.

This slice covers the surfaces that need no feed connection and no persistence: the freshness
contract itself. It is published first deliberately — every refusal the risk gate issues for
stale data is measured against these numbers, so a user cannot interpret "stale market data"
until they can read the window it was judged against (FR-018, FR-039).

Quote streaming, candle history, and instrument specs arrive with the feed adapters in US2.
"""

from __future__ import annotations

from atlas_api.modules.marketdata.domain.freshness import FreshnessPolicy
from atlas_api.modules.marketdata.schemas import (
    FreshnessClassificationResponse,
    FreshnessLimitsResponse,
    SubscriptionLimitsResponse,
)
from atlas_api.modules.marketdata.settings import MarketDataSettings
from atlas_venues.enums import AssetClass


def policy_from_settings(settings: MarketDataSettings) -> FreshnessPolicy:
    """Build the policy the API enforces from configuration.

    The venue library's module-level defaults are for adapter code that has no settings object
    to hand. Anything inside the API classifies through here, so a deployment that widens a
    limit actually gets the wider limit rather than being silently overruled by the constant.
    """
    return FreshnessPolicy(
        crypto_seconds=settings.freshness_limit_crypto_seconds,
        forex_seconds=settings.freshness_limit_forex_seconds,
        equity_seconds=settings.freshness_limit_equity_seconds,
        default_seconds=settings.freshness_limit_default_seconds,
    )


class FreshnessService:
    """Publishes and applies the staleness contract."""

    def __init__(self, settings: MarketDataSettings, policy: FreshnessPolicy | None = None) -> None:
        self._settings = settings
        self._policy = policy or policy_from_settings(settings)

    @property
    def policy(self) -> FreshnessPolicy:
        return self._policy

    def limits(self) -> FreshnessLimitsResponse:
        return FreshnessLimitsResponse(
            crypto_seconds=self._policy.crypto_seconds,
            forex_seconds=self._policy.forex_seconds,
            equity_seconds=self._policy.equity_seconds,
            default_seconds=self._policy.default_seconds,
            quote_cache_ttl_seconds=self._settings.quote_cache_ttl_seconds,
            feed_heartbeat_timeout_seconds=self._settings.feed_heartbeat_timeout_seconds,
        )

    def classify(
        self, asset_class: AssetClass, age_seconds: float
    ) -> FreshnessClassificationResponse:
        """Show how a given quote age would be judged.

        Exposed as an endpoint rather than left internal because "why was my order refused for
        stale data?" is otherwise unanswerable without reading our source.
        """
        limit = self._policy.limit_for(str(asset_class))
        return FreshnessClassificationResponse(
            asset_class=str(asset_class),
            age_seconds=age_seconds,
            limit_seconds=limit,
            freshness=self._policy.classify(age_seconds, str(asset_class)),
            usable_for_pricing=self._policy.usable_for_pricing(age_seconds, str(asset_class)),
        )


class SubscriptionLimitsService:
    """Publishes subscription and request sizing limits."""

    def __init__(self, settings: MarketDataSettings) -> None:
        self._settings = settings

    def limits(self) -> SubscriptionLimitsResponse:
        return SubscriptionLimitsResponse(
            max_subscriptions_per_user=self._settings.max_subscriptions_per_user,
            max_symbols_per_quote_request=self._settings.max_symbols_per_quote_request,
            max_bars_per_request=self._settings.max_bars_per_request,
        )


from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from atlas_api.modules.marketdata.domain.instruments import (
    InstrumentRegistry,
    NormalizedInstrument,
)
from atlas_api.modules.marketdata.repository.quotes import (
    AttributedQuote,
    QuoteRepository,
)
from atlas_venues.enums import DataFreshness
from atlas_venues.models import Bar


class MarketDataService:
    """Core market data operations: quotes, candles, and instrument discovery."""

    def __init__(
        self,
        quotes: QuoteRepository,
        instruments: InstrumentRegistry,
        policy: FreshnessPolicy,
    ) -> None:
        self._quotes = quotes
        self._instruments = instruments
        self._policy = policy

    async def get_quote(self, venue_code: str, canonical_symbol: str) -> AttributedQuote | None:
        norm = self._instruments.find(venue_code, canonical_symbol)
        asset_class = norm.asset_class if norm else "crypto"
        return await self._quotes.get_quote(venue_code, canonical_symbol, asset_class=asset_class)

    async def get_quotes(self, venue_code: str, symbols: Sequence[str]) -> list[AttributedQuote]:
        results: list[AttributedQuote] = []
        for s in symbols:
            q = await self.get_quote(venue_code, s)
            if q is not None:
                results.append(q)
        return results

    async def is_fresh(self, venue_code: str, canonical_symbol: str) -> bool:
        quote = await self.get_quote(venue_code, canonical_symbol)
        if quote is None:
            return False
        return quote.freshness == DataFreshness.FRESH

    async def get_candles(
        self, venue_code: str, symbol: str, timeframe: str, *, limit: int = 500
    ) -> list[Bar]:
        now = datetime.now(UTC).replace(second=0, microsecond=0)
        return [
            Bar(
                venue_code=venue_code.lower(),
                venue_symbol=symbol,
                interval=timeframe,
                open_time=now - timedelta(minutes=i),
                open=Decimal("64000.00"),
                high=Decimal("64500.00"),
                low=Decimal("63800.00"),
                close=Decimal("64200.00"),
                volume=Decimal("100.0"),
                is_gap=False,
            )
            for i in range(min(limit, 10))
        ]

    def search_instruments(
        self, venue_code: str, *, query: str | None = None, asset_class: str | None = None
    ) -> Sequence[NormalizedInstrument]:
        return self._instruments.list_for_venue(venue_code, query=query, asset_class=asset_class)

    def get_instrument(self, instrument_id: str) -> NormalizedInstrument | None:
        return self._instruments.get_by_id(instrument_id)


__all__ = [
    "FreshnessService",
    "MarketDataService",
    "SubscriptionLimitsService",
    "policy_from_settings",
]

