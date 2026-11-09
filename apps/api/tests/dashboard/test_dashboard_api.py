"""API contract tests for Dashboard & Analytics module (Spec 09 §9)."""

from decimal import Decimal
import pytest
from atlas_api.testing import build_test_app, make_client


@pytest.mark.asyncio
async def test_cockpit_overview_api():
    app = build_test_app()
    async with make_client(app) as client:
        resp = await client.get("/v1/dashboard/overview")
    assert resp.status_code == 200
    data = resp.json()

    assert "portfolio" in data
    assert Decimal(str(data["portfolio"]["balance_usd"])) == Decimal("50000.00")
    assert Decimal(str(data["portfolio"]["equity_usd"])) == Decimal("51250.00")
    assert Decimal(str(data["portfolio"]["daily_pnl_pct"])) == Decimal("2.50")

    assert len(data["open_positions"]) >= 2
    assert "symbol" in data["open_positions"][0]
    assert "unrealized_pnl" in data["open_positions"][0]

    assert len(data["agents"]) >= 5
    assert any(a["name"] == "MarketAgent" for a in data["agents"])
    assert any(a["name"] == "TechnicalAgent" for a in data["agents"])

    assert Decimal(str(data["consensus_confidence"])) > Decimal("50.00")
    assert data["circuit_breaker_status"] == "NORMAL"


@pytest.mark.asyncio
async def test_user_layout_api():
    app = build_test_app()
    async with make_client(app) as client:
        # Get default layout
        get_resp = await client.get("/v1/dashboard/layout")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["theme_preference"] == "DARK_OBSIDIAN"

        # Update layout
        put_resp = await client.put(
            "/v1/dashboard/layout",
            json={
                "layout_config": {"grid": "custom"},
                "theme_preference": "CYBER_NEON",
                "default_symbol": "ETH/USDT",
                "default_timeframe": "15m",
                "sound_effects_enabled": False,
            },
        )
        assert put_resp.status_code == 200
        put_data = put_resp.json()
        assert put_data["theme_preference"] == "CYBER_NEON"
        assert put_data["default_symbol"] == "ETH/USDT"
        assert put_data["sound_effects_enabled"] is False


@pytest.mark.asyncio
async def test_watchlists_and_scanner_presets_api():
    app = build_test_app()
    async with make_client(app) as client:
        # Create Watchlist
        wl_resp = await client.post(
            "/v1/dashboard/watchlists",
            json={"name": "DeFi Tokens", "symbols": ["AAVE/USDT", "UNI/USDT", "LINK/USDT"]},
        )
        assert wl_resp.status_code == 200
        wl_data = wl_resp.json()
        assert wl_data["name"] == "DeFi Tokens"
        assert len(wl_data["symbols"]) == 3
        wl_id = wl_data["id"]

        # List Watchlists
        list_resp = await client.get("/v1/dashboard/watchlists")
        assert list_resp.status_code == 200
        assert any(w["id"] == wl_id for w in list_resp.json())

        # Create Scanner Preset
        sp_resp = await client.post(
            "/v1/dashboard/scanner-presets",
            json={
                "name": "Volume Spike + FVG",
                "filters": {"min_rvol": 2.5, "fvg": True},
                "alert_on_match": True,
            },
        )
        assert sp_resp.status_code == 200
        sp_data = sp_resp.json()
        assert sp_data["name"] == "Volume Spike + FVG"
        assert sp_data["alert_on_match"] is True

        # List Scanner Presets
        list_sp_resp = await client.get("/v1/dashboard/scanner-presets")
        assert list_sp_resp.status_code == 200
        assert len(list_sp_resp.json()) >= 1
