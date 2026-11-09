"""Pydantic schemas for the Market Intelligence API (Spec 04 §9)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator


class HeatmapItemResponse(BaseModel):
    symbol: str
    category: str
    price: Decimal
    change_24h_pct: Decimal
    relative_volume: Decimal
    funding_rate: Decimal | None
    sentiment_score: Decimal


class HeatmapResponse(BaseModel):
    items: list[HeatmapItemResponse]
    updated_at: str


class DerivativeMetricsResponse(BaseModel):
    symbol: str
    venue: str
    open_interest: Decimal
    open_interest_usd: Decimal
    funding_rate: Decimal
    predicted_funding_rate: Decimal
    long_short_ratio: Decimal
    estimated_liquidations_long_usd: Decimal
    estimated_liquidations_short_usd: Decimal
    recorded_at: str


class WhaleTransferResponse(BaseModel):
    tx_hash: str
    blockchain: str
    asset: str
    amount: Decimal
    amount_usd: Decimal
    from_entity: str
    to_entity: str
    transfer_type: str
    detected_at: str


class WhalesListResponse(BaseModel):
    transfers: list[WhaleTransferResponse]


class MacroEventResponse(BaseModel):
    country: str
    event_name: str
    impact_level: str
    previous_value: str
    forecast_value: str
    actual_value: str | None = None
    surprise_pct: Decimal | None = None
    release_date: str


class MacroCalendarResponse(BaseModel):
    events: list[MacroEventResponse]


class FearGreedResponse(BaseModel):
    score: int = Field(..., ge=0, le=100)
    classification: str
    historical_yesterday: int
    historical_last_week: int
    updated_at: str


class NewsSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(default=5, ge=1, le=20)
    entities: list[str] | None = None


class NewsItemResponse(BaseModel):
    id: str
    source: str
    title: str
    summary: str
    url: str
    sentiment_score: Decimal
    impact_level: str
    entities: list[str]
    similarity_score: Decimal
    published_at: str


class NewsSearchResponse(BaseModel):
    results: list[NewsItemResponse]
