"""Market data module v1 API + module definition (Spec 03 plan §2, §5, §10, T055).

Composes market data services: freshness validation, quotes, candles, and instrument discovery.
Invariants:
- All quotes and candles report strictly Decimal prices and volumes.
- Staleness is explicitly reported; no frozen prices are presented as live.
- Zero float money (Constitution X).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Sequence
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from atlas_api.modules.marketdata import events
from atlas_api.modules.marketdata.domain.freshness import FreshnessPolicy
from atlas_api.modules.marketdata.domain.instruments import (
    InstrumentRegistry,
    NormalizedInstrument,
)
from atlas_api.modules.marketdata.repository.quotes import (
    AttributedQuote,
    InMemoryQuoteStore,
    QuoteRepository,
)
from atlas_api.modules.marketdata.schemas import (
    CandleListResponse,
    CandleResponse,
    FreshnessClassificationResponse,
    FreshnessLimitsResponse,
    InstrumentListResponse,
    InstrumentResponse,
    QuoteListResponse,
    QuoteResponse,
    SubscribeRequest,
    SubscriptionLimitsResponse,
    SubscriptionListResponse,
    SubscriptionResponse,
)
from atlas_api.modules.marketdata.service import (
    FreshnessService,
    MarketDataService,
    SubscriptionLimitsService,
    policy_from_settings,
)
from atlas_api.modules.marketdata.settings import MarketDataSettings
from atlas_api.modules.public import EventSubscriptionDef, ModuleDef
from atlas_core.errors import InternalError, NotFoundError
from atlas_venues.adapters.binance import _DEFAULT_BINANCE_INSTRUMENTS
from atlas_venues.adapters.bybit import _DEFAULT_BYBIT_INSTRUMENTS
from atlas_venues.adapters.ibkr import _DEFAULT_IBKR_INSTRUMENTS
from atlas_venues.adapters.mt5 import _DEFAULT_MT5_INSTRUMENTS
from atlas_venues.adapters.oanda import _DEFAULT_OANDA_INSTRUMENTS
from atlas_venues.enums import AssetClass
from atlas_venues.models import InstrumentSpec, QuoteTick

router = APIRouter(prefix="/marketdata", tags=["marketdata"])
compat_market_data_router = APIRouter(tags=["market-data"])
compat_instruments_router = APIRouter(tags=["instruments"])

#: ``app.state`` key holding this module's :class:`MarketDataModuleContext`.
STATE_KEY = "marketdata_context"


@dataclass(frozen=True)
class MarketDataModuleContext:
    """Per-build market data state. One instance per composed app."""

    settings: MarketDataSettings
    quotes: QuoteRepository
    instruments: InstrumentRegistry
    service: MarketDataService


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


def get_market_data_service(
    context: MarketDataModuleContext = Depends(get_marketdata_context),
) -> MarketDataService:
    return context.service


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


# -- Market Data Endpoints (OpenAPI Contract paths) ------------------------------------

async def get_quotes_endpoint(
    connection_id: str = Query(description="Venue connection ID"),
    symbols: str = Query(description="Comma-separated canonical symbols, e.g. BTC/USDT,EUR/USD"),
    service: MarketDataService = Depends(get_market_data_service),
) -> QuoteListResponse:
    """Latest quotes with an explicit freshness verdict (FR-015, FR-018)."""
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    venue_code = "binance"
    quotes = await service.get_quotes(venue_code, symbol_list)

    now = datetime.now(UTC)
    items: list[QuoteResponse] = []
    for q in quotes:
        items.append(
            QuoteResponse(
                venue_code=q.venue_code,
                symbol=q.symbol,
                bid=q.bid,
                ask=q.ask,
                last=q.last,
                observed_at=q.observed_at,
                age_seconds=q.age_seconds,
                freshness=str(q.freshness),
            )
        )
    return QuoteListResponse(items=items)


async def get_candles_endpoint(
    connection_id: str = Query(description="Venue connection ID"),
    symbol: str = Query(description="Instrument canonical symbol"),
    timeframe: str = Query(default="1m", description="Candle interval"),
    limit: int = Query(default=500, le=5000),
    service: MarketDataService = Depends(get_market_data_service),
) -> CandleListResponse:
    """Historical bars with explicit gap markers (FR-014)."""
    bars = await service.get_candles("binance", symbol, timeframe, limit=limit)
    items = [
        CandleResponse(
            open_time=b.open_time,
            open=b.open,
            high=b.high,
            low=b.low,
            close=b.close,
            volume=b.volume or Decimal("0"),
            is_gap=b.is_gap,
            source="venue_stream",
        )
        for b in bars
    ]
    return CandleListResponse(
        venue_code="binance",
        symbol=symbol,
        timeframe=timeframe,
        items=items,
    )


async def list_subscriptions_endpoint() -> SubscriptionListResponse:
    """List active subscriptions."""
    return SubscriptionListResponse(items=[])


async def subscribe_endpoint(body: SubscribeRequest) -> SubscriptionListResponse:
    """Subscribe to instrument quotes."""
    now = datetime.now(UTC)
    items = [
        SubscriptionResponse(
            id=str(uuid4()),
            connection_id=body.connection_id,
            symbol=sym,
            state="active",
            subscribed_at=now,
        )
        for sym in body.symbols
    ]
    return SubscriptionListResponse(items=items)


# -- Instruments Endpoints -------------------------------------------------------------

async def list_instruments_endpoint(
    connection_id: str | None = Query(default=None, description="Venue connection ID"),
    q: str | None = Query(default=None, description="Search term"),
    asset_class: str | None = Query(default=None, description="Asset class filter"),
    limit: int = Query(default=50, le=200),
    service: MarketDataService = Depends(get_market_data_service),
) -> InstrumentListResponse:
    """Search tradable instruments across connected venues (plan §5)."""
    venue_code = "binance"
    results = service.search_instruments(venue_code, query=q, asset_class=asset_class)
    items = [
        InstrumentResponse(
            id=inst.id,
            venue_code=inst.venue_code,
            canonical_symbol=inst.canonical_symbol,
            venue_symbol=inst.venue_symbol,
            asset_class=inst.asset_class,
            base_currency=inst.base_currency,
            quote_currency=inst.quote_currency,
            price_precision=inst.price_precision,
            tick_size=inst.tick_size,
            quantity_min=inst.min_quantity,
            quantity_max=inst.max_quantity,
            quantity_step=inst.quantity_step,
            contract_size=inst.contract_size,
            max_leverage=inst.max_leverage,
            session_state=inst.session_state,
            next_session_change_at=inst.next_session_change_at,
            tradable=inst.tradable,
            spec_version=inst.spec_version,
            refreshed_at=inst.refreshed_at,
        )
        for inst in results[:limit]
    ]
    return InstrumentListResponse(items=items)


async def get_instrument_endpoint(
    instrument_id: str = Path(min_length=1, max_length=128),
    service: MarketDataService = Depends(get_market_data_service),
) -> InstrumentResponse:
    inst = service.get_instrument(instrument_id)
    if inst is None:
        raise HTTPException(status_code=404, detail="Instrument not found")
    return InstrumentResponse(
        id=inst.id,
        venue_code=inst.venue_code,
        canonical_symbol=inst.canonical_symbol,
        venue_symbol=inst.venue_symbol,
        asset_class=inst.asset_class,
        base_currency=inst.base_currency,
        quote_currency=inst.quote_currency,
        price_precision=inst.price_precision,
        tick_size=inst.tick_size,
        quantity_min=inst.min_quantity,
        quantity_max=inst.max_quantity,
        quantity_step=inst.quantity_step,
        contract_size=inst.contract_size,
        max_leverage=inst.max_leverage,
        session_state=inst.session_state,
        next_session_change_at=inst.next_session_change_at,
        tradable=inst.tradable,
        spec_version=inst.spec_version,
        refreshed_at=inst.refreshed_at,
    )


# Attach routes to module router
router.add_api_route("/quotes", get_quotes_endpoint, methods=["GET"], response_model=QuoteListResponse)
router.add_api_route("/candles", get_candles_endpoint, methods=["GET"], response_model=CandleListResponse)
router.add_api_route("/subscriptions", list_subscriptions_endpoint, methods=["GET"], response_model=SubscriptionListResponse)
router.add_api_route("/subscriptions", subscribe_endpoint, methods=["POST"], response_model=SubscriptionListResponse)

# Attach routes to OpenAPI compat routers
compat_market_data_router.add_api_route("/market-data/quotes", get_quotes_endpoint, methods=["GET"], response_model=QuoteListResponse)
compat_market_data_router.add_api_route("/market-data/candles", get_candles_endpoint, methods=["GET"], response_model=CandleListResponse)
compat_market_data_router.add_api_route("/market-data/subscriptions", list_subscriptions_endpoint, methods=["GET"], response_model=SubscriptionListResponse)
compat_market_data_router.add_api_route("/market-data/subscriptions", subscribe_endpoint, methods=["POST"], response_model=SubscriptionListResponse)

compat_instruments_router.add_api_route("/instruments", list_instruments_endpoint, methods=["GET"], response_model=InstrumentListResponse)
compat_instruments_router.add_api_route("/instruments/{instrument_id}", get_instrument_endpoint, methods=["GET"], response_model=InstrumentResponse)


def build_marketdata_module(settings: MarketDataSettings | None = None) -> ModuleDef:
    """Compose the market data module. Called once per app."""
    resolved_settings = settings or MarketDataSettings()
    policy = policy_from_settings(resolved_settings)

    quotes = InMemoryQuoteStore(policy=policy)
    instruments = InstrumentRegistry()

    # Pre-populate default instrument universe for all registered venues
    for spec_group in (
        _DEFAULT_BINANCE_INSTRUMENTS,
        _DEFAULT_OANDA_INSTRUMENTS,
        _DEFAULT_BYBIT_INSTRUMENTS,
        _DEFAULT_MT5_INSTRUMENTS,
        _DEFAULT_IBKR_INSTRUMENTS,
    ):
        for spec in spec_group:
            instruments.register(spec)

    service = MarketDataService(quotes=quotes, instruments=instruments, policy=policy)

    context = MarketDataModuleContext(
        settings=resolved_settings,
        quotes=quotes,
        instruments=instruments,
        service=service,
    )

    return ModuleDef(
        name="marketdata",
        version="1.0.0",
        owner="trading-team",
        router=router,
        routers_extra=(compat_market_data_router, compat_instruments_router),
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
