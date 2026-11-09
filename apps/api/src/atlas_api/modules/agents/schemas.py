"""Schemas for the agents module API (Spec 03 §9)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentChatRequest(BaseModel):
    """User input initiating or continuing multi-agent analysis."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(..., min_length=1, max_length=4000)
    symbol: str = Field(default="BTC/USDT", max_length=32)
    timeframe: str = Field(default="1h", max_length=16)
    session_id: str | None = Field(default=None, max_length=128)


class AgentRecommendationResponse(BaseModel):
    """Constitutional 4-part output contract (Principle III)."""

    confidence_score: Decimal = Field(..., ge=Decimal("0.00"), le=Decimal("100.00"))
    evidence: list[str] = Field(..., min_length=1)
    risks: list[str] = Field(..., min_length=1)
    alternative_scenarios: list[str] = Field(..., min_length=1)
    synthesized_recommendation: str

    @field_validator("confidence_score", mode="before")
    @classmethod
    def parse_confidence(cls, v: Any) -> Decimal:
        if isinstance(v, (str, int, float)):
            return Decimal(str(v)).quantize(Decimal("0.01"))
        if isinstance(v, Decimal):
            return v.quantize(Decimal("0.01"))
        raise ValueError("Invalid confidence score format")


class AgentChatResponse(BaseModel):
    """Full envelope returned by agent analysis endpoint."""

    session_id: str
    symbol: str
    status: str
    recommendation: AgentRecommendationResponse
    requires_human_approval: bool
    approval_ticket_id: str | None = None
    execution_result: dict[str, Any] | None = None


class WorkflowResumeRequest(BaseModel):
    """User decision resuming a paused LangGraph execution."""

    model_config = ConfigDict(extra="forbid")

    approved: bool
    user_notes: str | None = Field(default=None, max_length=1000)
    signature_token: str | None = Field(default=None, max_length=256)


class WorkflowCancelRequest(BaseModel):
    """Aborts an active or paused agent workflow."""

    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default="Cancelled by user", max_length=500)


class ActiveWorkflowSummary(BaseModel):
    """Summary of active or paused agent execution thread."""

    session_id: str
    symbol: str
    current_node: str
    status: str
    requires_human_approval: bool
    approval_ticket_id: str | None = None
    created_at: str
