"""API endpoint tests for the agents module (Spec 03 §9)."""

from __future__ import annotations

from decimal import Decimal
import pytest

from atlas_api.testing import build_test_app, make_client


@pytest.mark.asyncio
async def test_agent_chat_endpoint_informational():
    app = build_test_app()
    async with make_client(app) as client:
        resp = await client.post(
            "/v1/agents/chat",
            json={
                "message": "Analyze BTC/USDT price structure",
                "symbol": "BTC/USDT",
                "timeframe": "1h",
            },
        )
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "COMPLETED"
    assert data["symbol"] == "BTC/USDT"
    assert data["requires_human_approval"] is False

    rec = data["recommendation"]
    assert Decimal(str(rec["confidence_score"])) > Decimal("0.00")
    assert len(rec["evidence"]) >= 1
    assert len(rec["risks"]) >= 1
    assert len(rec["alternative_scenarios"]) >= 1
    assert "BTC/USDT" in rec["synthesized_recommendation"]


@pytest.mark.asyncio
async def test_agent_chat_endpoint_trade_approval_flow():
    app = build_test_app()
    async with make_client(app) as client:
        # Step 1: Request trade intent
        chat_resp = await client.post(
            "/v1/agents/chat",
            json={
                "message": "Execute buy order on BTC/USDT now",
                "symbol": "BTC/USDT",
                "timeframe": "15m",
            },
        )
        assert chat_resp.status_code == 200
        data = chat_resp.json()
        assert data["status"] == "PAUSED_APPROVAL"
        assert data["requires_human_approval"] is True
        assert data["approval_ticket_id"] is not None
        session_id = data["session_id"]

        # Step 2: Query active workflows
        active_resp = await client.get("/v1/agents/active-workflows")
        assert active_resp.status_code == 200
        active_list = active_resp.json()
        matching = [w for w in active_list if w["session_id"] == session_id]
        assert len(matching) == 1
        assert matching[0]["status"] == "PAUSED_APPROVAL"

        # Step 3: Resume workflow with human approval
        resume_resp = await client.post(
            f"/v1/agents/workflows/{session_id}/resume",
            json={
                "approved": True,
                "user_notes": "Reviewed orderblock setup, approved.",
                "signature_token": "token-valid-abc",
            },
        )
        assert resume_resp.status_code == 200
        resumed_data = resume_resp.json()
        assert resumed_data["status"] == "COMPLETED"
        assert resumed_data["execution_result"] is not None
        assert resumed_data["execution_result"]["status"] == "FILLED"


@pytest.mark.asyncio
async def test_agent_workflow_cancel():
    app = build_test_app()
    async with make_client(app) as client:
        chat_resp = await client.post(
            "/v1/agents/chat",
            json={
                "message": "Buy ETH",
                "symbol": "ETH/USDT",
            },
        )
        session_id = chat_resp.json()["session_id"]

        cancel_resp = await client.post(
            f"/v1/agents/workflows/{session_id}/cancel",
            json={"reason": "Trader changed mind"},
        )
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "CANCELLED"
