"""Market data configuration (T004).

Fail-fast at startup, per Spec 00 FR-005/006: a bad value aborts the process naming the field
rather than surfacing as a stale quote priced into a live order later.

The freshness limits here are the numbers the risk gate fails closed on, so they are config,
not constants — a venue with a genuinely slower feed needs a wider window, and hardcoding
would force a code change to accommodate one.
"""

from __future__ import annotations

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MarketDataSettings(BaseSettings):
    """Feed freshness, subscription caps, and history limits."""

    model_config = SettingsConfigDict(
        env_prefix="MARKETDATA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Freshness limits per asset class (seconds). A quote older than this is `stale` and the
    # risk gate refuses to price against it. Crypto and FX tick continuously, so a few seconds
    # of silence is already suspicious; equities and futures have wider legitimate gaps.
    freshness_limit_crypto_seconds: float = Field(default=3.0, gt=0, le=300)
    freshness_limit_forex_seconds: float = Field(default=3.0, gt=0, le=300)
    freshness_limit_equity_seconds: float = Field(default=10.0, gt=0, le=300)
    freshness_limit_default_seconds: float = Field(default=10.0, gt=0, le=300)

    #: Redis TTL for the latest quote. Expiry *is* the staleness signal — a missing key means
    #: "we have no fresh price", which is exactly what a consumer needs to fail closed on. Set
    #: slightly above the widest freshness limit so the classifier, not eviction, decides.
    quote_cache_ttl_seconds: int = Field(default=15, ge=1, le=600)

    #: Per-user streaming caps. Fan-out is the cost driver, so this is a real limit.
    max_subscriptions_per_user: int = Field(default=50, ge=1, le=1000)
    max_symbols_per_quote_request: int = Field(default=100, ge=1, le=1000)

    #: History fetch bounds.
    max_bars_per_request: int = Field(default=5000, ge=1, le=50_000)
    backfill_gap_threshold_seconds: int = Field(default=60, ge=1)

    #: How long a feed may be silent before it is declared degraded and quotes marked stale.
    feed_heartbeat_timeout_seconds: float = Field(default=20.0, gt=0, le=600)
    stream_reconnect_max_backoff_seconds: float = Field(default=60.0, gt=0, le=600)

    #: Server-Sent Events keep-alive for the browser quote channel.
    sse_keepalive_seconds: float = Field(default=15.0, gt=0, le=120)

    @model_validator(mode="after")
    def _cache_outlives_freshness(self) -> MarketDataSettings:
        """The cache must not expire a quote that would still count as fresh.

        Otherwise a quote vanishes from Redis while still inside its freshness window, and the
        gate refuses an order it should have priced — a false refusal caused purely by config.
        """
        widest = max(
            self.freshness_limit_crypto_seconds,
            self.freshness_limit_forex_seconds,
            self.freshness_limit_equity_seconds,
            self.freshness_limit_default_seconds,
        )
        if self.quote_cache_ttl_seconds <= widest:
            raise ValueError(
                f"MARKETDATA_QUOTE_CACHE_TTL_SECONDS ({self.quote_cache_ttl_seconds}) must "
                f"exceed the widest freshness limit ({widest}s), or fresh quotes will be "
                f"evicted before they go stale"
            )
        return self

    def freshness_limit_for(self, asset_class: str) -> float:
        """Limit for an asset class, falling back to the default for anything unlisted."""
        return {
            "crypto": self.freshness_limit_crypto_seconds,
            "forex": self.freshness_limit_forex_seconds,
            "equity": self.freshness_limit_equity_seconds,
        }.get(asset_class.lower(), self.freshness_limit_default_seconds)


__all__ = ["MarketDataSettings"]
