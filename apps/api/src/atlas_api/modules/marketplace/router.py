"""Marketplace API router and dependency injection (Spec 12 §2, §5)."""

from __future__ import annotations

from dataclasses import dataclass
from fastapi import APIRouter, Depends, Path, Query, Request

from atlas_api.modules.marketplace.domain.models import (
    CreatorAccount,
    MarketplaceInstallation,
    MarketplacePlugin,
    MarketplaceReview,
)
from atlas_api.modules.marketplace.schemas import (
    CreateReviewRequest,
    CreatorEarningsResponse,
    InstallationResponse,
    InstallPluginRequest,
    MarketplacePluginResponse,
    ReviewResponse,
    SubmitPluginRequest,
)
from atlas_api.modules.marketplace.service import MarketplaceService
from atlas_core.errors import InternalError

router = APIRouter(prefix="/marketplace", tags=["marketplace"])

STATE_KEY = "marketplace_context"


@dataclass(frozen=True)
class MarketplaceModuleContext:
    service: MarketplaceService


def get_marketplace_context(request: Request) -> MarketplaceModuleContext:
    context = getattr(request.app.state, STATE_KEY, None)
    if not isinstance(context, MarketplaceModuleContext):
        raise InternalError(
            internal_context={"detail": "marketplace module accessed before composition"}
        )
    return context


def get_marketplace_service(
    context: MarketplaceModuleContext = Depends(get_marketplace_context),
) -> MarketplaceService:
    return context.service


def _format_plugin(plugin: MarketplacePlugin) -> MarketplacePluginResponse:
    return MarketplacePluginResponse(
        id=plugin.id,
        creator_id=plugin.creator_id,
        slug=plugin.slug,
        name=plugin.name,
        plugin_type=plugin.plugin_type,
        current_version=plugin.current_version,
        pricing_model=plugin.pricing_model,
        price_usd=plugin.price_usd,
        status=plugin.status,
        rating_avg=plugin.rating_avg,
        rating_count=plugin.rating_count,
        install_count=plugin.install_count,
        manifest=plugin.manifest,
        backtest_metrics=plugin.backtest_metrics,
        created_at=plugin.created_at,
    )


def _format_installation(inst: MarketplaceInstallation) -> InstallationResponse:
    return InstallationResponse(
        id=inst.id,
        user_id=inst.user_id,
        plugin_id=inst.plugin_id,
        target_account_id=inst.target_account_id,
        installed_version=inst.installed_version,
        is_active=inst.is_active,
        config=inst.config,
        installed_at=inst.installed_at,
    )


def _format_review(review: MarketplaceReview) -> ReviewResponse:
    return ReviewResponse(
        id=review.id,
        plugin_id=review.plugin_id,
        user_id=review.user_id,
        rating=review.rating,
        review_title=review.review_title,
        review_body=review.review_body,
        is_verified_purchaser=review.is_verified_purchaser,
        created_at=review.created_at,
    )


def _format_earnings(creator: CreatorAccount) -> CreatorEarningsResponse:
    return CreatorEarningsResponse(
        creator_id=creator.user_id,
        stripe_connect_id=creator.stripe_connect_id,
        payout_status=creator.payout_status,
        total_revenue_usd=creator.total_revenue_usd,
        creator_earnings_usd=creator.creator_earnings_usd,
        platform_fees_usd=creator.platform_fees_usd,
    )


@router.get("/plugins", response_model=list[MarketplacePluginResponse])
async def list_plugins(
    plugin_type: str | None = Query(default=None),
    search: str | None = Query(default=None),
    service: MarketplaceService = Depends(get_marketplace_service),
) -> list[MarketplacePluginResponse]:
    """Browses verified marketplace plugins, strategies, agents, and indicators."""
    plugins = service.list_plugins(plugin_type=plugin_type, search=search)
    return [_format_plugin(p) for p in plugins]


@router.get("/plugins/{plugin_id}", response_model=MarketplacePluginResponse)
async def get_plugin_details(
    plugin_id: str = Path(...),
    service: MarketplaceService = Depends(get_marketplace_service),
) -> MarketplacePluginResponse:
    """Retrieves full details and backtesting performance for a specific plugin."""
    plugin = service.get_plugin(plugin_id)
    return _format_plugin(plugin)


@router.post("/plugins/{plugin_id}/install", response_model=InstallationResponse)
async def install_plugin(
    body: InstallPluginRequest,
    plugin_id: str = Path(...),
    request: Request = None,
    service: MarketplaceService = Depends(get_marketplace_service),
) -> InstallationResponse:
    """Executes 1-click install and licensing of a marketplace plugin onto a trading account."""
    principal = getattr(request.state, "principal", None) if request else None
    user_id = principal.user_id if principal else "demo-user-001"
    inst = service.install_plugin(user_id=user_id, plugin_id=plugin_id, request=body)
    return _format_installation(inst)


@router.get("/installations", response_model=list[InstallationResponse])
async def list_installations(
    request: Request = None,
    service: MarketplaceService = Depends(get_marketplace_service),
) -> list[InstallationResponse]:
    """Lists all active and installed marketplace plugins for the authenticated user."""
    principal = getattr(request.state, "principal", None) if request else None
    user_id = principal.user_id if principal else "demo-user-001"
    insts = service.list_user_installations(user_id)
    return [_format_installation(i) for i in insts]


@router.post("/plugins/{plugin_id}/reviews", response_model=ReviewResponse)
async def create_review(
    body: CreateReviewRequest,
    plugin_id: str = Path(...),
    request: Request = None,
    service: MarketplaceService = Depends(get_marketplace_service),
) -> ReviewResponse:
    """Submits a verified purchaser review and rating for an installed plugin."""
    principal = getattr(request.state, "principal", None) if request else None
    user_id = principal.user_id if principal else "demo-user-001"
    review = service.add_review(user_id=user_id, plugin_id=plugin_id, request=body)
    return _format_review(review)


@router.get("/plugins/{plugin_id}/reviews", response_model=list[ReviewResponse])
async def list_reviews(
    plugin_id: str = Path(...),
    service: MarketplaceService = Depends(get_marketplace_service),
) -> list[ReviewResponse]:
    """Retrieves all reviews and ratings for a plugin."""
    reviews = service.get_plugin_reviews(plugin_id)
    return [_format_review(r) for r in reviews]


@router.post("/creator/submit", response_model=MarketplacePluginResponse)
async def submit_plugin(
    body: SubmitPluginRequest,
    request: Request = None,
    service: MarketplaceService = Depends(get_marketplace_service),
) -> MarketplacePluginResponse:
    """Submits a new plugin to the creator marketplace with automated AST security scanning."""
    principal = getattr(request.state, "principal", None) if request else None
    creator_id = principal.user_id if principal else "creator-quant-007"
    plugin = service.submit_plugin(creator_id=creator_id, request=body)
    return _format_plugin(plugin)


@router.get("/creator/earnings", response_model=CreatorEarningsResponse)
async def get_creator_earnings(
    request: Request = None,
    service: MarketplaceService = Depends(get_marketplace_service),
) -> CreatorEarningsResponse:
    """Returns creator monetization ledger, gross sales, 70% earnings, and 30% platform fee splits."""
    principal = getattr(request.state, "principal", None) if request else None
    creator_id = principal.user_id if principal else "creator-quant-alpha"
    creator = service.get_creator_earnings(creator_id)
    return _format_earnings(creator)
