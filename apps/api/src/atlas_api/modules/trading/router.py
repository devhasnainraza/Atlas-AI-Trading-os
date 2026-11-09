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

from fastapi import APIRouter, Depends, Path, Query, Request

from atlas_api.deps import get_runtime
from atlas_api.modules.public import EventSubscriptionDef, ModuleDef
from atlas_api.modules.trading import events
from atlas_api.modules.trading.domain.connections import ConnectionHealth
from atlas_api.modules.trading.repository.connections import (
    ConnectionRepository,
    InMemoryConnectionRepository,
)
from atlas_api.modules.trading.schemas import (
    CreateVenueConnectionRequest,
    LiveTradingStatusResponse,
    PaperResetRequest,
    PaperResetResponse,
    PositionListResponse,
    RiskRulesResponse,
    VenueAccountListResponse,
    VenueConnectionListResponse,
    VenueConnectionResponse,
    VenueListResponse,
    VerifyVenueConnectionResponse,
)
from atlas_api.modules.trading.service import (
    LiveTradingStatusService,
    PaperAccountService,
    RiskCatalogService,
    VenueCatalogService,
    VenueConnectionService,
)
from atlas_api.modules.trading.settings import TradingSettings
from atlas_api.modules.trading.venues import PaperBookStore, register_builtin_venues
from atlas_api.runtime import PlatformRuntime
from atlas_core.errors import InternalError
from atlas_venues.enums import VenueEnvironment
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
    connections: ConnectionRepository


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


def get_connection_service(
    context: TradingModuleContext = Depends(get_trading_context),
    runtime: PlatformRuntime = Depends(get_runtime),
) -> VenueConnectionService:
    catalog = VenueCatalogService(context.registry, runtime.flags)
    return VenueConnectionService(
        repository=context.connections,
        registry=context.registry,
        flags=runtime.flags,
        catalog=catalog,
        settings=context.settings,
        outbox=runtime.outbox,
        bus=runtime.bus,
        audit_log=runtime.audit_log,
    )


@router.get("/venues", response_model=VenueListResponse)
async def list_venues(
    catalog: VenueCatalogService = Depends(get_venue_catalog),
) -> VenueListResponse:
    """Every venue this build ships, with its declared capabilities and flag state (FR-001)."""
    return catalog.list_venues()


@router.get("/venue-connections", response_model=VenueConnectionListResponse)
async def list_venue_connections(
    request: Request,
    environment: VenueEnvironment | None = None,
    health: ConnectionHealth | None = None,
    service: VenueConnectionService = Depends(get_connection_service),
) -> VenueConnectionListResponse:
    """List the caller's venue connections."""
    user_id = request.headers.get("X-User-ID", "usr-default-001")
    return await service.list_connections(user_id, environment=environment, health=health)


@router.post("/venue-connections", response_model=VenueConnectionResponse, status_code=201)
async def create_venue_connection(
    request: Request,
    body: CreateVenueConnectionRequest,
    service: VenueConnectionService = Depends(get_connection_service),
) -> VenueConnectionResponse:
    """Create a venue connection from a stored credential (FR-004..FR-011)."""
    user_id = request.headers.get("X-User-ID", "usr-default-001")
    step_up_verified = request.headers.get("X-Step-Up-MFA", "").lower() == "true"
    return await service.create_connection(user_id, body, step_up_verified=step_up_verified)


@router.get("/venue-connections/{connection_id}", response_model=VenueConnectionResponse)
async def get_venue_connection(
    request: Request,
    connection_id: str = Path(min_length=1, max_length=128),
    service: VenueConnectionService = Depends(get_connection_service),
) -> VenueConnectionResponse:
    """Get one connection with health and capabilities."""
    user_id = request.headers.get("X-User-ID", "usr-default-001")
    return await service.get_connection(connection_id, user_id=user_id)


@router.delete("/venue-connections/{connection_id}", status_code=204)
async def disconnect_venue_connection(
    request: Request,
    connection_id: str = Path(min_length=1, max_length=128),
    service: VenueConnectionService = Depends(get_connection_service),
) -> None:
    """Disconnect a venue. Stops streams and routing."""
    user_id = request.headers.get("X-User-ID", "usr-default-001")
    await service.delete_connection(connection_id, user_id=user_id)


@router.post("/venue-connections/{connection_id}/verify", response_model=VerifyVenueConnectionResponse)
async def verify_venue_connection(
    request: Request,
    connection_id: str = Path(min_length=1, max_length=128),
    service: VenueConnectionService = Depends(get_connection_service),
) -> VerifyVenueConnectionResponse:
    """Re-verify reachability and granted permissions."""
    user_id = request.headers.get("X-User-ID", "usr-default-001")
    return await service.verify_connection(connection_id, user_id=user_id)


@router.get("/venue-connections/{connection_id}/accounts", response_model=VenueAccountListResponse)
async def list_venue_accounts(
    request: Request,
    connection_id: str = Path(min_length=1, max_length=128),
    refresh: bool = False,
    service: VenueConnectionService = Depends(get_connection_service),
) -> VenueAccountListResponse:
    """List accounts exposed by a connection."""
    user_id = request.headers.get("X-User-ID", "usr-default-001")
    return await service.list_accounts(connection_id, user_id=user_id, refresh=refresh)


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


@router.get("/positions", response_model=PositionListResponse)
async def list_positions_endpoint(
    request: Request,
    connection_id: str | None = Query(default=None, description="Filter by venue connection"),
    service: VenueConnectionService = Depends(get_connection_service),
) -> PositionListResponse:
    """List open positions across connections with external-origin flags and freshness (FR-017, FR-020)."""
    user_id = request.headers.get("X-User-ID", "usr-default-001")
    return await service.list_positions(connection_id, user_id=user_id)


compat_router = APIRouter(tags=["connections", "venues"])

compat_router.add_api_route("/venues", list_venues, methods=["GET"], response_model=VenueListResponse)
compat_router.add_api_route("/venue-connections", list_venue_connections, methods=["GET"], response_model=VenueConnectionListResponse)
compat_router.add_api_route("/venue-connections", create_venue_connection, methods=["POST"], response_model=VenueConnectionResponse, status_code=201)
compat_router.add_api_route("/venue-connections/{connection_id}", get_venue_connection, methods=["GET"], response_model=VenueConnectionResponse)
compat_router.add_api_route("/venue-connections/{connection_id}", disconnect_venue_connection, methods=["DELETE"], status_code=204)
compat_router.add_api_route("/venue-connections/{connection_id}/verify", verify_venue_connection, methods=["POST"], response_model=VerifyVenueConnectionResponse)
compat_router.add_api_route("/venue-connections/{connection_id}/accounts", list_venue_accounts, methods=["GET"], response_model=VenueAccountListResponse)
compat_router.add_api_route("/positions", list_positions_endpoint, methods=["GET"], response_model=PositionListResponse)


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
    connections = InMemoryConnectionRepository()
    context = TradingModuleContext(
        settings=resolved,
        registry=registry,
        books=books,
        connections=connections,
    )

    return ModuleDef(
        name="trading",
        version="1.0.0",
        owner="trading-team",
        router=router,
        routers_extra=(compat_router,),
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
            EventSubscriptionDef(
                consumer="trading.credential_revocation_handler",
                event_type="atlas.credentials.credential.revoked",
                handler=events.make_credential_revoked_handler(connections),
            ),
        ),
    )
