"""Unit tests for MCP and A2A protocols (prompt.md Features 5 & 6)."""

from decimal import Decimal
import pytest
from atlas_ai.mcp import create_default_mcp_server, MCPClient
from atlas_ai.a2a import A2ARegistry, A2ADelegationClient


@pytest.mark.asyncio
async def test_mcp_tool_execution():
    server = create_default_mcp_server()
    client = MCPClient(server)

    tools = await client.list_tools()
    assert len(tools) >= 4
    uris = {t.uri for t in tools}
    assert "mcp://market/get_quote" in uris
    assert "mcp://news/get_sentiment" in uris
    assert "mcp://risk/check_limits" in uris
    assert "mcp://trading/submit_order" in uris

    # 1. Market Quote via MCP
    quote_res = await client.call("mcp://market/get_quote", {"symbol": "BTC/USDT"}, caller_agent="market_agent")
    assert quote_res.status == "SUCCESS"
    assert quote_res.data["symbol"] == "BTC/USDT"
    assert "last_price" in quote_res.data

    # 2. News Sentiment via MCP
    news_res = await client.call("mcp://news/get_sentiment", {"symbol": "BTC/USDT"}, caller_agent="news_agent")
    assert news_res.status == "SUCCESS"
    assert news_res.data["sentiment_label"] == "BULLISH"

    # 3. Risk Verification via MCP
    risk_res = await client.call("mcp://risk/check_limits", {"symbol": "BTC/USDT"}, caller_agent="risk_agent")
    assert risk_res.status == "SUCCESS"
    assert risk_res.data["passed"] is True


@pytest.mark.asyncio
async def test_a2a_discovery_and_delegation():
    registry = A2ARegistry()
    specialists = registry.discover_specialists()
    assert len(specialists) >= 3

    client = A2ADelegationClient(registry)

    # Delegate sub-task to external Macro Sentinel
    res = await client.delegate(
        originator_agent="decision_agent",
        target_agent_id="agent-macro-global",
        task_type="cpi_analysis",
        payload={"symbol": "BTC/USDT"},
    )
    assert res.status == "COMPLETED"
    assert res.findings["macro_regime"] == "RISK_ON"
    assert res.confidence > Decimal("85.00")
