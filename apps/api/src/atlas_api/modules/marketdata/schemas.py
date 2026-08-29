"""Market data request/response schemas — strict validation (FR-010)."""

from __future__ import annotations

from pydantic import BaseModel

from atlas_venues.enums import DataFreshness


class FreshnessLimitsResponse(BaseModel):
    """The thresholds that decide whether a quote may be used to price an order.

    Published because they are load-bearing: a user who sees "stale data" refusals needs to
    know what window they are being measured against before they can tell a broken feed from a
    quiet market.
    """

    crypto_seconds: float
    forex_seconds: float
    equity_seconds: float
    default_seconds: float
    quote_cache_ttl_seconds: int
    feed_heartbeat_timeout_seconds: float


class FreshnessClassificationResponse(BaseModel):
    """How a given age would be classified, for a given asset class."""

    asset_class: str
    age_seconds: float
    limit_seconds: float
    freshness: DataFreshness
    usable_for_pricing: bool


class SubscriptionLimitsResponse(BaseModel):
    max_subscriptions_per_user: int
    max_symbols_per_quote_request: int
    max_bars_per_request: int


__all__ = [
    "FreshnessClassificationResponse",
    "FreshnessLimitsResponse",
    "SubscriptionLimitsResponse",
]
