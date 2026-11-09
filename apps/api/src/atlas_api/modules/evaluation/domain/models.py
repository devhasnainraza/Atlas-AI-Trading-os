"""Domain models for Historical Scenario Evaluation (prompt.md Feature 8)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class EvaluationScenario:
    """A historical market scenario used to stress-test the multi-agent system."""

    id: str
    name: str
    description: str
    market_regime: str  # "FLASH_CRASH" | "HIGH_VOL_CPI" | "RANGE_BOUND_CHOP" | "LIQUIDATION_CASCADE"
    historical_date: str
    primary_symbol: str
    volatility_index: str
    ground_truth_optimal_action: str  # "VETO_LONG" | "WAIT_PULLBACK" | "SCALP_FADE" | "DEFENSIVE_FLAT"


@dataclass
class ScenarioEvaluationResult:
    """Comprehensive test metrics for a historical market scenario per prompt.md:

    - Decision accuracy
    - Risk violations
    - False signals
    - Execution errors
    - Latency
    - Cost
    - Agent disagreement
    """

    id: str
    scenario_id: str
    scenario_name: str
    decision_accuracy_pct: Decimal  # e.g. 87.50%
    risk_violations_count: int  # Must be 0 for constitutional safety
    false_signals_count: int  # Filtered by Critic Agent
    execution_errors_count: int  # Venue/order submission failures
    latency_ms_p95: Decimal  # Pipeline p95 latency
    cost_usd: Decimal  # Simulated fees & slippage
    agent_disagreement_score: Decimal  # 0.00 (full consensus) to 1.00 (polar debate)
    verdict: str  # "EXEMPLARY" | "COMPLIANT" | "FAILED"
    notes: list[str]
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
