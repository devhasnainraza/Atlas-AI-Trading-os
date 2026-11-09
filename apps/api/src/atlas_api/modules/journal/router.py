"""Memory, Journal & Learning API router and endpoints (Spec 07 §2, §9)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, Path, Query, Request

from atlas_api.modules.journal.domain.models import (
    CoachingReportRecord,
    CognitiveBiasProfile,
    MemoryEmbeddingRecord,
    TradeJournalRecord,
)
from atlas_api.modules.journal.schemas import (
    AnnotateJournalEntryRequest,
    CoachingReportResponse,
    CognitiveBiasProfileResponse,
    CreateJournalEntryRequest,
    MemoryItemResponse,
    StoreMemoryRequest,
    TradeJournalResponse,
)
from atlas_api.modules.journal.service import JournalService
from atlas_core.errors import InternalError

router = APIRouter(prefix="/journal", tags=["journal"])

STATE_KEY = "journal_context"


@dataclass(frozen=True)
class JournalModuleContext:
    service: JournalService


def get_journal_context(request: Request) -> JournalModuleContext:
    context = getattr(request.app.state, STATE_KEY, None)
    if not isinstance(context, JournalModuleContext):
        raise InternalError(
            internal_context={"detail": "journal module accessed before composition"}
        )
    return context


def get_journal_service(
    context: JournalModuleContext = Depends(get_journal_context),
) -> JournalService:
    return context.service


def _format_journal_entry(record: TradeJournalRecord) -> TradeJournalResponse:
    return TradeJournalResponse(
        id=record.id,
        user_id=record.user_id,
        order_id=record.order_id,
        symbol=record.symbol,
        side=record.side,
        entry_price=record.entry_price,
        exit_price=record.exit_price,
        entry_time=record.entry_time.isoformat(),
        exit_time=record.exit_time.isoformat(),
        net_pnl=record.net_pnl,
        r_multiple=record.r_multiple,
        fees_usd=record.fees_usd,
        slippage_pips=record.slippage_pips,
        chart_image_url=record.chart_image_url,
        technical_indicators=record.technical_indicators,
        ai_post_mortem=record.ai_post_mortem,
        user_notes=record.user_notes,
        emotional_tags=list(record.emotional_tags),
        user_rating=record.user_rating,
        created_at=record.created_at.isoformat(),
    )


@router.post("/entries", response_model=TradeJournalResponse)
async def record_journal_entry(
    body: CreateJournalEntryRequest,
    request: Request,
    service: JournalService = Depends(get_journal_service),
) -> TradeJournalResponse:
    """Records an automated trade journal entry upon position close."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    record = service.record_closed_trade(
        user_id=user_id,
        order_id=body.order_id,
        account_id=body.account_id,
        symbol=body.symbol,
        side=body.side,
        entry_price=body.entry_price,
        exit_price=body.exit_price,
        stop_loss_price=body.stop_loss_price,
        entry_time=datetime.fromisoformat(body.entry_time),
        exit_time=datetime.fromisoformat(body.exit_time),
        net_pnl=body.net_pnl,
        fees_usd=body.fees_usd,
        slippage_pips=body.slippage_pips,
        technical_indicators=body.technical_indicators,
    )
    return _format_journal_entry(record)


@router.get("/entries", response_model=list[TradeJournalResponse])
async def list_journal_entries(
    request: Request,
    service: JournalService = Depends(get_journal_service),
) -> list[TradeJournalResponse]:
    """Returns chronological trade journal entries for the current user."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    records = service.get_journal_entries(user_id=user_id)
    return [_format_journal_entry(r) for r in records]


@router.get("/entries/{entry_id}", response_model=TradeJournalResponse)
async def get_journal_entry(
    entry_id: str = Path(..., description="Journal entry UUID"),
    request: Request = ...,
    service: JournalService = Depends(get_journal_service),
) -> TradeJournalResponse:
    """Returns a specific journal entry with chart snapshot and post-mortem."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    record = service.get_journal_entry(entry_id=entry_id, user_id=user_id)
    return _format_journal_entry(record)


@router.post("/entries/{entry_id}/annotate", response_model=TradeJournalResponse)
async def annotate_journal_entry(
    entry_id: str = Path(..., description="Journal entry UUID"),
    body: AnnotateJournalEntryRequest = ...,
    request: Request = ...,
    service: JournalService = Depends(get_journal_service),
) -> TradeJournalResponse:
    """Allows trader to tag emotional state and subjective reflections."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    record = service.annotate_entry(
        entry_id=entry_id,
        user_id=user_id,
        user_notes=body.user_notes,
        emotional_tags=body.emotional_tags,
        user_rating=body.user_rating,
    )
    return _format_journal_entry(record)


@router.get("/biases", response_model=CognitiveBiasProfileResponse)
async def get_bias_profile(
    request: Request,
    service: JournalService = Depends(get_journal_service),
) -> CognitiveBiasProfileResponse:
    """Returns real-time psychological and cognitive bias metrics."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    profile = service.get_bias_profile(user_id=user_id)
    return CognitiveBiasProfileResponse(
        user_id=profile.user_id,
        fomo_score=profile.fomo_score,
        revenge_trading_score=profile.revenge_trading_score,
        loss_aversion_score=profile.loss_aversion_score,
        overtrading_score=profile.overtrading_score,
        discipline_rating=profile.discipline_rating,
        top_mistake_triggers=list(profile.top_mistake_triggers),
        last_updated=profile.last_updated.isoformat(),
    )


@router.get("/coaching/latest", response_model=CoachingReportResponse)
async def get_latest_coaching_report(
    request: Request,
    service: JournalService = Depends(get_journal_service),
) -> CoachingReportResponse:
    """Returns the weekly AI coaching performance review and action plan."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    report = service.get_or_generate_coaching_report(user_id=user_id)
    return CoachingReportResponse(
        id=report.id,
        user_id=report.user_id,
        period_start=report.period_start,
        period_end=report.period_end,
        net_pnl=report.net_pnl,
        profit_factor=report.profit_factor,
        win_rate=report.win_rate,
        total_trades=report.total_trades,
        disciplined_actions=list(report.disciplined_actions),
        cognitive_bias_warnings=list(report.cognitive_bias_warnings),
        recommendations=list(report.recommendations),
        created_at=report.created_at.isoformat(),
    )


@router.post("/memory", response_model=MemoryItemResponse)
async def store_memory(
    body: StoreMemoryRequest,
    request: Request,
    service: JournalService = Depends(get_journal_service),
) -> MemoryItemResponse:
    """Stores episodic memory rule or preference for personalized AI agent retrieval."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    record = service.store_memory(
        user_id=user_id,
        scope=body.scope,
        memory_text=body.memory_text,
        importance_weight=body.importance_weight,
    )
    return MemoryItemResponse(
        id=record.id,
        user_id=record.user_id,
        scope=record.scope,
        memory_text=record.memory_text,
        importance_weight=record.importance_weight,
        created_at=record.created_at.isoformat(),
    )


@router.get("/memory", response_model=list[MemoryItemResponse])
async def list_memories(
    scope: str | None = Query(default=None, description="Optional scope filter"),
    request: Request = ...,
    service: JournalService = Depends(get_journal_service),
) -> list[MemoryItemResponse]:
    """Lists stored episodic memories for the user."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    records = service.list_memories(user_id=user_id, scope=scope)
    return [
        MemoryItemResponse(
            id=r.id,
            user_id=r.user_id,
            scope=r.scope,
            memory_text=r.memory_text,
            importance_weight=r.importance_weight,
            created_at=r.created_at.isoformat(),
        )
        for r in records
    ]


@router.get("/decision-chains")
async def list_decision_chains(
    request: Request,
    service: JournalService = Depends(get_journal_service),
) -> list[dict]:
    """Retrieves all stored 7-step decision chains per prompt.md Feature 7."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "default-user"
    records = service.get_decision_chains(user_id=user_id)
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "symbol": r.symbol,
            "action": r.action,
            "market_state": r.market_state,
            "agent_observations": r.agent_observations,
            "decision": r.decision,
            "risk_assessment": r.risk_assessment,
            "user_approval": r.user_approval,
            "execution": r.execution,
            "result": r.result,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]


@router.get("/decision-chains/{chain_id}")
async def get_decision_chain(
    chain_id: str = Path(description="ID of decision chain"),
    service: JournalService = Depends(get_journal_service),
) -> dict:
    """Retrieves a single 7-step decision chain by ID."""
    r = service.get_decision_chain(chain_id)
    return {
        "id": r.id,
        "user_id": r.user_id,
        "symbol": r.symbol,
        "action": r.action,
        "market_state": r.market_state,
        "agent_observations": r.agent_observations,
        "decision": r.decision,
        "risk_assessment": r.risk_assessment,
        "user_approval": r.user_approval,
        "execution": r.execution,
        "result": r.result,
        "created_at": r.created_at.isoformat(),
    }

