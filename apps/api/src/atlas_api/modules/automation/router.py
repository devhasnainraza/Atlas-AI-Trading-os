"""Trading Automation API router and dependency injection (Spec 06 §2, §9)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, Path, Request

from atlas_api.modules.automation.domain.models import AutomationMandate, PositionGuardState
from atlas_api.modules.automation.schemas import (
    AutomationMandateResponse,
    CircuitBreakerResetRequest,
    CircuitBreakerStatusResponse,
    CreateMandateRequest,
    EmergencyStopRequest,
    EmergencyStopResponse,
    PositionGuardCreateRequest,
    PositionGuardResponse,
    TickEvaluationRequest,
    TickEvaluationResponse,
)
from atlas_api.modules.automation.service import AutomationService
from atlas_core.errors import InternalError, ValidationError

router = APIRouter(prefix="/automation", tags=["automation"])

STATE_KEY = "automation_context"


@dataclass(frozen=True)
class AutomationModuleContext:
    service: AutomationService


def get_automation_context(request: Request) -> AutomationModuleContext:
    context = getattr(request.app.state, STATE_KEY, None)
    if not isinstance(context, AutomationModuleContext):
        raise InternalError(
            internal_context={"detail": "automation module accessed before composition"}
        )
    return context


def get_automation_service(
    context: AutomationModuleContext = Depends(get_automation_context),
) -> AutomationService:
    return context.service


def _format_mandate(mandate: AutomationMandate) -> AutomationMandateResponse:
    return AutomationMandateResponse(
        id=mandate.id,
        user_id=mandate.user_id,
        account_id=mandate.account_id,
        mode=mandate.mode,
        allowed_symbols=list(mandate.allowed_symbols),
        max_capital_risk_pct=mandate.max_capital_risk_pct,
        daily_loss_limit_usd=mandate.daily_loss_limit_usd,
        max_open_positions=mandate.max_open_positions,
        news_protection=mandate.news_protection,
        session_restrictions=list(mandate.session_restrictions),
        is_active=mandate.is_active,
        expires_at=mandate.expires_at.isoformat(),
        created_at=mandate.created_at.isoformat(),
    )


def _format_guard(guard: PositionGuardState) -> PositionGuardResponse:
    return PositionGuardResponse(
        id=guard.id,
        position_id=guard.position_id,
        symbol=guard.symbol,
        side=guard.side,
        entry_price=guard.entry_price,
        current_stop_loss=guard.current_stop_loss,
        initial_stop_loss=guard.initial_stop_loss,
        tp1_price=guard.tp1_price,
        tp2_price=guard.tp2_price,
        tp3_price=guard.tp3_price,
        breakeven_reached=guard.breakeven_reached,
        tp1_filled=guard.tp1_filled,
        tp2_filled=guard.tp2_filled,
        trailing_active=guard.trailing_active,
        trailing_distance=guard.trailing_distance,
        highest_price_seen=guard.highest_price_seen,
        lowest_price_seen=guard.lowest_price_seen,
        status=guard.status,
        updated_at=guard.updated_at.isoformat(),
    )


@router.post("/mandates", response_model=AutomationMandateResponse)
async def create_mandate(
    body: CreateMandateRequest,
    request: Request,
    service: AutomationService = Depends(get_automation_service),
) -> AutomationMandateResponse:
    """Authorizes and activates an automation mandate for scoped execution."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    mandate = service.create_mandate(
        user_id=user_id,
        account_id=body.account_id,
        mode=body.mode,
        allowed_symbols=body.allowed_symbols,
        max_capital_risk_pct=body.max_capital_risk_pct,
        daily_loss_limit_usd=body.daily_loss_limit_usd,
        max_open_positions=body.max_open_positions,
        news_protection=body.news_protection,
        session_restrictions=body.session_restrictions,
        mandate_signature=body.mandate_signature,
        expires_in_days=body.expires_in_days,
    )
    return _format_mandate(mandate)


@router.get("/mandates", response_model=list[AutomationMandateResponse])
async def list_mandates(
    request: Request,
    service: AutomationService = Depends(get_automation_service),
) -> list[AutomationMandateResponse]:
    """Lists active and archived automation mandates for the user."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    mandates = service.get_mandates(user_id=user_id)
    return [_format_mandate(m) for m in mandates]


@router.post("/mandates/{mandate_id}/revoke", response_model=AutomationMandateResponse)
async def revoke_mandate(
    mandate_id: str = Path(..., description="Mandate identifier"),
    request: Request = ...,
    service: AutomationService = Depends(get_automation_service),
) -> AutomationMandateResponse:
    """Revokes an automation mandate, returning execution to Manual mode."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    mandate = service.revoke_mandate(mandate_id=mandate_id, user_id=user_id)
    return _format_mandate(mandate)


@router.post("/guards", response_model=PositionGuardResponse)
async def register_guard(
    body: PositionGuardCreateRequest,
    request: Request,
    service: AutomationService = Depends(get_automation_service),
) -> PositionGuardResponse:
    """Registers an active position guard for dynamic SL/TP and breakeven management."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    guard = service.register_position_guard(
        position_id=body.position_id,
        account_id=body.account_id,
        user_id=user_id,
        symbol=body.symbol,
        side=body.side,
        entry_price=body.entry_price,
        atr=body.atr,
        initial_stop_loss=body.initial_stop_loss,
        tp1_price=body.tp1_price,
        tp2_price=body.tp2_price,
        tp3_price=body.tp3_price,
        breakeven_offset=body.breakeven_offset,
        trailing_distance=body.trailing_distance,
    )
    return _format_guard(guard)


@router.get("/guards", response_model=list[PositionGuardResponse])
async def list_guards(
    request: Request,
    service: AutomationService = Depends(get_automation_service),
) -> list[PositionGuardResponse]:
    """Returns active position guards monitored by the automation daemon."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    guards = service.get_active_guards(user_id=user_id)
    return [_format_guard(g) for g in guards]


@router.post("/guards/{position_id}/tick", response_model=TickEvaluationResponse)
async def evaluate_tick(
    position_id: str = Path(..., description="Position reference identifier"),
    body: TickEvaluationRequest = ...,
    service: AutomationService = Depends(get_automation_service),
) -> TickEvaluationResponse:
    """Simulates/evaluates a live price tick against position stops and take-profits."""
    actions, guard = service.evaluate_tick(
        position_id=position_id,
        current_price=body.current_price,
    )
    return TickEvaluationResponse(
        position_id=position_id,
        current_price=body.current_price,
        actions_triggered=actions,
        guard=_format_guard(guard),
    )


@router.get("/circuit-breakers/status", response_model=CircuitBreakerStatusResponse)
async def get_circuit_breaker_status(
    request: Request,
    service: AutomationService = Depends(get_automation_service),
) -> CircuitBreakerStatusResponse:
    """Returns current automation health, daily drawdown, and circuit breaker status."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    status = service.get_status(user_id=user_id)
    return CircuitBreakerStatusResponse(
        user_id=status.user_id,
        mode=status.mode,
        active_mandates_count=status.active_mandates_count,
        circuit_breaker_active=status.circuit_breaker_active,
        circuit_breaker_reason=status.circuit_breaker_reason,
        daily_loss_usd=status.daily_loss_usd,
        daily_loss_limit_usd=status.daily_loss_limit_usd,
        protected_positions_count=status.protected_positions_count,
    )


@router.post("/circuit-breakers/reset", response_model=CircuitBreakerStatusResponse)
async def reset_circuit_breaker(
    body: CircuitBreakerResetRequest,
    request: Request,
    service: AutomationService = Depends(get_automation_service),
) -> CircuitBreakerStatusResponse:
    """Resets a tripped circuit breaker using authorized administrative override."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    service.reset_circuit_breaker(user_id=user_id, admin_token=body.admin_token)
    status = service.get_status(user_id=user_id)
    return CircuitBreakerStatusResponse(
        user_id=status.user_id,
        mode=status.mode,
        active_mandates_count=status.active_mandates_count,
        circuit_breaker_active=status.circuit_breaker_active,
        circuit_breaker_reason=status.circuit_breaker_reason,
        daily_loss_usd=status.daily_loss_usd,
        daily_loss_limit_usd=status.daily_loss_limit_usd,
        protected_positions_count=status.protected_positions_count,
    )


@router.post("/emergency-stop", response_model=EmergencyStopResponse)
async def trigger_emergency_stop(
    body: EmergencyStopRequest,
    request: Request,
    service: AutomationService = Depends(get_automation_service),
) -> EmergencyStopResponse:
    """Global emergency panic button: suspends mandates and cancels pending orders."""
    if body.confirmation_token != "EMERGENCY_HALT":
        raise ValidationError("Invalid emergency stop confirmation token. Expected 'EMERGENCY_HALT'")

    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    suspended, cancelled, flattened = service.trigger_emergency_stop(
        user_id=user_id,
        flatten=body.flatten_open_positions,
    )
    return EmergencyStopResponse(
        status="HALTED",
        mandates_suspended=suspended,
        orders_cancelled=cancelled,
        positions_flattened=flattened,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
