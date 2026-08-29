"""Trading module v1 API + module definition.

The module owns its own composition root: :func:`build_trading_module` creates the venue
registry, the paper book store, and the settings once, and hands them to the app as module
state. Routes read them back off ``request.app.state``, so two composed apps never share one
paper book. Nothing trading-specific leaks into ``PlatformRuntime``, so the platform foundation
stays unaware that trading exists (Constitution X).

Endpoints in this slice are all reads plus the paper reset — the surfaces that need no
persistence. Order intent, confirmation, and submission arrive with US4 behind the same
composition root.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, Depends, Path, Request

from atlas_api.deps import get_runtime
from atlas_api.modules.public import EventSubscriptionDef, ModuleDef
from atlas_api.modules.trading import events
from atlas_api.modules.trading.schemas import (
    LiveTradingStatusResponse,
    PaperResetRequest,
    PaperResetResponse,
    RiskRulesResponse,
    VenueListResponse,
)
from atlas_api.modules.trading.service import (
    LiveTradingStatusService,
    PaperAccountService,
    RiskCatalogService,
    VenueCatalogService,
)
from atlas_api.modules.trading.settings import TradingSettings
from atlas_api.modules.trading.venues import PaperBookStore, register_builtin_venues
from atlas_api.runtime import PlatformRuntime
from atlas_core.errors import InternalError
from atlas_venues.registry import VenueRegistry

router = APIRouter(prefix="/trading", tags=["trading"])

#: ``app.state`` key holding this module's :class:`TradingModuleContext`.
STATE_KEY = "trading_context"


@dataclass(frozen=True)
class TradingModuleContext:
    """Per-build trading state. One instance per composed app."""

    settings: TradingSettings
    registry: VenueRegistry
    books: PaperBookStore


def get_trading_context(request: Request) -> TradingModuleContext:
    """The module's composition root, read off the app it belongs to.

    Raises rather than lazily building one: a route reachable before the module was composed
    means the app was assembled wrong, and silently constructing a second registry would give
    that route a different set of venues than the rest of the app sees.
    """
    context = getattr(request.app.state, STATE_KEY, None)
    if not isinstance(context, TradingModuleContext):  # pragma: no cover - composition guard
        raise InternalError(
            internal_context={"detail": "trading module accessed before composition"}
        )
    return context


def get_venue_catalog(
    context: TradingModuleContext = Depends(get_trading_context),
    runtime: PlatformRuntime = Depends(get_runtime),
) -> VenueCatalogService:
    return VenueCatalogService(context.registry, runtime.flags)


def get_risk_catalog() -> RiskCatalogService:
    return RiskCatalogService()


def get_live_status(
    context: TradingModuleContext = Depends(get_trading_context),
    runtime: PlatformRuntime = Depends(get_runtime),
) -> LiveTradingStatusService:
    return LiveTradingStatusService(context.settings, runtime.flags)


def get_paper_accounts(
    context: TradingModuleContext = Depends(get_trading_context),
    runtime: PlatformRuntime = Depends(get_runtime),
) -> PaperAccountService:
    return PaperAccountService(context.books, context.settings, runtime.outbox, runtime.bus)


@router.get("/venues", response_model=VenueListResponse)
async def list_venues(
    catalog: VenueCatalogService = Depends(get_venue_catalog),
) -> VenueListResponse:
    """Every venue this build ships, with its declared capabilities and flag state (FR-001)."""
    return catalog.list_venues()


@router.get("/risk/rules", response_model=RiskRulesResponse)
async def list_risk_rules(
    catalog: RiskCatalogService = Depends(get_risk_catalog),
) -> RiskRulesResponse:
    """Every rule the pre-trade gate evaluates, in order — published up front (FR-035)."""
    return catalog.rules()


@router.get("/live-status", response_model=LiveTradingStatusResponse)
async def live_trading_status(
    service: LiveTradingStatusService = Depends(get_live_status),
) -> LiveTradingStatusResponse:
    """Whether real-money orders can leave this deployment, and why not if they cannot."""
    return service.status()


@router.post("/paper/{venue_account_ref}/reset", response_model=PaperResetResponse)
async def reset_paper_account(
    body: PaperResetRequest,
    venue_account_ref: str = Path(min_length=1, max_length=128),
    service: PaperAccountService = Depends(get_paper_accounts),
    catalog: VenueCatalogService = Depends(get_venue_catalog),
) -> PaperResetResponse:
    """Reset a paper book to its starting balance (FR-051).

    Audit history and the reset counter survive, so a run cannot be made to look like it
    never happened.
    """
    catalog.require_enabled(service.paper_venue_code())
    return await service.reset(venue_account_ref, starting_balance=body.starting_balance)


def build_trading_module(settings: TradingSettings | None = None) -> ModuleDef:
    """Compose the trading module.

    Called once per app. The venue registry is fresh per build rather than a shared global, so
    a test that disables a venue cannot change what another app sees.
    """
    resolved = settings or TradingSettings()
    books = PaperBookStore(
        starting_balance=resolved.paper_starting_balance,
        slippage_bps=resolved.paper_slippage_bps,
        commission_bps=resolved.paper_commission_bps,
    )
    registry = register_builtin_venues(VenueRegistry(), books=books)
    context = TradingModuleContext(settings=resolved, registry=registry, books=books)

    return ModuleDef(
        name="trading",
        version="1.0.0",
        owner="trading-team",
        router=router,
        app_state={STATE_KEY: context},
        subscriptions=(
            EventSubscriptionDef(
                consumer="trading.paper_reset_recorder",
                event_type="atlas.trading.paper.reset",
                handler=events.on_paper_reset,
            ),
            EventSubscriptionDef(
                consumer="trading.kill_switch_listener",
                event_type="atlas.trading.risk.kill_switch_engaged",
                handler=events.on_kill_switch_engaged,
            ),
            EventSubscriptionDef(
                consumer="trading.unresolved_watcher",
                event_type="atlas.trading.order.unresolved",
                handler=events.on_order_unresolved,
            ),
        ),
    )
