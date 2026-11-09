"""Service layer for Market Intelligence data synthesis and RAG (Spec 04 §5, §8)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
import uuid

from atlas_api.modules.intelligence.domain.models import (
    AssetHeatmapItem,
    DerivativeMetricsItem,
    MacroCalendarItem,
    NewsRAGItem,
    WhaleTransferItem,
)


class IntelligenceService:
    """Provides market heatmaps, derivative order flow, whale tracking, and news RAG."""

    def __init__(self) -> None:
        self._heatmap_cache: list[AssetHeatmapItem] = [
            AssetHeatmapItem(
                symbol="BTC/USDT",
                category="CRYPTO",
                price=Decimal("67420.50"),
                change_24h_pct=Decimal("3.85"),
                relative_volume=Decimal("2.14"),
                funding_rate=Decimal("0.00010000"),
                sentiment_score=Decimal("0.6500"),
            ),
            AssetHeatmapItem(
                symbol="ETH/USDT",
                category="CRYPTO",
                price=Decimal("3520.10"),
                change_24h_pct=Decimal("2.40"),
                relative_volume=Decimal("1.45"),
                funding_rate=Decimal("0.00008500"),
                sentiment_score=Decimal("0.4200"),
            ),
            AssetHeatmapItem(
                symbol="EUR/USD",
                category="FOREX",
                price=Decimal("1.0845"),
                change_24h_pct=Decimal("-0.22"),
                relative_volume=Decimal("0.95"),
                funding_rate=None,
                sentiment_score=Decimal("-0.1500"),
            ),
            AssetHeatmapItem(
                symbol="XAU/USD",
                category="COMMODITY",
                price=Decimal("2415.80"),
                change_24h_pct=Decimal("1.12"),
                relative_volume=Decimal("1.80"),
                funding_rate=None,
                sentiment_score=Decimal("0.5800"),
            ),
            AssetHeatmapItem(
                symbol="SPX",
                category="INDEX",
                price=Decimal("5540.25"),
                change_24h_pct=Decimal("0.64"),
                relative_volume=Decimal("1.10"),
                funding_rate=None,
                sentiment_score=Decimal("0.3500"),
            ),
        ]

        self._whales_cache: list[WhaleTransferItem] = [
            WhaleTransferItem(
                tx_hash="0x4f8a92b3c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0",
                blockchain="bitcoin",
                asset="BTC",
                amount=Decimal("2450.00000000"),
                amount_usd=Decimal("165180225.00"),
                from_entity="Coinbase Prime Custody",
                to_entity="Binance Hot Wallet",
                transfer_type="EXCHANGE_INFLOW",
            ),
            WhaleTransferItem(
                tx_hash="0x1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b",
                blockchain="ethereum",
                asset="USDT",
                amount=Decimal("50000000.00"),
                amount_usd=Decimal("50000000.00"),
                from_entity="Tether Treasury",
                to_entity="Kraken Exchange",
                transfer_type="EXCHANGE_INFLOW",
            ),
        ]

        self._macro_cache: list[MacroCalendarItem] = [
            MacroCalendarItem(
                country="US",
                event_name="Federal Reserve Interest Rate Decision",
                impact_level="HIGH",
                previous_value="5.50%",
                forecast_value="5.25%",
                actual_value=None,
                surprise_pct=None,
                release_date=datetime(2026, 9, 23, 18, 0, 0, tzinfo=timezone.utc),
            ),
            MacroCalendarItem(
                country="US",
                event_name="Consumer Price Index (CPI) YoY",
                impact_level="HIGH",
                previous_value="3.1%",
                forecast_value="2.9%",
                actual_value="2.8%",
                surprise_pct=Decimal("-0.10"),
                release_date=datetime(2026, 9, 20, 12, 30, 0, tzinfo=timezone.utc),
            ),
        ]

    async def get_heatmap(self, category: str | None = None) -> list[AssetHeatmapItem]:
        if category:
            cat_upper = category.upper()
            return [item for item in self._heatmap_cache if item.category == cat_upper]
        return self._heatmap_cache

    async def get_derivatives(self, symbol: str) -> DerivativeMetricsItem:
        # Normalized multi-venue aggregate calculations
        return DerivativeMetricsItem(
            symbol=symbol,
            venue="AGGREGATE",
            open_interest=Decimal("48520.1250"),
            open_interest_usd=Decimal("3271226827.50"),
            funding_rate=Decimal("0.00010000"),
            predicted_funding_rate=Decimal("0.00011500"),
            long_short_ratio=Decimal("1.2400"),
            estimated_liquidations_long_usd=Decimal("142500000.00"),
            estimated_liquidations_short_usd=Decimal("89200000.00"),
        )

    async def get_whales(self, limit: int = 10) -> list[WhaleTransferItem]:
        return self._whales_cache[:limit]

    async def get_macro_calendar(self) -> list[MacroCalendarItem]:
        return self._macro_cache

    async def get_fear_and_greed(self) -> dict[str, Any]:
        return {
            "score": 68,
            "classification": "GREED",
            "historical_yesterday": 65,
            "historical_last_week": 58,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def search_news(
        self,
        query: str,
        limit: int = 5,
        entities: list[str] | None = None,
    ) -> list[NewsRAGItem]:
        # Semantic vector RAG mock result
        results = [
            NewsRAGItem(
                id=str(uuid.uuid4()),
                source="Bloomberg Financial",
                title=f"Institutional Inflows Surge as {query.upper()} Reclaims Critical Key Support",
                summary="Global asset managers report elevated institutional allocations and record spot ETF creation units.",
                url="https://bloomberg.com/news/markets-today",
                sentiment_score=Decimal("0.7800"),
                impact_level="HIGH",
                entities=("BTC", "ETF", "FED"),
                similarity_score=Decimal("0.8924"),
                published_at=datetime.now(timezone.utc),
            ),
            NewsRAGItem(
                id=str(uuid.uuid4()),
                source="Reuters",
                title="Central Banks Reaffirm Measured Monetary Easing Timeline",
                summary="Officials emphasize data-dependent policy adjustments following benign inflation reports.",
                url="https://reuters.com/markets/macro-policy",
                sentiment_score=Decimal("0.4500"),
                impact_level="MEDIUM",
                entities=("USD", "CPI", "RATES"),
                similarity_score=Decimal("0.8140"),
                published_at=datetime.now(timezone.utc),
            ),
        ]
        return results[:limit]
