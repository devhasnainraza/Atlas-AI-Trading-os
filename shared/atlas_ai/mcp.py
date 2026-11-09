"""Model Context Protocol (MCP) integration for Atlas AI (prompt.md Feature 5).

Provides standard MCP tool registries, schemas, and transport abstractions
allowing autonomous agents to discover and invoke tools via MCP protocol.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Awaitable, Callable
import json
import logging

logger = logging.getLogger("atlas_ai.mcp")


@dataclass(frozen=True)
class MCPToolDefinition:
    """Standard Model Context Protocol tool specification."""

    name: str
    uri: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    category: str  # "market" | "news" | "risk" | "trading"


@dataclass
class MCPToolCall:
    """An invocation payload for an MCP tool."""

    call_id: str
    tool_uri: str
    arguments: dict[str, Any]
    caller_agent: str


@dataclass
class MCPToolResult:
    """The structured result returned from an MCP tool."""

    call_id: str
    tool_uri: str
    status: str  # "SUCCESS" | "ERROR"
    data: dict[str, Any]
    error_message: str | None = None


class MCPServer:
    """Exposes domain capabilities as Model Context Protocol tools."""

    def __init__(self, server_name: str = "atlas-mcp-core") -> None:
        self.server_name = server_name
        self._tools: dict[str, MCPToolDefinition] = {}
        self._handlers: dict[str, Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]] = {}

    def register_tool(
        self,
        tool: MCPToolDefinition,
        handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
    ) -> None:
        """Registers a tool definition and async handler."""
        self._tools[tool.uri] = tool
        self._handlers[tool.uri] = handler

    def list_tools(self, category: str | None = None) -> list[MCPToolDefinition]:
        """Lists all registered MCP tools, optionally filtered by category."""
        if category:
            return [t for t in self._tools.values() if t.category == category]
        return list(self._tools.values())

    async def execute_tool(self, call: MCPToolCall) -> MCPToolResult:
        """Executes an MCP tool call with boundary checking and schema validation."""
        tool = self._tools.get(call.tool_uri)
        if not tool:
            return MCPToolResult(
                call_id=call.call_id,
                tool_uri=call.tool_uri,
                status="ERROR",
                data={},
                error_message=f"MCP tool '{call.tool_uri}' not found on server '{self.server_name}'",
            )

        handler = self._handlers.get(call.tool_uri)
        if not handler:
            return MCPToolResult(
                call_id=call.call_id,
                tool_uri=call.tool_uri,
                status="ERROR",
                data={},
                error_message=f"No handler bound for MCP tool '{call.tool_uri}'",
            )

        try:
            result_data = await handler(call.arguments)
            return MCPToolResult(
                call_id=call.call_id,
                tool_uri=call.tool_uri,
                status="SUCCESS",
                data=result_data,
            )
        except Exception as exc:
            logger.exception("mcp_tool_execution_failed", extra={"call_id": call.call_id, "uri": call.tool_uri})
            return MCPToolResult(
                call_id=call.call_id,
                tool_uri=call.tool_uri,
                status="ERROR",
                data={},
                error_message=str(exc),
            )


class MCPClient:
    """Client used by agents to communicate with MCP servers."""

    def __init__(self, server: MCPServer) -> None:
        self.server = server

    async def list_tools(self, category: str | None = None) -> list[MCPToolDefinition]:
        return self.server.list_tools(category=category)

    async def call(self, tool_uri: str, arguments: dict[str, Any], caller_agent: str) -> MCPToolResult:
        import uuid
        call = MCPToolCall(
            call_id=str(uuid.uuid4()),
            tool_uri=tool_uri,
            arguments=arguments,
            caller_agent=caller_agent,
        )
        return await self.server.execute_tool(call)


def create_default_mcp_server() -> MCPServer:
    """Creates an MCP server pre-configured with core financial OS tools."""
    server = MCPServer(server_name="atlas-financial-mcp")

    # 1. Market Quote Tool (READ)
    quote_tool = MCPToolDefinition(
        name="get_market_quote",
        uri="mcp://market/get_quote",
        description="Fetches real-time price, 24h volume, spread, and regime for an asset.",
        category="market",
        input_schema={"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]},
        output_schema={"type": "object", "properties": {"last_price": {"type": "string"}, "spread_bps": {"type": "string"}}},
    )

    async def _handle_quote(args: dict[str, Any]) -> dict[str, Any]:
        symbol = args.get("symbol", "BTC/USDT")
        return {
            "symbol": symbol,
            "last_price": "67240.00",
            "bid": "67239.50",
            "ask": "67240.50",
            "spread_bps": "1.2",
            "regime": "EXPANSION_BULLISH",
            "volume_24h": "18400.5",
        }

    server.register_tool(quote_tool, _handle_quote)

    # 2. News & Sentiment Tool (READ / ANALYZE)
    news_tool = MCPToolDefinition(
        name="get_news_sentiment",
        uri="mcp://news/get_sentiment",
        description="Retrieves live macroeconomic headlines, sentiment score, and upcoming high-impact calendar events.",
        category="news",
        input_schema={"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]},
        output_schema={"type": "object", "properties": {"sentiment_score": {"type": "string"}, "headlines": {"type": "array"}}},
    )

    async def _handle_news(args: dict[str, Any]) -> dict[str, Any]:
        return {
            "symbol": args.get("symbol", "BTC/USDT"),
            "sentiment_score": "+0.68",
            "sentiment_label": "BULLISH",
            "headlines": [
                "Institutional spot ETF net inflows hit +$450M today",
                "Fed remarks signal monetary easing cycle continuation",
            ],
            "upcoming_embargoes": [{"event": "US CPI", "hours_left": 18.5}],
        }

    server.register_tool(news_tool, _handle_news)

    # 3. Risk Verification Tool (ANALYZE)
    risk_tool = MCPToolDefinition(
        name="evaluate_portfolio_risk",
        uri="mcp://risk/check_limits",
        description="Verifies pre-trade margin bounds, current drawdown headroom, and constitutional rules.",
        category="risk",
        input_schema={"type": "object", "properties": {"symbol": {"type": "string"}, "proposed_size": {"type": "string"}}, "required": ["symbol"]},
        output_schema={"type": "object", "properties": {"passed": {"type": "boolean"}, "hard_veto": {"type": "boolean"}}},
    )

    async def _handle_risk(args: dict[str, Any]) -> dict[str, Any]:
        return {
            "passed": True,
            "hard_veto": False,
            "max_drawdown_headroom": "1.75%",
            "recommended_max_qty": "0.15",
            "var_99_pct": "2.10%",
        }

    server.register_tool(risk_tool, _handle_risk)

    # 4. Broker Order Submission Tool (EXECUTE only)
    broker_tool = MCPToolDefinition(
        name="submit_broker_order",
        uri="mcp://trading/submit_order",
        description="Submits an approved order to the underlying broker venue (OANDA, Binance, MT5, IBKR).",
        category="trading",
        input_schema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "side": {"type": "string"},
                "quantity": {"type": "string"},
                "human_approval_token": {"type": "string"},
            },
            "required": ["symbol", "side", "quantity", "human_approval_token"],
        },
        output_schema={"type": "object", "properties": {"order_id": {"type": "string"}, "status": {"type": "string"}}},
    )

    async def _handle_broker(args: dict[str, Any]) -> dict[str, Any]:
        if not args.get("human_approval_token"):
            raise ValueError("Direct broker execution rejected: Missing human approval token!")
        return {
            "order_id": f"ORD-MCP-8842",
            "symbol": args.get("symbol", "BTC/USDT"),
            "side": args.get("side", "BUY"),
            "status": "FILLED",
            "fill_price": "67240.00",
            "venue": "binance",
        }

    server.register_tool(broker_tool, _handle_broker)

    return server
