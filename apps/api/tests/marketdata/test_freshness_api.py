"""Market data freshness contract (US2 read surfaces).

The freshness window is the number the risk gate fails closed on, so these tests pin the
behaviour that matters: the boundary is inclusive, the configured limit is the one enforced, and
anything that is not provably fresh is stale.
"""

from __future__ import annotations

import pytest

from atlas_api.modules.marketdata.domain.freshness import FreshnessPolicy
from atlas_api.modules.marketdata.service import policy_from_settings
from atlas_api.modules.marketdata.settings import MarketDataSettings
from atlas_api.testing import build_test_app, make_client
from atlas_venues.enums import DataFreshness


async def test_freshness_limits_are_published():
    app = build_test_app()
    async with make_client(app) as client:
        resp = await client.get("/v1/marketdata/freshness/limits")
    assert resp.status_code == 200
    body = resp.json()
    assert body["crypto_seconds"] > 0
    assert body["quote_cache_ttl_seconds"] > max(
        body["crypto_seconds"], body["forex_seconds"], body["equity_seconds"]
    ), "the cache must not evict a quote that is still fresh"


async def test_classification_uses_the_asset_class_window():
    app = build_test_app()
    async with make_client(app) as client:
        crypto = await client.get(
            "/v1/marketdata/freshness/classify",
            params={"asset_class": "crypto", "age_seconds": 5},
        )
        equity = await client.get(
            "/v1/marketdata/freshness/classify",
            params={"asset_class": "equity", "age_seconds": 5},
        )
    # Same age, different verdict: crypto ticks continuously, so five seconds of silence is
    # already suspicious, while an equity gap of five seconds is ordinary.
    assert crypto.json()["freshness"] == DataFreshness.STALE
    assert crypto.json()["usable_for_pricing"] is False
    assert equity.json()["freshness"] == DataFreshness.FRESH
    assert equity.json()["usable_for_pricing"] is True


async def test_an_unknown_asset_class_is_rejected_not_defaulted():
    """A typo must not silently borrow the default window."""
    app = build_test_app()
    async with make_client(app) as client:
        resp = await client.get(
            "/v1/marketdata/freshness/classify",
            params={"asset_class": "crytpo", "age_seconds": 1},
        )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "ATLAS-VAL-001"


async def test_configured_limits_are_the_ones_enforced(monkeypatch: pytest.MonkeyPatch):
    """The library default must not silently overrule deployment config.

    ``atlas_venues.timing.classify_freshness`` reads a module constant. If the API delegated to
    it, widening a limit in config would change the published number and nothing else — the
    worst kind of config: one that appears to work.
    """
    monkeypatch.setenv("MARKETDATA_FRESHNESS_LIMIT_CRYPTO_SECONDS", "30")
    monkeypatch.setenv("MARKETDATA_QUOTE_CACHE_TTL_SECONDS", "45")
    app = build_test_app()
    async with make_client(app) as client:
        limits = await client.get("/v1/marketdata/freshness/limits")
        classified = await client.get(
            "/v1/marketdata/freshness/classify",
            params={"asset_class": "crypto", "age_seconds": 20},
        )
    assert limits.json()["crypto_seconds"] == 30.0
    assert classified.json()["limit_seconds"] == 30.0
    assert classified.json()["freshness"] == DataFreshness.FRESH


async def test_subscription_limits_are_published():
    app = build_test_app()
    async with make_client(app) as client:
        resp = await client.get("/v1/marketdata/subscriptions/limits")
    assert resp.status_code == 200
    body = resp.json()
    assert body["max_subscriptions_per_user"] >= 1
    assert body["max_symbols_per_quote_request"] >= 1
    assert body["max_bars_per_request"] >= 1


class TestFreshnessPolicy:
    """Unit-level boundary behaviour, where the off-by-one lives."""

    policy = FreshnessPolicy(
        crypto_seconds=3.0, forex_seconds=3.0, equity_seconds=10.0, default_seconds=10.0
    )

    def test_exactly_at_the_limit_is_still_fresh(self):
        assert self.policy.classify(3.0, "crypto") is DataFreshness.FRESH

    def test_just_past_the_limit_is_stale(self):
        assert self.policy.classify(3.001, "crypto") is DataFreshness.STALE

    def test_an_unlisted_asset_class_gets_the_default_window(self):
        assert self.policy.limit_for("commodity") == 10.0
        assert self.policy.classify(9.0, "commodity") is DataFreshness.FRESH

    def test_a_future_dated_quote_is_stale_not_maximally_fresh(self):
        """Negative age means clock skew, and skew we cannot reconcile is not trustworthy."""
        assert self.policy.classify(-5.0, "crypto") is DataFreshness.STALE
        assert self.policy.usable_for_pricing(-5.0, "crypto") is False

    def test_a_non_positive_limit_is_refused(self):
        """Zero would mark every quote stale on arrival, halting trading from a config typo."""
        with pytest.raises(ValueError, match="must be positive"):
            FreshnessPolicy(
                crypto_seconds=0, forex_seconds=3.0, equity_seconds=10.0, default_seconds=10.0
            )

    def test_a_non_numeric_limit_is_refused(self):
        with pytest.raises(TypeError, match="must be a number"):
            FreshnessPolicy(
                crypto_seconds="3",  # type: ignore[arg-type]
                forex_seconds=3.0,
                equity_seconds=10.0,
                default_seconds=10.0,
            )

    def test_the_policy_mirrors_the_settings_it_was_built_from(self):
        settings = MarketDataSettings()
        policy = policy_from_settings(settings)
        for asset_class in ("crypto", "forex", "equity", "commodity"):
            assert policy.limit_for(asset_class) == settings.freshness_limit_for(asset_class)


def test_the_cache_ttl_must_outlive_the_widest_freshness_window(monkeypatch: pytest.MonkeyPatch):
    """A config that evicts fresh quotes is a config that causes false refusals."""
    monkeypatch.setenv("MARKETDATA_QUOTE_CACHE_TTL_SECONDS", "2")
    monkeypatch.setenv("MARKETDATA_FRESHNESS_LIMIT_CRYPTO_SECONDS", "5")
    with pytest.raises(ValueError, match="must exceed the widest freshness limit"):
        MarketDataSettings()
