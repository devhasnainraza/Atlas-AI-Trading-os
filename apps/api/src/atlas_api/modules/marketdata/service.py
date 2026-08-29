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
    """The caps a client should size its own requests against before being rejected."""

    def __init__(self, settings: MarketDataSettings) -> None:
        self._settings = settings

    def limits(self) -> SubscriptionLimitsResponse:
        return SubscriptionLimitsResponse(
            max_subscriptions_per_user=self._settings.max_subscriptions_per_user,
            max_symbols_per_quote_request=self._settings.max_symbols_per_quote_request,
            max_bars_per_request=self._settings.max_bars_per_request,
        )


__all__ = ["FreshnessService", "SubscriptionLimitsService", "policy_from_settings"]
