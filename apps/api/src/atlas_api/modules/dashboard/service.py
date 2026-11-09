"""Service implementation for Dashboard & Analytics (Spec 09 §2, §5)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
import uuid

from atlas_api.modules.dashboard.domain.models import (
    AgentTelemetryStatus,
    CockpitOverview,
    DashboardScannerPreset,
    DashboardUserLayout,
    DashboardWatchlist,
)
from atlas_core.errors import NotFoundError


class DashboardService:
    """Orchestrates cockpit aggregation, widget layouts, watchlists, and scanner presets."""

    def __init__(self) -> None:
        self._layouts: dict[str, DashboardUserLayout] = {}
        self._watchlists: dict[str, DashboardWatchlist] = {}
        self._presets: dict[str, DashboardScannerPreset] = {}

    def get_user_layout(self, user_id: str) -> DashboardUserLayout:
        if user_id not in self._layouts:
            self._layouts[user_id] = DashboardUserLayout(
                id=str(uuid.uuid4()),
                user_id=user_id,
                layout_config={
                    "widgets": [
                        {"id": "portfolio", "col": 0, "row": 0, "w": 4, "h": 2},
                        {"id": "chart", "col": 4, "row": 0, "w": 8, "h": 6},
                        {"id": "agent_stream", "col": 0, "row": 2, "w": 4, "h": 4},
                        {"id": "positions", "col": 0, "row": 6, "w": 8, "h": 3},
                        {"id": "risk_meter", "col": 8, "row": 6, "w": 4, "h": 3},
                    ]
                },
                theme_preference="DARK_OBSIDIAN",
                default_symbol="BTC/USDT",
                default_timeframe="1h",
                sound_effects_enabled=True,
                updated_at=datetime.now(timezone.utc),
            )
        return self._layouts[user_id]

    def update_user_layout(
        self,
        user_id: str,
        layout_config: dict[str, Any],
        theme_preference: str = "DARK_OBSIDIAN",
        default_symbol: str = "BTC/USDT",
        default_timeframe: str = "1h",
        sound_effects_enabled: bool = True,
    ) -> DashboardUserLayout:
        layout = self.get_user_layout(user_id)
        layout.layout_config = layout_config
        layout.theme_preference = theme_preference.upper()
        layout.default_symbol = default_symbol.upper()
        layout.default_timeframe = default_timeframe
        layout.sound_effects_enabled = sound_effects_enabled
        layout.updated_at = datetime.now(timezone.utc)
        return layout

    def create_watchlist(
        self,
        user_id: str,
        name: str,
        symbols: list[str],
        is_default: bool = False,
    ) -> DashboardWatchlist:
        wl_id = str(uuid.uuid4())
        wl = DashboardWatchlist(
            id=wl_id,
            user_id=user_id,
            name=name,
            symbols=tuple(s.upper() for s in symbols),
            sort_order=len(self._watchlists),
            is_default=is_default,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self._watchlists[wl_id] = wl
        return wl

    def get_watchlists(self, user_id: str) -> list[DashboardWatchlist]:
        user_wls = [w for w in self._watchlists.values() if w.user_id == user_id]
        if not user_wls:
            # Seed standard default watchlist
            default_wl = self.create_watchlist(
                user_id=user_id,
                name="Core Markets",
                symbols=["BTC/USDT", "ETH/USDT", "SOL/USDT", "EUR/USD", "GBP/USD", "XAU/USD"],
                is_default=True,
            )
            return [default_wl]
        return sorted(user_wls, key=lambda w: w.sort_order)

    def delete_watchlist(self, watchlist_id: str, user_id: str) -> None:
        wl = self._watchlists.get(watchlist_id)
        if not wl or wl.user_id != user_id:
            raise NotFoundError(f"Watchlist '{watchlist_id}' not found")
        del self._watchlists[watchlist_id]

    def create_scanner_preset(
        self,
        user_id: str,
        name: str,
        filters: dict[str, Any],
        alert_on_match: bool = False,
        is_public: bool = False,
    ) -> DashboardScannerPreset:
        preset_id = str(uuid.uuid4())
        preset = DashboardScannerPreset(
            id=preset_id,
            user_id=user_id,
            name=name,
            filters=filters,
            alert_on_match=alert_on_match,
            is_public=is_public,
            created_at=datetime.now(timezone.utc),
        )
        self._presets[preset_id] = preset
        return preset

    def get_scanner_presets(self, user_id: str) -> list[DashboardScannerPreset]:
        presets = [p for p in self._presets.values() if p.user_id == user_id or p.is_public]
        if not presets:
            # Seed standard presets
            p1 = self.create_scanner_preset(
                user_id=user_id,
                name="High Volatility Breakout",
                filters={"min_rvol": 2.0, "atr_pct": 1.5, "timeframe": "1h"},
                is_public=True,
            )
            p2 = self.create_scanner_preset(
                user_id=user_id,
                name="RSI Divergence + Order Block",
                filters={"rsi_min": 30, "rsi_max": 70, "structure": "FVG"},
                is_public=True,
            )
            return [p1, p2]
        return presets

    def get_cockpit_overview(self, user_id: str) -> CockpitOverview:
        portfolio = {
            "balance_usd": Decimal("50000.00"),
            "equity_usd": Decimal("51250.00"),
            "free_margin_usd": Decimal("44500.00"),
            "used_margin_usd": Decimal("6750.00"),
            "daily_pnl_usd": Decimal("1250.00"),
            "daily_pnl_pct": Decimal("2.50"),
            "margin_level_pct": Decimal("759.25"),
        }

        open_positions = [
            {
                "id": "pos-btc-01",
                "symbol": "BTC/USDT",
                "side": "LONG",
                "entry_price": "65200.00",
                "current_price": "67150.00",
                "stop_loss": "65250.00",  # Trailed to breakeven + buffer
                "take_profit": "68500.00",
                "unrealized_pnl": "975.00",
                "unrealized_r": "2.40",
            },
            {
                "id": "pos-eur-01",
                "symbol": "EUR/USD",
                "side": "SHORT",
                "entry_price": "1.0850",
                "current_price": "1.0815",
                "stop_loss": "1.0860",
                "take_profit": "1.0770",
                "unrealized_pnl": "275.00",
                "unrealized_r": "1.75",
            },
        ]

        agents = [
            AgentTelemetryStatus("MarketAgent", "Intelligence", "THINKING", "Scanning Order Book Imbalances", Decimal("84.50")),
            AgentTelemetryStatus("TechnicalAgent", "Analysis", "THINKING", "ICT Fair Value Gap identification", Decimal("79.00")),
            AgentTelemetryStatus("RiskAgent", "Governance", "IDLE", "Pre-trade risk boundaries checked", Decimal("98.00")),
            AgentTelemetryStatus("ManagerAgent", "Orchestration", "DEBATING", "Arbitrating Bull/Bear debate setup", Decimal("81.50")),
            AgentTelemetryStatus("ExecutionAgent", "Order Routing", "WAITING_APPROVAL", "Standby for human cryptographic sign-off", Decimal("95.00")),
        ]

        return CockpitOverview(
            user_id=user_id,
            portfolio=portfolio,
            open_positions=open_positions,
            agents=agents,
            consensus_confidence=Decimal("81.50"),
            circuit_breaker_status="NORMAL",
            active_mandates_count=1,
            generated_at=datetime.now(timezone.utc),
        )
