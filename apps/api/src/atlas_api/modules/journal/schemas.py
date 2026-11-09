"""Pydantic schemas for Memory, Journal & Learning API requests and responses (Spec 07 §2, §9)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from pydantic import BaseModel, Field


class CreateJournalEntryRequest(BaseModel):
    order_id: str = Field(..., description="Unique fill/order UUID")
    account_id: str = Field(..., description="Venue account UUID")
    symbol: str = Field(..., description="e.g. EUR/USD or BTC/USDT")
    side: str = Field(..., description="LONG or SHORT")
    entry_price: Decimal = Field(..., gt=Decimal("0"))
    exit_price: Decimal = Field(..., gt=Decimal("0"))
    stop_loss_price: Decimal = Field(..., gt=Decimal("0"))
    entry_time: str
    exit_time: str
    net_pnl: Decimal
    fees_usd: Decimal = Field(default=Decimal("0.00"))
    slippage_pips: Decimal = Field(default=Decimal("0.00"))
    technical_indicators: dict[str, Any] = Field(default_factory=dict)


class AnnotateJournalEntryRequest(BaseModel):
    user_notes: str = Field(..., description="Subjective trader notes and reflections")
    emotional_tags: list[str] = Field(
        default_factory=lambda: ["DISCIPLINED"],
        description="Tags: CALM, FOMO, REVENGE, GREED, FEAR, DISCIPLINED",
    )
    user_rating: int = Field(default=5, ge=1, le=5, description="Self-rating from 1 to 5 stars")


class TradeJournalResponse(BaseModel):
    id: str
    user_id: str
    order_id: str
    symbol: str
    side: str
    entry_price: Decimal
    exit_price: Decimal
    entry_time: str
    exit_time: str
    net_pnl: Decimal
    r_multiple: Decimal
    fees_usd: Decimal
    slippage_pips: Decimal
    chart_image_url: str
    technical_indicators: dict[str, Any]
    ai_post_mortem: str
    user_notes: str
    emotional_tags: list[str]
    user_rating: int | None
    created_at: str


class CognitiveBiasProfileResponse(BaseModel):
    user_id: str
    fomo_score: Decimal
    revenge_trading_score: Decimal
    loss_aversion_score: Decimal
    overtrading_score: Decimal
    discipline_rating: Decimal
    top_mistake_triggers: list[str]
    last_updated: str


class CoachingReportResponse(BaseModel):
    id: str
    user_id: str
    period_start: str
    period_end: str
    net_pnl: Decimal
    profit_factor: Decimal
    win_rate: Decimal
    total_trades: int
    disciplined_actions: list[str]
    cognitive_bias_warnings: list[str]
    recommendations: list[str]
    created_at: str


class StoreMemoryRequest(BaseModel):
    scope: str = Field(default="RULES", description="STRATEGY | BEHAVIOR | GOALS | RULES | LESSONS")
    memory_text: str = Field(..., min_length=5, description="Trader rule or episodic statement")
    importance_weight: Decimal = Field(default=Decimal("0.80"), ge=Decimal("0.10"), le=Decimal("1.00"))


class MemoryItemResponse(BaseModel):
    id: str
    user_id: str
    scope: str
    memory_text: str
    importance_weight: Decimal
    created_at: str
