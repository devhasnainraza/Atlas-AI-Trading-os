"""Unit tests for DashboardService and cockpit aggregation (Spec 09 §2, §5)."""

from decimal import Decimal
import pytest
from atlas_api.modules.dashboard.service import DashboardService
from atlas_core.errors import NotFoundError


def test_dashboard_user_layout_management():
    service = DashboardService()
    layout = service.get_user_layout("user-cockpit-1")
    assert layout.user_id == "user-cockpit-1"
    assert layout.theme_preference == "DARK_OBSIDIAN"
    assert layout.default_symbol == "BTC/USDT"

    updated = service.update_user_layout(
        user_id="user-cockpit-1",
        layout_config={"widgets": [{"id": "chart", "w": 12, "h": 8}]},
        theme_preference="MIDNIGHT_BLUE",
        default_symbol="EUR/USD",
        default_timeframe="4h",
    )
    assert updated.theme_preference == "MIDNIGHT_BLUE"
    assert updated.default_symbol == "EUR/USD"
    assert updated.default_timeframe == "4h"
    assert len(updated.layout_config["widgets"]) == 1


def test_dashboard_watchlists():
    service = DashboardService()
    # Default watchlist auto-created if none exists
    watchlists = service.get_watchlists("user-cockpit-2")
    assert len(watchlists) == 1
    assert watchlists[0].name == "Core Markets"
    assert "BTC/USDT" in watchlists[0].symbols

    # Create new custom watchlist
    custom = service.create_watchlist(
        user_id="user-cockpit-2",
        name="Forex Crosses",
        symbols=["EUR/GBP", "AUD/JPY", "NZD/USD"],
    )
    assert custom.name == "Forex Crosses"
    assert len(custom.symbols) == 3

    service.delete_watchlist(custom.id, "user-cockpit-2")
    with pytest.raises(NotFoundError):
        service.delete_watchlist(custom.id, "user-cockpit-2")


def test_cockpit_overview_aggregation():
    service = DashboardService()
    overview = service.get_cockpit_overview("trader-user-01")

    assert overview.user_id == "trader-user-01"
    assert overview.portfolio["equity_usd"] == Decimal("51250.00")
    assert overview.portfolio["daily_pnl_pct"] == Decimal("2.50")
    assert len(overview.open_positions) == 2
    assert overview.consensus_confidence == Decimal("81.50")
    assert overview.circuit_breaker_status == "NORMAL"
    assert len(overview.agents) >= 5
    assert any(a.name == "MarketAgent" for a in overview.agents)
    assert any(a.name == "RiskAgent" for a in overview.agents)
