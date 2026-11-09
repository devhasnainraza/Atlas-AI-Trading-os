"""Dashboard & Analytics API router and endpoints (Spec 09 §2, §9)."""

from __future__ import annotations

from dataclasses import dataclass
from fastapi import APIRouter, Depends, Path, Request

from atlas_api.modules.dashboard.domain.models import (
    DashboardScannerPreset,
    DashboardUserLayout,
    DashboardWatchlist,
)
from atlas_api.modules.dashboard.schemas import (
    AgentTelemetryResponse,
    CockpitOverviewResponse,
    CreateWatchlistRequest,
    PortfolioTelemetryResponse,
    ScannerPresetRequest,
    ScannerPresetResponse,
    UserLayoutRequest,
    UserLayoutResponse,
    WatchlistResponse,
)
from atlas_api.modules.dashboard.service import DashboardService
from atlas_core.errors import InternalError

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

STATE_KEY = "dashboard_context"


@dataclass(frozen=True)
class DashboardModuleContext:
    service: DashboardService


def get_dashboard_context(request: Request) -> DashboardModuleContext:
    context = getattr(request.app.state, STATE_KEY, None)
    if not isinstance(context, DashboardModuleContext):
        raise InternalError(
            internal_context={"detail": "dashboard module accessed before composition"}
        )
    return context


def get_dashboard_service(
    context: DashboardModuleContext = Depends(get_dashboard_context),
) -> DashboardService:
    return context.service


def _format_layout(layout: DashboardUserLayout) -> UserLayoutResponse:
    return UserLayoutResponse(
        user_id=layout.user_id,
        layout_config=layout.layout_config,
        theme_preference=layout.theme_preference,
        default_symbol=layout.default_symbol,
        default_timeframe=layout.default_timeframe,
        sound_effects_enabled=layout.sound_effects_enabled,
        updated_at=layout.updated_at.isoformat(),
    )


def _format_watchlist(wl: DashboardWatchlist) -> WatchlistResponse:
    return WatchlistResponse(
        id=wl.id,
        user_id=wl.user_id,
        name=wl.name,
        symbols=list(wl.symbols),
        sort_order=wl.sort_order,
        is_default=wl.is_default,
        created_at=wl.created_at.isoformat(),
    )


def _format_preset(p: DashboardScannerPreset) -> ScannerPresetResponse:
    return ScannerPresetResponse(
        id=p.id,
        user_id=p.user_id,
        name=p.name,
        filters=p.filters,
        alert_on_match=p.alert_on_match,
        is_public=p.is_public,
        created_at=p.created_at.isoformat(),
    )


@router.get("/overview", response_model=CockpitOverviewResponse)
async def get_cockpit_overview(
    request: Request,
    service: DashboardService = Depends(get_dashboard_service),
) -> CockpitOverviewResponse:
    """Returns aggregated real-time cockpit telemetry: portfolio, active agents, positions, risk."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    overview = service.get_cockpit_overview(user_id=user_id)
    return CockpitOverviewResponse(
        user_id=overview.user_id,
        portfolio=PortfolioTelemetryResponse(**overview.portfolio),
        open_positions=overview.open_positions,
        agents=[
            AgentTelemetryResponse(
                name=a.name,
                role=a.role,
                state=a.state,
                current_task=a.current_task,
                confidence_score=a.confidence_score,
            )
            for a in overview.agents
        ],
        consensus_confidence=overview.consensus_confidence,
        circuit_breaker_status=overview.circuit_breaker_status,
        active_mandates_count=overview.active_mandates_count,
        generated_at=overview.generated_at.isoformat(),
    )


@router.get("/layout", response_model=UserLayoutResponse)
async def get_layout(
    request: Request,
    service: DashboardService = Depends(get_dashboard_service),
) -> UserLayoutResponse:
    """Returns persistent cockpit widget layout and theme preferences."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    layout = service.get_user_layout(user_id=user_id)
    return _format_layout(layout)


@router.put("/layout", response_model=UserLayoutResponse)
async def update_layout(
    body: UserLayoutRequest,
    request: Request,
    service: DashboardService = Depends(get_dashboard_service),
) -> UserLayoutResponse:
    """Saves user cockpit widget grid arrangement, active theme, and default symbols."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    layout = service.update_user_layout(
        user_id=user_id,
        layout_config=body.layout_config,
        theme_preference=body.theme_preference,
        default_symbol=body.default_symbol,
        default_timeframe=body.default_timeframe,
        sound_effects_enabled=body.sound_effects_enabled,
    )
    return _format_layout(layout)


@router.get("/watchlists", response_model=list[WatchlistResponse])
async def list_watchlists(
    request: Request,
    service: DashboardService = Depends(get_dashboard_service),
) -> list[WatchlistResponse]:
    """Returns curated symbol watchlists for rapid asset monitoring."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    watchlists = service.get_watchlists(user_id=user_id)
    return [_format_watchlist(w) for w in watchlists]


@router.post("/watchlists", response_model=WatchlistResponse)
async def create_watchlist(
    body: CreateWatchlistRequest,
    request: Request,
    service: DashboardService = Depends(get_dashboard_service),
) -> WatchlistResponse:
    """Creates a new symbol watchlist."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    watchlist = service.create_watchlist(
        user_id=user_id,
        name=body.name,
        symbols=body.symbols,
        is_default=body.is_default,
    )
    return _format_watchlist(watchlist)


@router.delete("/watchlists/{watchlist_id}")
async def delete_watchlist(
    watchlist_id: str = Path(..., description="Watchlist UUID"),
    request: Request = ...,
    service: DashboardService = Depends(get_dashboard_service),
) -> dict[str, str]:
    """Deletes a custom watchlist."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    service.delete_watchlist(watchlist_id=watchlist_id, user_id=user_id)
    return {"status": "DELETED", "id": watchlist_id}


@router.get("/scanner-presets", response_model=list[ScannerPresetResponse])
async def list_scanner_presets(
    request: Request,
    service: DashboardService = Depends(get_dashboard_service),
) -> list[ScannerPresetResponse]:
    """Returns technical scanner filter presets."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    presets = service.get_scanner_presets(user_id=user_id)
    return [_format_preset(p) for p in presets]


@router.post("/scanner-presets", response_model=ScannerPresetResponse)
async def create_scanner_preset(
    body: ScannerPresetRequest,
    request: Request,
    service: DashboardService = Depends(get_dashboard_service),
) -> ScannerPresetResponse:
    """Saves a technical scanner filter preset."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    preset = service.create_scanner_preset(
        user_id=user_id,
        name=body.name,
        filters=body.filters,
        alert_on_match=body.alert_on_match,
        is_public=body.is_public,
    )
    return _format_preset(preset)
