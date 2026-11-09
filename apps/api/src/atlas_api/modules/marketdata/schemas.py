"""Market data request/response schemas — strict validation (FR-010)."""

from __future__ import annotations

from pydantic import BaseModel

from atlas_venues.enums import DataFreshness


from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from atlas_venues.enums import DataFreshness


class FreshnessLimitsResponse(BaseModel):
    """The thresholds that decide whether a quote may be used to price an order."""

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


class QuoteResponse(BaseModel):
    venue_code: str
    symbol: str
    bid: Decimal
    ask: Decimal
    last: Decimal
    observed_at: datetime
    age_seconds: float
    freshness: str


class QuoteListResponse(BaseModel):
    items: list[QuoteResponse]


class CandleResponse(BaseModel):
    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    is_gap: bool
    source: str = "aggregated"


class CandleListResponse(BaseModel):
    venue_code: str
    symbol: str
    timeframe: str
    items: list[CandleResponse]


class InstrumentResponse(BaseModel):
    id: str
    venue_code: str
    canonical_symbol: str
    venue_symbol: str
    asset_class: str
    base_currency: str | None = None
    quote_currency: str | None = None
    price_precision: int
    tick_size: Decimal
    quantity_min: Decimal
    quantity_max: Decimal | None = None
    quantity_step: Decimal
    contract_size: Decimal
    max_leverage: Decimal
    session_state: str
    next_session_change_at: datetime | None = None
    tradable: bool
    spec_version: int
    refreshed_at: datetime


class InstrumentListResponse(BaseModel):
    items: list[InstrumentResponse]


class SubscriptionResponse(BaseModel):
    id: str
    connection_id: str
    symbol: str
    state: str = "active"
    subscribed_at: datetime


class SubscriptionListResponse(BaseModel):
    items: list[SubscriptionResponse]


class SubscribeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connection_id: str
    symbols: list[str]


__all__ = [
    "CandleListResponse",
    "CandleResponse",
    "FreshnessClassificationResponse",
    "FreshnessLimitsResponse",
    "InstrumentListResponse",
    "InstrumentResponse",
    "QuoteListResponse",
    "QuoteResponse",
    "SubscribeRequest",
    "SubscriptionLimitsResponse",
    "SubscriptionListResponse",
    "SubscriptionResponse",
]

