"""Tests for specialized agent graph nodes and hard risk vetoes (Spec 03 §5, §7)."""

import pytest
from atlas_api.modules.agents.domain.nodes import (
    execution_agent_node,
    manager_agent_node,
    market_agent_node,
    risk_agent_node,
    technical_agent_node,
)
from atlas_api.modules.agents.domain.state import create_initial_state
from atlas_core.errors import ValidationError


@pytest.mark.asyncio
async def test_market_and_technical_nodes():
    state = create_initial_state(
        session_id="s1",
        user_id="u1",
        user_query="Analyze ETH/USDT",
        symbol="ETH/USDT",
    )

    market_delta = await market_agent_node(state)
    assert "market_data" in market_delta
    assert market_delta["market_data"]["symbol"] == "ETH/USDT"

    state.update(market_delta)  # type: ignore
    tech_delta = await technical_agent_node(state)
    assert "technical_analysis" in tech_delta
    assert tech_delta["technical_analysis"]["trend"] == "BULLISH_CONTINUATION"


@pytest.mark.asyncio
async def test_risk_node_normal_vs_hard_veto():
    # Normal case
    normal_state = create_initial_state(
        session_id="s2",
        user_id="u1",
        user_query="Evaluate trade",
        symbol="EUR/USD",
    )
    risk_normal = await risk_agent_node(normal_state)
    assert risk_normal["risk_evaluation"]["passed"] is True
    assert risk_normal["risk_evaluation"]["hard_veto"] is False

    # Hard veto simulation
    breach_state = create_initial_state(
        session_id="s3",
        user_id="u1",
        user_query="Evaluate trade simulate_risk_breach",
        symbol="EUR/USD",
    )
    risk_breach = await risk_agent_node(breach_state)
    assert risk_breach["risk_evaluation"]["passed"] is False
    assert risk_breach["risk_evaluation"]["hard_veto"] is True
    assert risk_breach["status"] == "REJECTED"


@pytest.mark.asyncio
async def test_manager_node_respects_hard_veto():
    state = create_initial_state(
        session_id="s4",
        user_id="u1",
        user_query="Buy BTC",
        symbol="BTC/USDT",
    )
    state["risk_evaluation"] = {
        "passed": False,
        "hard_veto": True,
        "reason": "DAILY_LOSS_LIMIT_EXCEEDED",
    }

    manager_delta = await manager_agent_node(state)
    assert manager_delta["status"] == "REJECTED"
    assert manager_delta["confidence_score"] == "0.00"
    assert manager_delta["requires_human_approval"] is False
    assert "Hard risk veto active" in manager_delta["synthesized_recommendation"]


@pytest.mark.asyncio
async def test_execution_node_blocks_unapproved_invocation():
    state = create_initial_state(
        session_id="s5",
        user_id="u1",
        user_query="Buy BTC",
        symbol="BTC/USDT",
    )
    state["human_approved"] = False

    with pytest.raises(ValidationError, match="verified human approval token"):
        await execution_agent_node(state)
