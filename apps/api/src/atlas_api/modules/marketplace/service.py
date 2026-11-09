"""Service orchestrator for AI Marketplace & Creator Ecosystem (Spec 12 §2, §5)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import uuid

from atlas_api.modules.marketplace.domain.models import (
    CreatorAccount,
    MarketplaceInstallation,
    MarketplacePlugin,
    MarketplaceReview,
)
from atlas_api.modules.marketplace.domain.verifier import (
    calculate_creator_revenue_split,
    scan_plugin_code_security,
)
from atlas_api.modules.marketplace.schemas import (
    CreateReviewRequest,
    InstallPluginRequest,
    SubmitPluginRequest,
)
from atlas_core.errors import NotFoundError, ValidationError


class MarketplaceService:
    """Manages plugin lifecycle, security verification, licensing, and creator monetization."""

    def __init__(self) -> None:
        self._plugins: dict[str, MarketplacePlugin] = {}
        self._installations: dict[str, MarketplaceInstallation] = {}
        self._reviews: dict[str, list[MarketplaceReview]] = {}
        self._creators: dict[str, CreatorAccount] = {}
        self._seed_curated_plugins()

    def _seed_curated_plugins(self) -> None:
        now = datetime.now(timezone.utc)
        seeds = [
            MarketplacePlugin(
                id="plugin-seed-trend-master",
                creator_id="creator-quant-alpha",
                slug="trend-master-pro",
                name="Trend Master Pro",
                plugin_type="STRATEGY",
                current_version="1.4.0",
                pricing_model="ONE_TIME",
                price_usd=Decimal("49.00"),
                status="APPROVED",
                rating_avg=Decimal("4.85"),
                rating_count=34,
                install_count=1420,
                manifest={"entrypoint": "strategy.py", "supported_pairs": ["EUR/USD", "GBP/USD", "BTC/USD"]},
                backtest_metrics={"sharpe_ratio": 2.15, "max_drawdown_pct": 8.4, "win_rate_pct": 64.2},
                created_at=now,
                updated_at=now,
            ),
            MarketplacePlugin(
                id="plugin-seed-arbitrage-agent",
                creator_id="creator-deep-liquidity",
                slug="arbitrage-hunter",
                name="Arbitrage Hunter Agent",
                plugin_type="AGENT",
                current_version="2.0.1",
                pricing_model="SUBSCRIPTION",
                price_usd=Decimal("99.00"),
                status="APPROVED",
                rating_avg=Decimal("4.92"),
                rating_count=58,
                install_count=890,
                manifest={"entrypoint": "agent.py", "latency_budget_ms": 15},
                backtest_metrics={"sharpe_ratio": 3.02, "max_drawdown_pct": 4.1, "win_rate_pct": 78.5},
                created_at=now,
                updated_at=now,
            ),
            MarketplacePlugin(
                id="plugin-seed-volatility-sentinel",
                creator_id="creator-community-open",
                slug="volatility-shock-sentinel",
                name="Volatility Shock Sentinel",
                plugin_type="INDICATOR",
                current_version="1.0.0",
                pricing_model="FREE",
                price_usd=Decimal("0.00"),
                status="APPROVED",
                rating_avg=Decimal("4.70"),
                rating_count=112,
                install_count=3400,
                manifest={"entrypoint": "indicator.py"},
                backtest_metrics={"accuracy_pct": 91.2},
                created_at=now,
                updated_at=now,
            ),
        ]
        for p in seeds:
            self._plugins[p.id] = p
            # Seed creator accounts
            if p.creator_id not in self._creators:
                self._creators[p.creator_id] = CreatorAccount(
                    id=str(uuid.uuid4()),
                    user_id=p.creator_id,
                    stripe_connect_id=f"acct_{p.creator_id.replace('-', '')[:16]}",
                    payout_status="ACTIVE",
                    total_revenue_usd=p.price_usd * Decimal(str(p.install_count)),
                    creator_earnings_usd=(p.price_usd * Decimal(str(p.install_count)) * Decimal("0.70")).quantize(Decimal("0.01")),
                    platform_fees_usd=(p.price_usd * Decimal(str(p.install_count)) * Decimal("0.30")).quantize(Decimal("0.01")),
                )

    def list_plugins(
        self,
        plugin_type: str | None = None,
        search: str | None = None,
        status: str = "APPROVED",
    ) -> list[MarketplacePlugin]:
        plugins = [p for p in self._plugins.values() if p.status == status]
        if plugin_type:
            plugins = [p for p in plugins if p.plugin_type.upper() == plugin_type.upper()]
        if search:
            q = search.strip().lower()
            plugins = [p for p in plugins if q in p.name.lower() or q in p.slug.lower()]
        return sorted(plugins, key=lambda p: p.install_count, reverse=True)

    def get_plugin(self, plugin_id: str) -> MarketplacePlugin:
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            # Check by slug
            for p in self._plugins.values():
                if p.slug == plugin_id:
                    return p
            raise NotFoundError(f"Marketplace plugin '{plugin_id}' not found")
        return plugin

    def submit_plugin(self, creator_id: str, request: SubmitPluginRequest) -> MarketplacePlugin:
        # Check slug uniqueness
        for p in self._plugins.values():
            if p.slug == request.slug:
                raise ValidationError(f"Plugin slug '{request.slug}' already exists")

        # Security AST scan
        is_safe, error_reason = scan_plugin_code_security(request.source_code)
        if not is_safe:
            raise ValidationError(f"Code verification veto: {error_reason}")

        plugin_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        plugin = MarketplacePlugin(
            id=plugin_id,
            creator_id=creator_id,
            slug=request.slug,
            name=request.name,
            plugin_type=request.plugin_type.upper(),
            current_version=request.version,
            pricing_model=request.pricing_model.upper(),
            price_usd=request.price_usd,
            status="APPROVED",
            rating_avg=Decimal("0.00"),
            rating_count=0,
            install_count=0,
            manifest=request.manifest,
            backtest_metrics=request.backtest_metrics,
            created_at=now,
            updated_at=now,
        )
        self._plugins[plugin_id] = plugin

        if creator_id not in self._creators:
            self._creators[creator_id] = CreatorAccount(
                id=str(uuid.uuid4()),
                user_id=creator_id,
                stripe_connect_id=f"acct_{uuid.uuid4().hex[:16]}",
                payout_status="ACTIVE",
            )

        return plugin

    def install_plugin(
        self,
        user_id: str,
        plugin_id: str,
        request: InstallPluginRequest,
    ) -> MarketplaceInstallation:
        plugin = self.get_plugin(plugin_id)
        if plugin.status != "APPROVED":
            raise ValidationError(f"Cannot install plugin in status '{plugin.status}'")

        # Record purchase & revenue split
        if plugin.price_usd > Decimal("0.00"):
            creator_share, platform_share = calculate_creator_revenue_split(plugin.price_usd)
            creator = self._creators.get(plugin.creator_id)
            if creator:
                creator.total_revenue_usd += plugin.price_usd
                creator.creator_earnings_usd += creator_share
                creator.platform_fees_usd += platform_share

        # Increment install counter
        plugin.install_count += 1
        plugin.updated_at = datetime.now(timezone.utc)

        installation_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        installation = MarketplaceInstallation(
            id=installation_id,
            user_id=user_id,
            plugin_id=plugin.id,
            target_account_id=request.target_account_id,
            installed_version=plugin.current_version,
            is_active=True,
            config=request.config,
            installed_at=now,
            updated_at=now,
        )
        self._installations[installation_id] = installation
        return installation

    def list_user_installations(self, user_id: str) -> list[MarketplaceInstallation]:
        return [inst for inst in self._installations.values() if inst.user_id == user_id]

    def add_review(
        self,
        user_id: str,
        plugin_id: str,
        request: CreateReviewRequest,
    ) -> MarketplaceReview:
        plugin = self.get_plugin(plugin_id)

        review_id = str(uuid.uuid4())
        review = MarketplaceReview(
            id=review_id,
            plugin_id=plugin.id,
            user_id=user_id,
            rating=request.rating,
            review_title=request.review_title,
            review_body=request.review_body,
            is_verified_purchaser=True,
            created_at=datetime.now(timezone.utc),
        )

        if plugin.id not in self._reviews:
            self._reviews[plugin.id] = []
        self._reviews[plugin.id].append(review)

        # Update average rating
        all_ratings = [r.rating for r in self._reviews[plugin.id]]
        avg = sum(all_ratings) / len(all_ratings)
        plugin.rating_avg = Decimal(str(round(avg, 2)))
        plugin.rating_count = len(all_ratings)
        plugin.updated_at = datetime.now(timezone.utc)

        return review

    def get_plugin_reviews(self, plugin_id: str) -> list[MarketplaceReview]:
        plugin = self.get_plugin(plugin_id)
        return self._reviews.get(plugin.id, [])

    def get_creator_earnings(self, creator_id: str) -> CreatorAccount:
        account = self._creators.get(creator_id)
        if not account:
            account = CreatorAccount(
                id=str(uuid.uuid4()),
                user_id=creator_id,
                stripe_connect_id=f"acct_{uuid.uuid4().hex[:16]}",
                payout_status="ACTIVE",
            )
            self._creators[creator_id] = account
        return account
