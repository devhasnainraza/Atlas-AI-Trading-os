"""Tests for agent state schemas and initialization (Spec 03 §6)."""

from decimal import Decimal
from atlas_api.modules.agents.domain.state import create_initial_state
from atlas_api.modules.agents.schemas import AgentRecommendationResponse


def test_create_initial_state():
    state = create_initial_state(
        session_id="test-session-123",
        user_id="user-456",
        user_query="Analyze BTC/USDT momentum",
        symbol="BTC/USDT",
        timeframe="4h",
    )

    assert state["session_id"] == "test-session-123"
    assert state["user_id"] == "user-456"
    assert state["symbol"] == "BTC/USDT"
    assert state["timeframe"] == "4h"
    assert state["status"] == "ACTIVE"
    assert state["confidence_score"] == "0.00"
    assert state["requires_human_approval"] is False
    assert len(state["messages"]) == 1
    assert state["messages"][0]["content"] == "Analyze BTC/USDT momentum"


def test_agent_recommendation_4_part_contract():
    rec = AgentRecommendationResponse(
        confidence_score=Decimal("84.50"),
        evidence=["Bullish breakout above 65000", "Volume expansion +35%"],
        risks=["Approaching historical resistance at 68000"],
        alternative_scenarios=["If 4h closes below 64500, invalidate long bias"],
        synthesized_recommendation="BUY BTC/USDT with 1.5% portfolio risk",
    )

    assert rec.confidence_score == Decimal("84.50")
    assert len(rec.evidence) == 2
    assert len(rec.risks) == 1
    assert len(rec.alternative_scenarios) == 1
