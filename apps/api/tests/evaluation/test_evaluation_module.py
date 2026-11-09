"""Tests for Historical Scenario Evaluation framework (prompt.md Feature 8)."""

from decimal import Decimal
import pytest
from atlas_api.modules.evaluation.service import EvaluationService


def test_scenario_initialization():
    service = EvaluationService()
    scenarios = service.list_scenarios()
    assert len(scenarios) >= 4

    regimes = {s.market_regime for s in scenarios}
    assert "FLASH_CRASH" in regimes
    assert "HIGH_VOL_CPI" in regimes
    assert "RANGE_BOUND_CHOP" in regimes
    assert "LIQUIDATION_CASCADE" in regimes


def test_evaluation_run_computes_all_seven_metrics():
    service = EvaluationService()
    results = service.run_evaluation()

    assert len(results) >= 4
    for r in results:
        # 1. Decision accuracy
        assert r.decision_accuracy_pct > Decimal("80.00")
        # 2. Risk violations
        assert r.risk_violations_count == 0  # Zero tolerance for risk breaches
        # 3. False signals
        assert r.false_signals_count >= 0
        # 4. Execution errors
        assert r.execution_errors_count == 0
        # 5. Latency
        assert r.latency_ms_p95 < Decimal("100.00")
        # 6. Cost
        assert r.cost_usd >= Decimal("0.00")
        # 7. Agent disagreement
        assert Decimal("0.00") <= r.agent_disagreement_score <= Decimal("1.00")
        assert r.verdict in ("EXEMPLARY", "COMPLIANT")
