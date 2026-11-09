"""API contract tests for Memory, Journal & Learning module (Spec 07 §9)."""

from datetime import datetime, timezone
from decimal import Decimal
import pytest
from atlas_api.testing import build_test_app, make_client


@pytest.mark.asyncio
async def test_record_and_annotate_journal_entry_api():
    app = build_test_app()
    now = datetime.now(timezone.utc).isoformat()

    async with make_client(app) as client:
        # 1. Record a closed trade
        record_resp = await client.post(
            "/v1/journal/entries",
            json={
                "order_id": "ord-win-101",
                "account_id": "acc-venue-101",
                "symbol": "BTC/USDT",
                "side": "LONG",
                "entry_price": "65000.00",
                "exit_price": "67500.00",
                "stop_loss_price": "64000.00",
                "entry_time": now,
                "exit_time": now,
                "net_pnl": "1250.00",
                "fees_usd": "12.50",
                "slippage_pips": "0.20",
                "technical_indicators": {"rsi": 62.5, "atr": 450.0},
            },
        )
        assert record_resp.status_code == 200
        data = record_resp.json()
        assert data["symbol"] == "BTC/USDT"
        assert Decimal(str(data["net_pnl"])) == Decimal("1250.00")
        assert Decimal(str(data["r_multiple"])) == Decimal("2.50")  # (67500-65000)/1000
        assert "storage.atlas.internal" in data["chart_image_url"]
        assert len(data["ai_post_mortem"]) > 20
        entry_id = data["id"]

        # 2. Annotate entry
        annotate_resp = await client.post(
            f"/v1/journal/entries/{entry_id}/annotate",
            json={
                "user_notes": "Followed trading plan perfectly. Good patient entry.",
                "emotional_tags": ["CALM", "DISCIPLINED"],
                "user_rating": 5,
            },
        )
        assert annotate_resp.status_code == 200
        annotated_data = annotate_resp.json()
        assert annotated_data["user_rating"] == 5
        assert "CALM" in annotated_data["emotional_tags"]
        assert annotated_data["user_notes"] == "Followed trading plan perfectly. Good patient entry."

        # 3. Retrieve entry
        get_resp = await client.get(f"/v1/journal/entries/{entry_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == entry_id


@pytest.mark.asyncio
async def test_bias_profile_and_coaching_report_api():
    app = build_test_app()
    async with make_client(app) as client:
        # Bias profile
        bias_resp = await client.get("/v1/journal/biases")
        assert bias_resp.status_code == 200
        bias_data = bias_resp.json()
        assert Decimal(str(bias_data["discipline_rating"])) > Decimal("50.00")
        assert "LATE_NY_SESSION" in bias_data["top_mistake_triggers"]

        # Coaching report
        coaching_resp = await client.get("/v1/journal/coaching/latest")
        assert coaching_resp.status_code == 200
        coaching_data = coaching_resp.json()
        assert len(coaching_data["disciplined_actions"]) > 0
        assert len(coaching_data["recommendations"]) > 0


@pytest.mark.asyncio
async def test_episodic_memory_store_and_list_api():
    app = build_test_app()
    async with make_client(app) as client:
        # Store memory rule
        store_resp = await client.post(
            "/v1/journal/memory",
            json={
                "scope": "RULES",
                "memory_text": "Never risk more than 1.5% on any single trade setup.",
                "importance_weight": "0.95",
            },
        )
        assert store_resp.status_code == 200
        stored_data = store_resp.json()
        assert stored_data["scope"] == "RULES"
        assert stored_data["memory_text"] == "Never risk more than 1.5% on any single trade setup."

        # List memories
        list_resp = await client.get("/v1/journal/memory?scope=RULES")
        assert list_resp.status_code == 200
        memories = list_resp.json()
        assert len(memories) >= 1
        assert any("1.5%" in m["memory_text"] for m in memories)


@pytest.mark.asyncio
async def test_decision_chain_journal_api():
    """Tests the 7-step decision chain storage and retrieval per prompt.md Feature 7."""
    app = build_test_app()
    async with make_client(app) as client:
        resp = await client.get("/v1/journal/decision-chains")
        assert resp.status_code == 200
        chains = resp.json()
        assert len(chains) >= 1

        chain = chains[0]
        # Verify exact 7 links in chain
        assert "market_state" in chain
        assert "agent_observations" in chain
        assert "decision" in chain
        assert "risk_assessment" in chain
        assert "user_approval" in chain
        assert "execution" in chain
        assert "result" in chain

        # Individual fetch
        single_resp = await client.get(f"/v1/journal/decision-chains/{chain['id']}")
        assert single_resp.status_code == 200
        assert single_resp.json()["symbol"] == "BTC/USDT"

