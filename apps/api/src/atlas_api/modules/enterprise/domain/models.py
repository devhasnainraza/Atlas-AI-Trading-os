"""Domain models for Enterprise Features (Spec 10 §2, §5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
import uuid


@dataclass
class Organization:
    id: str
    name: str
    slug: str
    plan_tier: str  # TEAM | INSTITUTIONAL | ENTERPRISE
    custom_domain: str | None = None
    white_label_settings: dict[str, Any] = field(default_factory=dict)
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    max_seats: int = 10
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Team:
    id: str
    org_id: str
    name: str
    allocated_capital_usd: Decimal
    risk_budget_pct: Decimal
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Membership:
    id: str
    org_id: str
    user_id: str
    role: str  # Org_Owner | Risk_Officer | Portfolio_Manager | Senior_Trader | Junior_Trader | Auditor
    team_id: str | None = None
    max_lot_size: Decimal = Decimal("10.00")
    max_risk_per_trade_pct: Decimal = Decimal("1.00")
    requires_dual_approval: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class OrgRiskPolicy:
    id: str
    org_id: str
    max_org_daily_drawdown_pct: Decimal = Decimal("4.00")
    max_portfolio_leverage: Decimal = Decimal("5.00")
    allowed_venues: tuple[str, ...] = ("binance", "ibkr", "oanda")
    dual_approval_threshold_usd: Decimal = Decimal("100000.00")
    emergency_halt_active: bool = False
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class EnterpriseWebhook:
    id: str
    org_id: str
    target_url: str
    secret_hash: str
    subscribed_events: tuple[str, ...]
    is_active: bool = True
    failure_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
