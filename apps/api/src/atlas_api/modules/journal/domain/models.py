"""Domain models for Memory, Journal & Learning per prompt.md Feature 7."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
import uuid


@dataclass
class DecisionChainJournalRecord:
    """Stores the complete 7-step decision trail specified in prompt.md:

    1. Market state
    2. Agent observations
    3. Decision
    4. Risk assessment
    5. User approval
    6. Execution
    7. Result
    """

    id: str
    user_id: str
    symbol: str
    action: str  # BUY | SELL
    market_state: dict[str, Any]
    agent_observations: dict[str, Any]
    decision: dict[str, Any]
    risk_assessment: dict[str, Any]
    user_approval: dict[str, Any]
    execution: dict[str, Any]
    result: dict[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TradeJournalRecord:
    id: str
    user_id: str
    order_id: str
    account_id: str
    symbol: str
    side: str  # LONG | SHORT
    entry_price: Decimal
    exit_price: Decimal
    entry_time: datetime
    exit_time: datetime
    net_pnl: Decimal
    r_multiple: Decimal
    fees_usd: Decimal
    slippage_pips: Decimal
    chart_image_url: str
    technical_indicators: dict[str, Any]
    ai_post_mortem: str
    user_notes: str = ""
    emotional_tags: tuple[str, ...] = ()
    user_rating: int | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class CognitiveBiasProfile:
    id: str
    user_id: str
    fomo_score: Decimal  # 0.00 to 1.00
    revenge_trading_score: Decimal  # 0.00 to 1.00
    loss_aversion_score: Decimal  # 0.00 to 1.00
    overtrading_score: Decimal  # 0.00 to 1.00
    discipline_rating: Decimal  # 0.00 to 100.00
    top_mistake_triggers: tuple[str, ...]
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class CoachingReportRecord:
    id: str
    user_id: str
    period_start: str
    period_end: str
    net_pnl: Decimal
    profit_factor: Decimal
    win_rate: Decimal
    total_trades: int
    disciplined_actions: tuple[str, ...]
    cognitive_bias_warnings: tuple[str, ...]
    recommendations: tuple[str, ...]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class MemoryEmbeddingRecord:
    id: str
    user_id: str
    scope: str  # STRATEGY | BEHAVIOR | GOALS | RULES | LESSONS
    memory_text: str
    importance_weight: Decimal
    last_retrieved_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
