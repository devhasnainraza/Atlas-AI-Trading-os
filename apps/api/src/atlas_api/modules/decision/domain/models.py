"""Domain models for the Decision Engine and Risk Management (Spec 05 §6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
import uuid


@dataclass(frozen=True)
class DebateArgument:
    role: str  # BULL_ADVOCATE | BEAR_ADVOCATE | SYNTHESIS_ARBITRATOR
    thesis: str
    key_points: tuple[str, ...]
    invalidation_level: str | None = None


@dataclass(frozen=True)
class DebateTranscript:
    bull_arguments: tuple[str, ...]
    bear_arguments: tuple[str, ...]
    arbitrator_synthesis: str
    identified_fallacies: tuple[str, ...] = ()


@dataclass
class TradeProposalRecord:
    id: str
    user_id: str
    symbol: str
    direction: str  # LONG | SHORT
    confidence_score: Decimal
    entry_range_min: Decimal
    entry_range_max: Decimal
    stop_loss: Decimal
    take_profit_levels: tuple[Decimal, ...]
    risk_reward_ratio: Decimal
    risk_amount_usd: Decimal
    calculated_position_size: Decimal
    proposal_hash: str
    evidence: tuple[str, ...]
    risks: tuple[str, ...]
    alternative_scenarios: tuple[str, ...]
    debate_transcript: DebateTranscript
    status: str  # PENDING_APPROVAL | APPROVED | REJECTED | EXPIRED | EXECUTED
    expires_at: datetime
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime | None = None


@dataclass(frozen=True)
class DecisionRiskRule:
    user_id: str
    max_risk_per_trade_pct: Decimal = Decimal("1.50")
    max_daily_loss_pct: Decimal = Decimal("3.00")
    max_drawdown_pct: Decimal = Decimal("6.00")
    max_open_positions: int = 3
    max_leverage: Decimal = Decimal("10.00")
    max_correlation_threshold: Decimal = Decimal("0.70")
    macro_embargo_minutes: int = 30
    is_active: bool = True
