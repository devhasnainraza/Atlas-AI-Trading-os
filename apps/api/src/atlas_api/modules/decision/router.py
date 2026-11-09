"""Decision engine module v1 API endpoints and module definition (Spec 05 §9)."""

from __future__ import annotations

from dataclasses import dataclass
from fastapi import APIRouter, Depends, Path, Request

from atlas_api.modules.decision.domain.models import TradeProposalRecord
from atlas_api.modules.decision.schemas import (
    DebateTranscriptResponse,
    EvaluateSetupRequest,
    ProposalApprovalRequest,
    ProposalRejectRequest,
    RiskRulesResponse,
    TradeProposalResponse,
)
from atlas_api.modules.decision.service import DecisionService
from atlas_api.modules.public import ModuleDef
from atlas_core.errors import InternalError

router = APIRouter(prefix="/decision", tags=["decision"])

STATE_KEY = "decision_context"


@dataclass(frozen=True)
class DecisionModuleContext:
    service: DecisionService


def get_decision_context(request: Request) -> DecisionModuleContext:
    context = getattr(request.app.state, STATE_KEY, None)
    if not isinstance(context, DecisionModuleContext):
        raise InternalError(
            internal_context={"detail": "decision module accessed before composition"}
        )
    return context


def get_decision_service(
    context: DecisionModuleContext = Depends(get_decision_context),
) -> DecisionService:
    return context.service


def _format_proposal(record: TradeProposalRecord) -> TradeProposalResponse:
    return TradeProposalResponse(
        id=record.id,
        symbol=record.symbol,
        direction=record.direction,
        confidence_score=record.confidence_score,
        entry_range_min=record.entry_range_min,
        entry_range_max=record.entry_range_max,
        stop_loss=record.stop_loss,
        take_profit_levels=list(record.take_profit_levels),
        risk_reward_ratio=record.risk_reward_ratio,
        risk_amount_usd=record.risk_amount_usd,
        calculated_position_size=record.calculated_position_size,
        proposal_hash=record.proposal_hash,
        evidence=list(record.evidence),
        risks=list(record.risks),
        alternative_scenarios=list(record.alternative_scenarios),
        debate_transcript=DebateTranscriptResponse(
            bull_arguments=list(record.debate_transcript.bull_arguments),
            bear_arguments=list(record.debate_transcript.bear_arguments),
            arbitrator_synthesis=record.debate_transcript.arbitrator_synthesis,
            identified_fallacies=list(record.debate_transcript.identified_fallacies),
        ),
        status=record.status,
        expires_at=record.expires_at.isoformat(),
        created_at=record.created_at.isoformat(),
    )


@router.post("/evaluate", response_model=TradeProposalResponse)
async def evaluate_setup(
    body: EvaluateSetupRequest,
    request: Request,
    service: DecisionService = Depends(get_decision_service),
) -> TradeProposalResponse:
    """Evaluates candidate setup through dialectic debate, Bayesian scoring, and risk gates."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    record = await service.evaluate_setup(
        user_id=user_id,
        symbol=body.symbol,
        direction=body.direction,
        timeframe=body.timeframe,
        entry_price=body.entry_price,
        stop_loss_price=body.stop_loss_price,
    )
    return _format_proposal(record)


@router.get("/proposals/pending", response_model=list[TradeProposalResponse])
async def get_pending_proposals(
    request: Request,
    service: DecisionService = Depends(get_decision_service),
) -> list[TradeProposalResponse]:
    """Returns unexpired trade proposals awaiting explicit human sign-off."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    records = await service.get_pending_proposals(user_id=user_id)
    return [_format_proposal(r) for r in records]


@router.post("/proposals/{proposal_id}/approve", response_model=TradeProposalResponse)
async def approve_proposal(
    proposal_id: str = Path(..., description="Unique proposal identifier"),
    body: ProposalApprovalRequest = ...,
    request: Request = ...,
    service: DecisionService = Depends(get_decision_service),
) -> TradeProposalResponse:
    """Submits human cryptographic approval to dispatch the trade."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    record = await service.approve_proposal(
        proposal_id=proposal_id,
        user_id=user_id,
        signature_token=body.signature_token,
    )
    return _format_proposal(record)


@router.post("/proposals/{proposal_id}/reject", response_model=TradeProposalResponse)
async def reject_proposal(
    proposal_id: str = Path(..., description="Unique proposal identifier"),
    body: ProposalRejectRequest = ...,
    request: Request = ...,
    service: DecisionService = Depends(get_decision_service),
) -> TradeProposalResponse:
    """Rejects proposal and records trader feedback for learning models."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    record = await service.reject_proposal(
        proposal_id=proposal_id,
        user_id=user_id,
        reason=body.rejection_reason,
    )
    return _format_proposal(record)


@router.get("/risk-rules", response_model=RiskRulesResponse)
async def get_risk_rules(
    request: Request,
    service: DecisionService = Depends(get_decision_service),
) -> RiskRulesResponse:
    """Returns active pre-trade risk governance rules."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    rule = service.get_risk_rules(user_id=user_id)
    return RiskRulesResponse(
        user_id=rule.user_id,
        max_risk_per_trade_pct=rule.max_risk_per_trade_pct,
        max_daily_loss_pct=rule.max_daily_loss_pct,
        max_drawdown_pct=rule.max_drawdown_pct,
        max_open_positions=rule.max_open_positions,
        max_leverage=rule.max_leverage,
        is_active=rule.is_active,
    )


def build_decision_module(env: str = "development") -> ModuleDef:
    """Composition root for the Spec 05 decision engine module."""
    service = DecisionService()
    context = DecisionModuleContext(service=service)

    return ModuleDef(
        name="decision",
        version="1.0.0",
        owner="decision-engine",
        router=router,
        app_state={STATE_KEY: context},
        health_probes={},
        subscriptions=(),
    )
