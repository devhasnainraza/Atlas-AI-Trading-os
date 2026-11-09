"""Evaluation API router and endpoints (prompt.md Feature 8)."""

from __future__ import annotations

from dataclasses import dataclass
from fastapi import APIRouter, Depends, Query, Request

from atlas_api.modules.evaluation.domain.models import (
    EvaluationScenario,
    ScenarioEvaluationResult,
)
from atlas_api.modules.evaluation.service import EvaluationService
from atlas_core.errors import InternalError

router = APIRouter(prefix="/evaluation", tags=["evaluation"])

STATE_KEY = "evaluation_context"


@dataclass(frozen=True)
class EvaluationModuleContext:
    service: EvaluationService


def get_evaluation_context(request: Request) -> EvaluationModuleContext:
    context = getattr(request.app.state, STATE_KEY, None)
    if not isinstance(context, EvaluationModuleContext):
        raise InternalError(
            internal_context={"detail": "evaluation module accessed before composition"}
        )
    return context


def get_evaluation_service(
    context: EvaluationModuleContext = Depends(get_evaluation_context),
) -> EvaluationService:
    return context.service


@router.get("/scenarios")
async def list_scenarios(
    service: EvaluationService = Depends(get_evaluation_service),
) -> list[dict]:
    """Lists historical test scenarios for evaluation."""
    scenarios = service.list_scenarios()
    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "market_regime": s.market_regime,
            "historical_date": s.historical_date,
            "primary_symbol": s.primary_symbol,
            "volatility_index": s.volatility_index,
            "ground_truth_optimal_action": s.ground_truth_optimal_action,
        }
        for s in scenarios
    ]


@router.post("/run")
async def run_evaluation(
    scenario_id: str | None = Query(default=None, description="Optional single scenario ID to run"),
    service: EvaluationService = Depends(get_evaluation_service),
) -> list[dict]:
    """Runs evaluation across historical market scenarios and returns all 7 prompt.md metrics:

    - Decision accuracy
    - Risk violations
    - False signals
    - Execution errors
    - Latency
    - Cost
    - Agent disagreement
    """
    results = service.run_evaluation(scenario_id=scenario_id)
    return [
        {
            "id": r.id,
            "scenario_id": r.scenario_id,
            "scenario_name": r.scenario_name,
            "decision_accuracy_pct": str(r.decision_accuracy_pct),
            "risk_violations_count": r.risk_violations_count,
            "false_signals_count": r.false_signals_count,
            "execution_errors_count": r.execution_errors_count,
            "latency_ms_p95": str(r.latency_ms_p95),
            "cost_usd": str(r.cost_usd),
            "agent_disagreement_score": str(r.agent_disagreement_score),
            "verdict": r.verdict,
            "notes": r.notes,
            "evaluated_at": r.evaluated_at.isoformat(),
        }
        for r in results
    ]


@router.get("/results")
async def get_results(
    service: EvaluationService = Depends(get_evaluation_service),
) -> list[dict]:
    """Returns latest evaluation metrics across historical scenarios."""
    results = service.get_latest_results()
    return [
        {
            "id": r.id,
            "scenario_id": r.scenario_id,
            "scenario_name": r.scenario_name,
            "decision_accuracy_pct": str(r.decision_accuracy_pct),
            "risk_violations_count": r.risk_violations_count,
            "false_signals_count": r.false_signals_count,
            "execution_errors_count": r.execution_errors_count,
            "latency_ms_p95": str(r.latency_ms_p95),
            "cost_usd": str(r.cost_usd),
            "agent_disagreement_score": str(r.agent_disagreement_score),
            "verdict": r.verdict,
            "notes": r.notes,
            "evaluated_at": r.evaluated_at.isoformat(),
        }
        for r in results
    ]
