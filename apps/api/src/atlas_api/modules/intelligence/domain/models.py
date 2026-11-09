"""Domain models for the Market Intelligence System (Spec 04 §6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class AssetHeatmapItem:
    """Individual asset in the multi-asset heatmap."""

    symbol: str
    category: str  # FOREX | CRYPTO | COMMODITY | INDEX
    price: Decimal
    change_24h_pct: Decimal
    relative_volume: Decimal
    funding_rate: Decimal | None
    sentiment_score: Decimal  # -1.0000 to +1.0000


@dataclass(frozen=True)
class DerivativeMetricsItem:
    """Aggregated derivatives and order flow metrics for a symbol."""

    symbol: str
    venue: str
    open_interest: Decimal
    open_interest_usd: Decimal
    funding_rate: Decimal
    predicted_funding_rate: Decimal
    long_short_ratio: Decimal
    estimated_liquidations_long_usd: Decimal
    estimated_liquidations_short_usd: Decimal
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class WhaleTransferItem:
    """Large on-chain whale transaction (> $1M USD)."""

    tx_hash: str
    blockchain: str
    asset: str
    amount: Decimal
    amount_usd: Decimal
    from_entity: str
    to_entity: str
    transfer_type: str  # EXCHANGE_INFLOW | EXCHANGE_OUTFLOW | WALLET_TO_WALLET
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class MacroCalendarItem:
    """Scheduled macroeconomic event."""

    country: str
    event_name: str
    impact_level: str  # LOW | MEDIUM | HIGH
    previous_value: str
    forecast_value: str
    actual_value: str | None
    surprise_pct: Decimal | None
    release_date: datetime


@dataclass(frozen=True)
class NewsRAGItem:
    """Semantic news article with sentiment and embedding distance."""

    id: str
    source: str
    title: str
    summary: str
    url: str
    sentiment_score: Decimal
    impact_level: str
    entities: tuple[str, ...]
    similarity_score: Decimal
    published_at: datetime
