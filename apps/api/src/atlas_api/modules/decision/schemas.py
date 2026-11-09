"""Schemas for the Decision Engine and Risk Management API (Spec 05 §9)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class EvaluateSetupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(..., max_length=32)
    direction: str = Field(default="LONG", max_length=16)
    timeframe: str = Field(default="1h", max_length=16)
    entry_price: Decimal | None = None
    stop_loss_price: Decimal | None = None


class DebateTranscriptResponse(BaseModel):
    bull_arguments: list[str]
    bear_arguments: list[str]
    arbitrator_synthesis: str
    identified_fallacies: list[str] = []


class TradeProposalResponse(BaseModel):
    id: str
    symbol: str
    direction: str
    confidence_score: Decimal
    entry_range_min: Decimal
    entry_range_max: Decimal
    stop_loss: Decimal
    take_profit_levels: list[Decimal]
    risk_reward_ratio: Decimal
    risk_amount_usd: Decimal
    calculated_position_size: Decimal
    proposal_hash: str
    evidence: list[str]
    risks: list[str]
    alternative_scenarios: list[str]
    debate_transcript: DebateTranscriptResponse
    status: str
    expires_at: str
    created_at: str


class ProposalApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signature_token: str | None = Field(default=None, max_length=256)
    user_notes: str | None = Field(default=None, max_length=1000)


class ProposalRejectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rejection_reason: str = Field(default="Trader declined setup", max_length=500)


class RiskRulesResponse(BaseModel):
    user_id: str
    max_risk_per_trade_pct: Decimal
    max_daily_loss_pct: Decimal
    max_drawdown_pct: Decimal
    max_open_positions: int
    max_leverage: Decimal
    is_active: bool
