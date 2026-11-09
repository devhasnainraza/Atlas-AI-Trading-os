"""Pydantic schemas for Enterprise Features API (Spec 10 §2, §9)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from pydantic import BaseModel, Field


class CreateOrganizationRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=50)
    plan_tier: str = Field(default="TEAM", description="TEAM | INSTITUTIONAL | ENTERPRISE")
    max_seats: int = Field(default=10, ge=1, le=500)


class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    plan_tier: str
    custom_domain: str | None
    max_seats: int
    created_at: str


class InviteMemberRequest(BaseModel):
    user_id: str = Field(...)
    role: str = Field(default="Junior_Trader", description="Org_Owner | Risk_Officer | Senior_Trader | Junior_Trader | Auditor")
    max_lot_size: Decimal = Field(default=Decimal("5.00"), gt=Decimal("0.00"))
    max_risk_per_trade_pct: Decimal = Field(default=Decimal("0.50"), ge=Decimal("0.10"), le=Decimal("5.00"))
    requires_dual_approval: bool = Field(default=False)


class MembershipResponse(BaseModel):
    id: str
    org_id: str
    user_id: str
    role: str
    max_lot_size: Decimal
    max_risk_per_trade_pct: Decimal
    requires_dual_approval: bool
    created_at: str


class UpdateOrgRiskPolicyRequest(BaseModel):
    max_org_daily_drawdown_pct: Decimal = Field(default=Decimal("4.00"), ge=Decimal("1.00"), le=Decimal("20.00"))
    max_portfolio_leverage: Decimal = Field(default=Decimal("5.00"), ge=Decimal("1.00"), le=Decimal("100.00"))
    allowed_venues: list[str] = Field(default_factory=lambda: ["binance", "ibkr", "oanda"])
    dual_approval_threshold_usd: Decimal = Field(default=Decimal("100000.00"), gt=Decimal("0.00"))
    emergency_halt_active: bool = Field(default=False)


class OrgRiskPolicyResponse(BaseModel):
    org_id: str
    max_org_daily_drawdown_pct: Decimal
    max_portfolio_leverage: Decimal
    allowed_venues: list[str]
    dual_approval_threshold_usd: Decimal
    emergency_halt_active: bool


class RegisterEnterpriseWebhookRequest(BaseModel):
    target_url: str = Field(..., description="HTTPS endpoint for algorithmic event payloads")
    subscribed_events: list[str] = Field(default_factory=lambda: ["trade.executed", "risk.limit_breached"])


class EnterpriseWebhookResponse(BaseModel):
    id: str
    org_id: str
    target_url: str
    subscribed_events: list[str]
    is_active: bool
    created_at: str


class WhiteLabelConfigRequest(BaseModel):
    custom_domain: str = Field(..., description="Custom white-label domain e.g. trading.fund.com")
    brand_name: str = Field(..., min_length=2)
    logo_url: str | None = None
    primary_color: str | None = "#00F0FF"


class WhiteLabelConfigResponse(BaseModel):
    org_id: str
    custom_domain: str
    brand_name: str
    logo_url: str | None
    primary_color: str | None
