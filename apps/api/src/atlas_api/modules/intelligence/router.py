"""Market intelligence module v1 API endpoints and module definition (Spec 04 §9)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Path, Query, Request

from atlas_api.modules.intelligence.schemas import (
    DerivativeMetricsResponse,
    FearGreedResponse,
    HeatmapItemResponse,
    HeatmapResponse,
    MacroCalendarResponse,
    MacroEventResponse,
    NewsItemResponse,
    NewsSearchRequest,
    NewsSearchResponse,
    WhalesListResponse,
    WhaleTransferResponse,
)
from atlas_api.modules.intelligence.service import IntelligenceService
from atlas_api.modules.public import ModuleDef
from atlas_core.errors import InternalError

router = APIRouter(prefix="/intelligence", tags=["intelligence"])

STATE_KEY = "intelligence_context"


@dataclass(frozen=True)
class IntelligenceModuleContext:
    service: IntelligenceService


def get_intelligence_context(request: Request) -> IntelligenceModuleContext:
    context = getattr(request.app.state, STATE_KEY, None)
    if not isinstance(context, IntelligenceModuleContext):
        raise InternalError(
            internal_context={"detail": "intelligence module accessed before composition"}
        )
    return context


def get_intelligence_service(
    context: IntelligenceModuleContext = Depends(get_intelligence_context),
) -> IntelligenceService:
    return context.service


@router.get("/heatmap", response_model=HeatmapResponse)
async def get_heatmap(
    category: str | None = Query(default=None, description="Optional filter: FOREX, CRYPTO, COMMODITY, INDEX"),
    service: IntelligenceService = Depends(get_intelligence_service),
) -> HeatmapResponse:
    """Returns real-time multi-asset market heatmap with RVOL and sentiment scores."""
    items = await service.get_heatmap(category=category)
    return HeatmapResponse(
        items=[
            HeatmapItemResponse(
                symbol=i.symbol,
                category=i.category,
                price=i.price,
                change_24h_pct=i.change_24h_pct,
                relative_volume=i.relative_volume,
                funding_rate=i.funding_rate,
                sentiment_score=i.sentiment_score,
            )
            for i in items
        ],
        updated_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/derivatives/{symbol:path}", response_model=DerivativeMetricsResponse)
async def get_derivatives(
    symbol: str = Path(..., description="Asset symbol (e.g. BTC/USDT)"),
    service: IntelligenceService = Depends(get_intelligence_service),
) -> DerivativeMetricsResponse:
    """Returns Open Interest, funding rate predictions, and liquidation estimates."""
    m = await service.get_derivatives(symbol=symbol)
    return DerivativeMetricsResponse(
        symbol=m.symbol,
        venue=m.venue,
        open_interest=m.open_interest,
        open_interest_usd=m.open_interest_usd,
        funding_rate=m.funding_rate,
        predicted_funding_rate=m.predicted_funding_rate,
        long_short_ratio=m.long_short_ratio,
        estimated_liquidations_long_usd=m.estimated_liquidations_long_usd,
        estimated_liquidations_short_usd=m.estimated_liquidations_short_usd,
        recorded_at=m.recorded_at.isoformat(),
    )


@router.get("/onchain/whales", response_model=WhalesListResponse)
async def get_whales(
    limit: int = Query(default=10, ge=1, le=50),
    service: IntelligenceService = Depends(get_intelligence_service),
) -> WhalesListResponse:
    """Returns large on-chain transactions exceeding $1,000,000 equivalent."""
    whales = await service.get_whales(limit=limit)
    return WhalesListResponse(
        transfers=[
            WhaleTransferResponse(
                tx_hash=w.tx_hash,
                blockchain=w.blockchain,
                asset=w.asset,
                amount=w.amount,
                amount_usd=w.amount_usd,
                from_entity=w.from_entity,
                to_entity=w.to_entity,
                transfer_type=w.transfer_type,
                detected_at=w.detected_at.isoformat(),
            )
            for w in whales
        ]
    )


@router.get("/macro/calendar", response_model=MacroCalendarResponse)
async def get_macro_calendar(
    service: IntelligenceService = Depends(get_intelligence_service),
) -> MacroCalendarResponse:
    """Returns scheduled global economic releases with historical surprise factors."""
    events = await service.get_macro_calendar()
    return MacroCalendarResponse(
        events=[
            MacroEventResponse(
                country=e.country,
                event_name=e.event_name,
                impact_level=e.impact_level,
                previous_value=e.previous_value,
                forecast_value=e.forecast_value,
                actual_value=e.actual_value,
                surprise_pct=e.surprise_pct,
                release_date=e.release_date.isoformat(),
            )
            for e in events
        ]
    )


@router.get("/sentiment/fear-greed", response_model=FearGreedResponse)
async def get_fear_and_greed(
    service: IntelligenceService = Depends(get_intelligence_service),
) -> FearGreedResponse:
    """Returns market-wide Fear & Greed sentiment index."""
    data = await service.get_fear_and_greed()
    return FearGreedResponse(**data)


@router.post("/news/search", response_model=NewsSearchResponse)
async def search_news(
    body: NewsSearchRequest,
    service: IntelligenceService = Depends(get_intelligence_service),
) -> NewsSearchResponse:
    """Performs semantic vector RAG search over financial news embeddings."""
    results = await service.search_news(
        query=body.query,
        limit=body.limit,
        entities=body.entities,
    )
    return NewsSearchResponse(
        results=[
            NewsItemResponse(
                id=r.id,
                source=r.source,
                title=r.title,
                summary=r.summary,
                url=r.url,
                sentiment_score=r.sentiment_score,
                impact_level=r.impact_level,
                entities=list(r.entities),
                similarity_score=r.similarity_score,
                published_at=r.published_at.isoformat(),
            )
            for r in results
        ]
    )


def build_intelligence_module(env: str = "development") -> ModuleDef:
    """Composition root for the Spec 04 market intelligence module."""
    service = IntelligenceService()
    context = IntelligenceModuleContext(service=service)

    return ModuleDef(
        name="intelligence",
        version="1.0.0",
        owner="market-intelligence",
        router=router,
        app_state={STATE_KEY: context},
        health_probes={},
        subscriptions=(),
    )
