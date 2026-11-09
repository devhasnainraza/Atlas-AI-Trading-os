"""Pydantic schemas for Dashboard & Analytics API (Spec 09 §2, §9)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from pydantic import BaseModel, Field


class UserLayoutRequest(BaseModel):
    layout_config: dict[str, Any] = Field(default_factory=dict)
    theme_preference: str = Field(default="DARK_OBSIDIAN", description="DARK_OBSIDIAN | MIDNIGHT_BLUE | CYBER_NEON")
    default_symbol: str = Field(default="BTC/USDT")
    default_timeframe: str = Field(default="1h")
    sound_effects_enabled: bool = Field(default=True)


class UserLayoutResponse(BaseModel):
    user_id: str
    layout_config: dict[str, Any]
    theme_preference: str
    default_symbol: str
    default_timeframe: str
    sound_effects_enabled: bool
    updated_at: str


class CreateWatchlistRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    symbols: list[str] = Field(..., min_length=1)
    is_default: bool = Field(default=False)


class WatchlistResponse(BaseModel):
    id: str
    user_id: str
    name: str
    symbols: list[str]
    sort_order: int
    is_default: bool
    created_at: str


class ScannerPresetRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    filters: dict[str, Any] = Field(default_factory=dict)
    alert_on_match: bool = Field(default=False)
    is_public: bool = Field(default=False)


class ScannerPresetResponse(BaseModel):
    id: str
    user_id: str
    name: str
    filters: dict[str, Any]
    alert_on_match: bool
    is_public: bool
    created_at: str


class AgentTelemetryResponse(BaseModel):
    name: str
    role: str
    state: str
    current_task: str
    confidence_score: Decimal


class PortfolioTelemetryResponse(BaseModel):
    balance_usd: Decimal
    equity_usd: Decimal
    free_margin_usd: Decimal
    used_margin_usd: Decimal
    daily_pnl_usd: Decimal
    daily_pnl_pct: Decimal
    margin_level_pct: Decimal


class CockpitOverviewResponse(BaseModel):
    user_id: str
    portfolio: PortfolioTelemetryResponse
    open_positions: list[dict[str, Any]]
    agents: list[AgentTelemetryResponse]
    consensus_confidence: Decimal
    circuit_breaker_status: str
    active_mandates_count: int
    generated_at: str
