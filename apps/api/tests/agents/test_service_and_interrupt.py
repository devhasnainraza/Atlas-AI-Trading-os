"""Tests for AgentOrchestrationService and human approval interrupt gate (Spec 03 US1, US3)."""

import pytest
from atlas_api.modules.agents.service import AgentOrchestrationService


@pytest.mark.asyncio
async def test_informational_workflow_runs_to_completion():
    service = AgentOrchestrationService()
    state = await service.run_analysis(
        session_id="session-info-1",
        user_id="user-1",
        query="What is your analysis on BTC/USDT?",
        symbol="BTC/USDT",
    )

    assert state["status"] == "COMPLETED"
    assert state["requires_human_approval"] is False
    assert state["approval_ticket_id"] is None
    assert len(state["evidence"]) > 0
    assert len(state["risks"]) > 0
    assert len(state["alternative_scenarios"]) > 0


@pytest.mark.asyncio
async def test_trade_intent_workflow_pauses_for_human_approval():
    service = AgentOrchestrationService()
    state = await service.run_analysis(
        session_id="session-trade-1",
        user_id="user-1",
        query="Please execute a buy order on BTC/USDT",
        symbol="BTC/USDT",
    )

    # Must unconditionally pause before execution_agent
    assert state["status"] == "PAUSED_APPROVAL"
    assert state["requires_human_approval"] is True
    assert state["approval_ticket_id"] is not None
    assert state["execution_result"] is None

    # Checkpoints verify state persistence
    checkpoints = await service.checkpointer.list_checkpoints("session-trade-1")
    assert len(checkpoints) >= 4

    # Resume with approval
    resumed = await service.resume_workflow(
        session_id="session-trade-1",
        approved=True,
        signature_token="sig-valid-123",
    )
    assert resumed["status"] == "COMPLETED"
    assert resumed["human_approved"] is True
    assert resumed["execution_result"] is not None
    assert resumed["execution_result"]["status"] == "FILLED"


@pytest.mark.asyncio
async def test_trade_intent_workflow_rejected_by_human():
    service = AgentOrchestrationService()
    await service.run_analysis(
        session_id="session-reject-1",
        user_id="user-1",
        query="Buy SOL now",
        symbol="SOL/USDT",
    )

    # Resume with rejection
    resumed = await service.resume_workflow(
        session_id="session-reject-1",
        approved=False,
    )
    assert resumed["status"] == "REJECTED"
    assert resumed["human_approved"] is False
    assert resumed["execution_result"] is None


@pytest.mark.asyncio
async def test_cancel_workflow():
    service = AgentOrchestrationService()
    await service.run_analysis(
        session_id="session-cancel-1",
        user_id="user-1",
        query="Buy ETH now",
        symbol="ETH/USDT",
    )

    cancelled = await service.cancel_workflow(
        session_id="session-cancel-1",
        reason="Market shifted",
    )
    assert cancelled["status"] == "CANCELLED"
