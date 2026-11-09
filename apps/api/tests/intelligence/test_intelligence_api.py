"""API tests for the Market Intelligence module (Spec 04 §9)."""

from decimal import Decimal
import pytest
from atlas_api.testing import build_test_app, make_client


@pytest.mark.asyncio
async def test_intelligence_heatmap_api():
    app = build_test_app()
    async with make_client(app) as client:
        resp = await client.get("/v1/intelligence/heatmap")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 4
    first = data["items"][0]
    assert "symbol" in first
    assert "price" in first
    assert "relative_volume" in first


@pytest.mark.asyncio
async def test_intelligence_derivatives_api():
    app = build_test_app()
    async with make_client(app) as client:
        resp = await client.get("/v1/intelligence/derivatives/BTC/USDT")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "BTC/USDT"
    assert Decimal(str(data["open_interest"])) > Decimal("0")
    assert Decimal(str(data["open_interest_usd"])) > Decimal("0")


@pytest.mark.asyncio
async def test_intelligence_whales_api():
    app = build_test_app()
    async with make_client(app) as client:
        resp = await client.get("/v1/intelligence/onchain/whales?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "transfers" in data
    assert len(data["transfers"]) >= 2
    assert Decimal(str(data["transfers"][0]["amount_usd"])) >= Decimal("1000000.00")


@pytest.mark.asyncio
async def test_intelligence_fear_greed_and_macro_api():
    app = build_test_app()
    async with make_client(app) as client:
        fg_resp = await client.get("/v1/intelligence/sentiment/fear-greed")
        assert fg_resp.status_code == 200
        fg_data = fg_resp.json()
        assert 0 <= fg_data["score"] <= 100

        macro_resp = await client.get("/v1/intelligence/macro/calendar")
        assert macro_resp.status_code == 200
        macro_data = macro_resp.json()
        assert len(macro_data["events"]) >= 2


@pytest.mark.asyncio
async def test_intelligence_news_rag_search_api():
    app = build_test_app()
    async with make_client(app) as client:
        resp = await client.post(
            "/v1/intelligence/news/search",
            json={"query": "Federal Reserve rate decision", "limit": 2},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert len(data["results"]) <= 2
    assert len(data["results"]) > 0
    assert "Bloomberg" in data["results"][0]["source"] or "Reuters" in data["results"][0]["source"]
