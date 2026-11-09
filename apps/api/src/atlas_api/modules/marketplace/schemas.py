"""Pydantic schemas for AI Marketplace & Creator Ecosystem (Spec 12 §2, §5)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class SubmitPluginRequest(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    slug: str = Field(min_length=3, max_length=50)
    plugin_type: str = Field(default="STRATEGY")
    pricing_model: str = Field(default="FREE")
    price_usd: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    version: str = Field(default="1.0.0")
    manifest: dict[str, Any] = Field(default_factory=dict)
    source_code: str = Field(default="")
    backtest_metrics: dict[str, Any] = Field(default_factory=dict)


class MarketplacePluginResponse(BaseModel):
    id: str
    creator_id: str
    slug: str
    name: str
    plugin_type: str
    current_version: str
    pricing_model: str
    price_usd: Decimal
    status: str
    rating_avg: Decimal
    rating_count: int
    install_count: int
    manifest: dict[str, Any]
    backtest_metrics: dict[str, Any]
    created_at: datetime


class InstallPluginRequest(BaseModel):
    target_account_id: str
    config: dict[str, Any] = Field(default_factory=dict)


class InstallationResponse(BaseModel):
    id: str
    user_id: str
    plugin_id: str
    target_account_id: str
    installed_version: str
    is_active: bool
    config: dict[str, Any]
    installed_at: datetime


class CreateReviewRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    review_title: str = Field(min_length=3, max_length=120)
    review_body: str = Field(min_length=5, max_length=2000)


class ReviewResponse(BaseModel):
    id: str
    plugin_id: str
    user_id: str
    rating: int
    review_title: str
    review_body: str
    is_verified_purchaser: bool
    created_at: datetime


class CreatorEarningsResponse(BaseModel):
    creator_id: str
    stripe_connect_id: str
    payout_status: str
    total_revenue_usd: Decimal
    creator_earnings_usd: Decimal
    platform_fees_usd: Decimal
