"""Pydantic schemas for Trading Automation API requests and responses (Spec 06 §2, §9)."""

from __future__ import annotations

from decimal import Decimal
from pydantic import BaseModel, Field


class CreateMandateRequest(BaseModel):
    account_id: str = Field(..., description="Target venue account UUID")
    mode: str = Field(default="SEMI_AUTOMATIC", description="MANUAL | SEMI_AUTOMATIC | FULLY_AUTOMATIC")
    allowed_symbols: list[str] = Field(..., min_length=1, description="Whitelisted trading instruments")
    max_capital_risk_pct: Decimal = Field(default=Decimal("1.50"), ge=Decimal("0.10"), le=Decimal("5.00"))
    daily_loss_limit_usd: Decimal = Field(default=Decimal("500.00"), gt=Decimal("0.00"))
    max_open_positions: int = Field(default=3, ge=1, le=10)
    news_protection: bool = Field(default=True)
    session_restrictions: list[str] = Field(default_factory=lambda: ["LONDON", "NEW_YORK"])
    mandate_signature: str = Field(..., description="Cryptographic signature confirming authorization")
    expires_in_days: int = Field(default=30, ge=1, le=365)


class AutomationMandateResponse(BaseModel):
    id: str
    user_id: str
    account_id: str
    mode: str
    allowed_symbols: list[str]
    max_capital_risk_pct: Decimal
    daily_loss_limit_usd: Decimal
    max_open_positions: int
    news_protection: bool
    session_restrictions: list[str]
    is_active: bool
    expires_at: str
    created_at: str


class PositionGuardCreateRequest(BaseModel):
    position_id: str = Field(..., description="Venue position reference ID")
    account_id: str = Field(..., description="Venue account UUID")
    symbol: str = Field(..., description="Trading pair e.g. BTC/USDT or EUR/USD")
    side: str = Field(..., description="LONG or SHORT")
    entry_price: Decimal = Field(..., gt=Decimal("0"))
    atr: Decimal | None = Field(default=None, gt=Decimal("0"))
    initial_stop_loss: Decimal | None = Field(default=None, gt=Decimal("0"))
    tp1_price: Decimal | None = Field(default=None, gt=Decimal("0"))
    tp2_price: Decimal | None = Field(default=None, gt=Decimal("0"))
    tp3_price: Decimal | None = Field(default=None, gt=Decimal("0"))
    breakeven_offset: Decimal = Field(default=Decimal("0"))
    trailing_distance: Decimal = Field(default=Decimal("0"))


class PositionGuardResponse(BaseModel):
    id: str
    position_id: str
    symbol: str
    side: str
    entry_price: Decimal
    current_stop_loss: Decimal
    initial_stop_loss: Decimal
    tp1_price: Decimal
    tp2_price: Decimal
    tp3_price: Decimal
    breakeven_reached: bool
    tp1_filled: bool
    tp2_filled: bool
    trailing_active: bool
    trailing_distance: Decimal
    highest_price_seen: Decimal
    lowest_price_seen: Decimal
    status: str
    updated_at: str


class TickEvaluationRequest(BaseModel):
    current_price: Decimal = Field(..., gt=Decimal("0"))


class TickEvaluationResponse(BaseModel):
    position_id: str
    current_price: Decimal
    actions_triggered: list[str]
    guard: PositionGuardResponse


class CircuitBreakerStatusResponse(BaseModel):
    user_id: str
    mode: str
    active_mandates_count: int
    circuit_breaker_active: bool
    circuit_breaker_reason: str | None
    daily_loss_usd: Decimal
    daily_loss_limit_usd: Decimal
    protected_positions_count: int


class EmergencyStopRequest(BaseModel):
    flatten_open_positions: bool = Field(default=False)
    confirmation_token: str = Field(..., description="Explicit security token e.g. EMERGENCY_HALT")


class EmergencyStopResponse(BaseModel):
    status: str
    mandates_suspended: int
    orders_cancelled: int
    positions_flattened: int
    timestamp: str


class CircuitBreakerResetRequest(BaseModel):
    admin_token: str = Field(..., description="Administrative authorization token")
