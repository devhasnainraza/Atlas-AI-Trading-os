"""Market data module v1 API + module definition.

Like trading, this module owns its own composition root and hands it to the app as module state
so the platform foundation stays unaware it exists (Constitution X). Settings are resolved once
at build time, not per request: a config error must abort startup, not surface as a 500 on the
first quote lookup.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, Depends, Query, Request

from atlas_api.modules.marketdata import events
from atlas_api.modules.marketdata.schemas import (
    FreshnessClassificationResponse,
    FreshnessLimitsResponse,
    SubscriptionLimitsResponse,
)
from atlas_api.modules.marketdata.service import FreshnessService, SubscriptionLimitsService
from atlas_api.modules.marketdata.settings import MarketDataSettings
from atlas_api.modules.public import EventSubscriptionDef, ModuleDef
from atlas_core.errors import InternalError
from atlas_venues.enums import AssetClass

router = APIRouter(prefix="/marketdata", tags=["marketdata"])

#: ``app.state`` key holding this module's :class:`MarketDataModuleContext`.
STATE_KEY = "marketdata_context"


@dataclass(frozen=True)
class MarketDataModuleContext:
    """Per-build market data state. One instance per composed app."""

    settings: MarketDataSettings


def get_marketdata_context(request: Request) -> MarketDataModuleContext:
    context = getattr(request.app.state, STATE_KEY, None)
    if not isinstance(context, MarketDataModuleContext):  # pragma: no cover - composition guard
        raise InternalError(
            internal_context={"detail": "marketdata module accessed before composition"}
        )
    return context


def get_freshness_service(
    context: MarketDataModuleContext = Depends(get_marketdata_context),
) -> FreshnessService:
    return FreshnessService(context.settings)


def get_subscription_limits(
    context: MarketDataModuleContext = Depends(get_marketdata_context),
) -> SubscriptionLimitsService:
    return SubscriptionLimitsService(context.settings)


@router.get("/freshness/limits", response_model=FreshnessLimitsResponse)
async def freshness_limits(
    service: FreshnessService = Depends(get_freshness_service),
) -> FreshnessLimitsResponse:
    """The staleness windows the risk gate fails closed on (FR-018)."""
    return service.limits()


@router.get("/freshness/classify", response_model=FreshnessClassificationResponse)
async def classify_freshness(
    asset_class: AssetClass = Query(description="Asset class whose window applies"),
    age_seconds: float = Query(ge=0, le=86_400, description="Age of the quote in seconds"),
    service: FreshnessService = Depends(get_freshness_service),
) -> FreshnessClassificationResponse:
    """Answer "would a quote this old have been usable?" without guesswork (FR-039)."""
    return service.classify(asset_class, age_seconds)


@router.get("/subscriptions/limits", response_model=SubscriptionLimitsResponse)
async def subscription_limits(
    service: SubscriptionLimitsService = Depends(get_subscription_limits),
) -> SubscriptionLimitsResponse:
    """Streaming and history caps, published so a client can size requests before rejection."""
    return service.limits()


def build_marketdata_module(settings: MarketDataSettings | None = None) -> ModuleDef:
    """Compose the market data module. Called once per app."""
    context = MarketDataModuleContext(settings=settings or MarketDataSettings())

    return ModuleDef(
        name="marketdata",
        version="1.0.0",
        owner="trading-team",
        router=router,
        app_state={STATE_KEY: context},
        subscriptions=(
            EventSubscriptionDef(
                consumer="marketdata.stale_quote_watcher",
                event_type="atlas.marketdata.quote.stale",
                handler=events.on_quote_stale,
            ),
            EventSubscriptionDef(
                consumer="marketdata.feed_health_watcher",
                event_type="atlas.marketdata.feed.degraded",
                handler=events.on_feed_degraded,
            ),
            EventSubscriptionDef(
                consumer="marketdata.feed_recovery_watcher",
                event_type="atlas.marketdata.feed.recovered",
                handler=events.on_feed_recovered,
            ),
        ),
    )
