"""API contract tests for AI Marketplace & Creator Ecosystem module (Spec 12 §9)."""

from decimal import Decimal
import pytest
from atlas_api.testing import build_test_app, make_client


@pytest.mark.asyncio
async def test_marketplace_catalog_and_filter() -> None:
    app = build_test_app()
    async with make_client(app) as client:
        # All approved plugins
        resp = await client.get("/v1/marketplace/plugins")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 3
        assert any(p["slug"] == "trend-master-pro" for p in data)
        assert any(p["slug"] == "arbitrage-hunter" for p in data)

        # Filter by type
        filter_resp = await client.get("/v1/marketplace/plugins?plugin_type=STRATEGY")
        assert filter_resp.status_code == 200
        strategy_data = filter_resp.json()
        assert all(p["plugin_type"] == "STRATEGY" for p in strategy_data)
        assert any(p["slug"] == "trend-master-pro" for p in strategy_data)

        # Search query
        search_resp = await client.get("/v1/marketplace/plugins?search=arbitrage")
        assert search_resp.status_code == 200
        search_data = search_resp.json()
        assert len(search_data) == 1
        assert search_data[0]["slug"] == "arbitrage-hunter"


@pytest.mark.asyncio
async def test_marketplace_plugin_details() -> None:
    app = build_test_app()
    async with make_client(app) as client:
        resp = await client.get("/v1/marketplace/plugins/plugin-seed-trend-master")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Trend Master Pro"
        assert Decimal(str(data["price_usd"])) == Decimal("49.00")
        assert "sharpe_ratio" in data["backtest_metrics"]
        assert data["rating_count"] >= 30


@pytest.mark.asyncio
async def test_marketplace_submit_plugin_and_security_veto() -> None:
    app = build_test_app()
    async with make_client(app) as client:
        # Safe plugin submission
        safe_resp = await client.post(
            "/v1/marketplace/creator/submit",
            json={
                "name": "Mean Reversion Bot",
                "slug": "mean-reversion-bot",
                "plugin_type": "STRATEGY",
                "pricing_model": "FREE",
                "price_usd": "0.00",
                "version": "1.0.0",
                "manifest": {"entrypoint": "strategy.py"},
                "source_code": "def signal(): return 'HOLD'",
                "backtest_metrics": {"sharpe_ratio": 1.8},
            },
        )
        assert safe_resp.status_code == 200
        safe_data = safe_resp.json()
        assert safe_data["status"] == "APPROVED"
        assert safe_data["slug"] == "mean-reversion-bot"

        # Malicious code submission -> vetoed
        malicious_resp = await client.post(
            "/v1/marketplace/creator/submit",
            json={
                "name": "Evil Exploit Strategy",
                "slug": "evil-exploit-strat",
                "plugin_type": "STRATEGY",
                "pricing_model": "FREE",
                "price_usd": "0.00",
                "version": "1.0.0",
                "manifest": {"entrypoint": "strategy.py"},
                "source_code": "import os; os.system('cat /etc/passwd')",
                "backtest_metrics": {},
            },
        )
        assert malicious_resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_marketplace_install_and_creator_earnings() -> None:
    app = build_test_app()
    async with make_client(app) as client:
        # Install plugin
        install_resp = await client.post(
            "/v1/marketplace/plugins/plugin-seed-trend-master/install",
            json={
                "target_account_id": "account-broker-binance-01",
                "config": {"risk_per_trade_pct": "1.5"},
            },
        )
        assert install_resp.status_code == 200
        inst_data = install_resp.json()
        assert inst_data["plugin_id"] == "plugin-seed-trend-master"
        assert inst_data["is_active"] is True
        assert inst_data["config"]["risk_per_trade_pct"] == "1.5"

        # List user installations
        list_inst = await client.get("/v1/marketplace/installations")
        assert list_inst.status_code == 200
        all_inst = list_inst.json()
        assert any(i["plugin_id"] == "plugin-seed-trend-master" for i in all_inst)

        # Check creator earnings ledger (70/30 split accounted)
        earnings_resp = await client.get("/v1/marketplace/creator/earnings")
        assert earnings_resp.status_code == 200
        earnings_data = earnings_resp.json()
        assert Decimal(str(earnings_data["total_revenue_usd"])) > Decimal("0.00")
        assert Decimal(str(earnings_data["creator_earnings_usd"])) > Decimal("0.00")
        assert Decimal(str(earnings_data["platform_fees_usd"])) > Decimal("0.00")


@pytest.mark.asyncio
async def test_marketplace_review_flow() -> None:
    app = build_test_app()
    async with make_client(app) as client:
        # Add review
        review_resp = await client.post(
            "/v1/marketplace/plugins/plugin-seed-arbitrage-agent/reviews",
            json={
                "rating": 5,
                "review_title": "Outstanding execution and low latency",
                "review_body": "Captured spread opportunities seamlessly with zero slippage.",
            },
        )
        assert review_resp.status_code == 200
        rev_data = review_resp.json()
        assert rev_data["rating"] == 5
        assert rev_data["review_title"] == "Outstanding execution and low latency"
        assert rev_data["is_verified_purchaser"] is True

        # Fetch reviews
        get_revs = await client.get("/v1/marketplace/plugins/plugin-seed-arbitrage-agent/reviews")
        assert get_revs.status_code == 200
        revs_list = get_revs.json()
        assert len(revs_list) >= 1
        assert revs_list[0]["review_title"] == "Outstanding execution and low latency"
