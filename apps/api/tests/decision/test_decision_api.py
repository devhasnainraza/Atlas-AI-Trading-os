"""API tests for the Decision Engine & Risk Management module (Spec 05 §9)."""

from decimal import Decimal
import pytest
from atlas_api.testing import build_test_app, make_client


@pytest.mark.asyncio
async def test_evaluate_setup_api_success():
    app = build_test_app()
    async with make_client(app) as client:
        resp = await client.post(
            "/v1/decision/evaluate",
            json={
                "symbol": "BTC/USDT",
                "direction": "LONG",
                "timeframe": "1h",
                "entry_price": "67500.00",
                "stop_loss_price": "66500.00",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "BTC/USDT"
    assert data["direction"] == "LONG"
    assert data["status"] == "PENDING_APPROVAL"
    assert Decimal(str(data["confidence_score"])) > Decimal("0")
    assert Decimal(str(data["calculated_position_size"])) > Decimal("0")
    assert "debate_transcript" in data
    assert len(data["debate_transcript"]["bull_arguments"]) > 0
    assert len(data["debate_transcript"]["bear_arguments"]) > 0
    assert "arbitrator_synthesis" in data["debate_transcript"]
    assert len(data["proposal_hash"]) == 64


@pytest.mark.asyncio
async def test_pending_proposals_and_approval_flow_api():
    app = build_test_app()
    async with make_client(app) as client:
        # Create a proposal
        create_resp = await client.post(
            "/v1/decision/evaluate",
            json={
                "symbol": "ETH/USDT",
                "direction": "LONG",
                "timeframe": "4h",
            },
        )
        assert create_resp.status_code == 200
        prop_id = create_resp.json()["id"]

        # Check pending list
        pending_resp = await client.get("/v1/decision/proposals/pending")
        assert pending_resp.status_code == 200
        pending_data = pending_resp.json()
        assert any(p["id"] == prop_id for p in pending_data)

        # Approve proposal
        approve_resp = await client.post(
            f"/v1/decision/proposals/{prop_id}/approve",
            json={"signature_token": "client-auth-token-123"},
        )
        assert approve_resp.status_code == 200
        approved_data = approve_resp.json()
        assert approved_data["id"] == prop_id
        assert approved_data["status"] == "APPROVED"

        # Pending list should now be empty of this proposal
        pending_resp2 = await client.get("/v1/decision/proposals/pending")
        assert pending_resp2.status_code == 200
        assert not any(p["id"] == prop_id for p in pending_resp2.json())


@pytest.mark.asyncio
async def test_proposal_rejection_api():
    app = build_test_app()
    async with make_client(app) as client:
        # Create a proposal
        create_resp = await client.post(
            "/v1/decision/evaluate",
            json={
                "symbol": "EUR/USD",
                "direction": "SHORT",
            },
        )
        assert create_resp.status_code == 200
        prop_id = create_resp.json()["id"]

        # Reject proposal
        reject_resp = await client.post(
            f"/v1/decision/proposals/{prop_id}/reject",
            json={"rejection_reason": "Risk-reward profile unfavorable in current session"},
        )
        assert reject_resp.status_code == 200
        rejected_data = reject_resp.json()
        assert rejected_data["id"] == prop_id
        assert rejected_data["status"] == "REJECTED"


@pytest.mark.asyncio
async def test_risk_rules_api():
    app = build_test_app()
    async with make_client(app) as client:
        resp = await client.get("/v1/decision/risk-rules")
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(str(data["max_risk_per_trade_pct"])) == Decimal("2.00")
    assert Decimal(str(data["max_daily_loss_pct"])) == Decimal("5.00")
    assert data["max_open_positions"] == 5
    assert data["is_active"] is True
