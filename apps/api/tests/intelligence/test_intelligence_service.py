"""Unit tests for IntelligenceService (Spec 04 §2, §8)."""

from decimal import Decimal
import pytest
from atlas_api.modules.intelligence.service import IntelligenceService


@pytest.mark.asyncio
async def test_heatmap_filtering():
    service = IntelligenceService()
    
    # All items
    all_items = await service.get_heatmap()
    assert len(all_items) >= 4
    symbols = [i.symbol for i in all_items]
    assert "BTC/USDT" in symbols
    assert "EUR/USD" in symbols

    # Filter by category
    crypto_items = await service.get_heatmap(category="crypto")
    assert all(i.category == "CRYPTO" for i in crypto_items)
    assert len(crypto_items) >= 2


@pytest.mark.asyncio
async def test_derivatives_metrics():
    service = IntelligenceService()
    deriv = await service.get_derivatives("BTC/USDT")
    
    assert deriv.symbol == "BTC/USDT"
    assert deriv.venue == "AGGREGATE"
    assert deriv.open_interest > Decimal("0")
    assert deriv.open_interest_usd > Decimal("0")
    assert deriv.funding_rate == Decimal("0.00010000")
    assert deriv.estimated_liquidations_long_usd > Decimal("0")


@pytest.mark.asyncio
async def test_whales_and_macro():
    service = IntelligenceService()
    
    whales = await service.get_whales(limit=5)
    assert len(whales) >= 2
    assert whales[0].amount_usd >= Decimal("1000000.00")
    assert whales[0].transfer_type in ("EXCHANGE_INFLOW", "EXCHANGE_OUTFLOW", "WALLET_TO_WALLET")

    macro = await service.get_macro_calendar()
    assert len(macro) >= 2
    assert any(m.impact_level == "HIGH" for m in macro)


@pytest.mark.asyncio
async def test_news_vector_rag_search():
    service = IntelligenceService()
    news = await service.search_news(query="bitcoin", limit=3)
    
    assert len(news) <= 3
    assert len(news) > 0
    assert news[0].similarity_score > Decimal("0.5")
    assert len(news[0].entities) > 0
