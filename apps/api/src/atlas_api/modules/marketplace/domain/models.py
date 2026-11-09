"""Domain models for AI Marketplace & Creator Ecosystem (Spec 12 §2, §5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
import uuid


@dataclass
class MarketplacePlugin:
    id: str
    creator_id: str
    slug: str
    name: str
    plugin_type: str  # AGENT | STRATEGY | INDICATOR | PROMPT | WORKFLOW | DASHBOARD
    current_version: str
    pricing_model: str  # FREE | ONE_TIME | SUBSCRIPTION
    price_usd: Decimal
    status: str  # IN_REVIEW | APPROVED | REJECTED | SUSPENDED
    rating_avg: Decimal
    rating_count: int
    install_count: int
    manifest: dict[str, Any]
    backtest_metrics: dict[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class MarketplaceInstallation:
    id: str
    user_id: str
    plugin_id: str
    target_account_id: str
    installed_version: str
    is_active: bool = True
    config: dict[str, Any] = field(default_factory=dict)
    installed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class MarketplaceReview:
    id: str
    plugin_id: str
    user_id: str
    rating: int  # 1 to 5
    review_title: str
    review_body: str
    is_verified_purchaser: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class CreatorAccount:
    id: str
    user_id: str
    stripe_connect_id: str
    payout_status: str  # ACTIVE | PENDING_KYC | RESTRICTED
    total_revenue_usd: Decimal = Decimal("0.00")
    creator_earnings_usd: Decimal = Decimal("0.00")
    platform_fees_usd: Decimal = Decimal("0.00")
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
