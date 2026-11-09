"""API tests for the Trading Automation module (Spec 06 §9)."""

from decimal import Decimal
import pytest
from atlas_api.testing import build_test_app, make_client


@pytest.mark.asyncio
async def test_create_and_list_mandate_api():
    app = build_test_app()
    async with make_client(app) as client:
        create_resp = await client.post(
            "/v1/automation/mandates",
            json={
                "account_id": "acc-venue-101",
                "mode": "FULLY_AUTOMATIC",
                "allowed_symbols": ["BTC/USDT", "ETH/USDT"],
                "max_capital_risk_pct": "1.50",
                "daily_loss_limit_usd": "600.00",
                "max_open_positions": 3,
                "news_protection": True,
                "mandate_signature": "signature-auth-valid",
            },
        )
    assert create_resp.status_code == 200
    data = create_resp.json()
    assert data["mode"] == "FULLY_AUTOMATIC"
    assert "BTC/USDT" in data["allowed_symbols"]
    assert data["is_active"] is True
    mandate_id = data["id"]

    async with make_client(app) as client:
        list_resp = await client.get("/v1/automation/mandates")
        assert list_resp.status_code == 200
        mandates = list_resp.json()
        assert any(m["id"] == mandate_id for m in mandates)


@pytest.mark.asyncio
async def test_position_guard_and_tick_evaluation_api():
    app = build_test_app()
    async with make_client(app) as client:
        # 1. Register a position guard
        guard_resp = await client.post(
            "/v1/automation/guards",
            json={
                "position_id": "pos-api-77",
                "account_id": "acc-venue-101",
                "symbol": "BTC/USDT",
                "side": "LONG",
                "entry_price": "65000.00",
                "initial_stop_loss": "64000.00",
                "tp1_price": "66000.00",
                "tp2_price": "67000.00",
                "tp3_price": "68500.00",
                "breakeven_offset": "20.00",
            },
        )
        assert guard_resp.status_code == 200
        g_data = guard_resp.json()
        assert g_data["position_id"] == "pos-api-77"
        assert g_data["breakeven_reached"] is False

        # 2. Simulate tick reaching TP1 (66100)
        tick_resp = await client.post(
            "/v1/automation/guards/pos-api-77/tick",
            json={"current_price": "66100.00"},
        )
        assert tick_resp.status_code == 200
        t_data = tick_resp.json()
        assert "TP1_FILLED_BREAKEVEN_LOCKED" in t_data["actions_triggered"]
        assert t_data["guard"]["breakeven_reached"] is True
        assert Decimal(str(t_data["guard"]["current_stop_loss"])) == Decimal("65020.00")


@pytest.mark.asyncio
async def test_circuit_breaker_status_and_emergency_stop_api():
    app = build_test_app()
    async with make_client(app) as client:
        status_resp = await client.get("/v1/automation/circuit-breakers/status")
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert "circuit_breaker_active" in status_data
        assert status_data["circuit_breaker_active"] is False

        # Trigger emergency stop
        stop_resp = await client.post(
            "/v1/automation/emergency-stop",
            json={"flatten_open_positions": True, "confirmation_token": "EMERGENCY_HALT"},
        )
        assert stop_resp.status_code == 200
        stop_data = stop_resp.json()
        assert stop_data["status"] == "HALTED"
        assert "timestamp" in stop_data

        # Status should now reflect circuit breaker active
        status_resp2 = await client.get("/v1/automation/circuit-breakers/status")
        assert status_resp2.status_code == 200
        assert status_resp2.json()["circuit_breaker_active"] is True
        assert status_resp2.json()["circuit_breaker_reason"] == "EMERGENCY_PANIC"
