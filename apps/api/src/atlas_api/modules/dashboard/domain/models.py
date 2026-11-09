"""Domain models for Dashboard & Analytics (Spec 09 §2, §5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
import uuid


@dataclass
class DashboardUserLayout:
    id: str
    user_id: str
    layout_config: dict[str, Any]
    theme_preference: str = "DARK_OBSIDIAN"  # DARK_OBSIDIAN | MIDNIGHT_BLUE | CYBER_NEON
    default_symbol: str = "BTC/USDT"
    default_timeframe: str = "1h"
    sound_effects_enabled: bool = True
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DashboardWatchlist:
    id: str
    user_id: str
    name: str
    symbols: tuple[str, ...]
    sort_order: int = 0
    is_default: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DashboardScannerPreset:
    id: str
    user_id: str
    name: str
    filters: dict[str, Any]
    alert_on_match: bool = False
    is_public: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class AgentTelemetryStatus:
    name: str
    role: str
    state: str  # IDLE | THINKING | DEBATING | WAITING_APPROVAL
    current_task: str
    confidence_score: Decimal


@dataclass(frozen=True)
class CockpitOverview:
    user_id: str
    portfolio: dict[str, Any]
    open_positions: list[dict[str, Any]]
    agents: list[AgentTelemetryStatus]
    consensus_confidence: Decimal
    circuit_breaker_status: str  # NORMAL | WARNING | TRIPPED
    active_mandates_count: int
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
