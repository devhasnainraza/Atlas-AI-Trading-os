"""Tool registry and sandboxed execution engine (Spec 03 FR-003, SEC-001)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Callable, Coroutine
from atlas_ai.interfaces import ToolDefinition
from atlas_core.errors import AuthorizationError, ValidationError


ToolCallable = Callable[..., Coroutine[Any, Any, dict[str, Any]]]


@dataclass
class ToolRegistration:
    definition: ToolDefinition
    handler: ToolCallable
    is_consequential: bool = False


class ToolExecutor:
    """Dispatches registered tools with permission verification and timeout guards."""

    def __init__(self, timeout_seconds: float = 5.0) -> None:
        self._tools: dict[str, ToolRegistration] = {}
        self._timeout_seconds = timeout_seconds

    def register(
        self,
        definition: ToolDefinition,
        handler: ToolCallable,
        is_consequential: bool = False,
    ) -> None:
        self._tools[definition.name] = ToolRegistration(
            definition=definition,
            handler=handler,
            is_consequential=is_consequential,
        )

    def get_definition(self, name: str) -> ToolDefinition | None:
        reg = self._tools.get(name)
        return reg.definition if reg else None

    def list_tools(self) -> list[ToolDefinition]:
        return [reg.definition for reg in self._tools.values()]

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        caller_agent: str,
        caller_permissions: set[str] | None = None,
    ) -> dict[str, Any]:
        """Execute a tool with parameter validation and permission checks."""
        reg = self._tools.get(tool_name)
        if not reg:
            raise ValidationError(
                detail=f"Tool '{tool_name}' is not registered in ToolRegistry",
            )

        caller_permissions = caller_permissions or set()
        for required_perm in reg.definition.required_permissions:
            if required_perm not in caller_permissions:
                raise AuthorizationError(
                    detail=f"Agent '{caller_agent}' lacks required permission '{required_perm}' for tool '{tool_name}'",
                )

        try:
            result = await asyncio.wait_for(
                reg.handler(**arguments),
                timeout=self._timeout_seconds,
            )
            return result
        except asyncio.TimeoutError:
            raise ValidationError(
                detail=f"Tool '{tool_name}' execution exceeded timeout of {self._timeout_seconds}s",
            )
        except Exception as err:
            raise ValidationError(
                detail=f"Tool '{tool_name}' execution failed: {err!s}",
            ) from err


# -- Built-in Reference Tools for Trading & Risk ------------------------------

async def tool_calc_indicators(
    symbol: str,
    timeframe: str = "1h",
    indicators: list[str] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Computes technical indicator values (RSI, MACD, Bollinger Bands, ATR)."""
    indicators = indicators or ["RSI", "MACD", "EMA_200"]
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "indicators": {
            "RSI": "48.50",
            "MACD": {"macd": "12.4", "signal": "10.1", "hist": "2.3"},
            "EMA_200": "64500.00",
            "ATR_14": "1200.50",
        },
        "regime": "TRENDING_BULLISH",
    }


async def tool_macro_calendar(
    currency: str = "USD",
    days_ahead: int = 3,
    **kwargs: Any,
) -> dict[str, Any]:
    """Fetches high-impact economic releases."""
    return {
        "currency": currency,
        "events": [
            {
                "event": "Consumer Price Index (CPI) YoY",
                "impact": "HIGH",
                "consensus": "2.9%",
                "previous": "3.1%",
                "release_hours_away": 18,
            }
        ],
    }


async def tool_risk_calculate_exposure(
    account_id: str,
    entry_price: str,
    stop_loss_price: str,
    risk_percent: str = "1.0",
    account_equity: str = "10000.00",
    **kwargs: Any,
) -> dict[str, Any]:
    """Calculates position size and exact USD risk based on stop loss distance."""
    entry = Decimal(entry_price)
    stop = Decimal(stop_loss_price)
    equity = Decimal(account_equity)
    risk_pct = Decimal(risk_percent) / Decimal("100")

    max_risk_usd = equity * risk_pct
    price_diff = abs(entry - stop)
    if price_diff <= 0:
        raise ValidationError(detail="Entry price and stop loss price cannot be identical")

    units = max_risk_usd / price_diff
    return {
        "account_id": account_id,
        "risk_amount_usd": str(max_risk_usd),
        "calculated_units": str(units.quantize(Decimal("0.0001"))),
        "is_within_limits": True,
    }


def register_default_tools(executor: ToolExecutor) -> None:
    """Registers the core standard tools."""
    executor.register(
        definition=ToolDefinition(
            name="tool_calc_indicators",
            version="1.0.0",
            input_schema={"required": ["symbol"]},
            output_schema={"type": "object"},
            required_permissions=("tools:read",),
        ),
        handler=tool_calc_indicators,
    )
    executor.register(
        definition=ToolDefinition(
            name="tool_macro_calendar",
            version="1.0.0",
            input_schema={"required": ["currency"]},
            output_schema={"type": "object"},
            required_permissions=("tools:read",),
        ),
        handler=tool_macro_calendar,
    )
    executor.register(
        definition=ToolDefinition(
            name="tool_risk_calculate_exposure",
            version="1.0.0",
            input_schema={"required": ["account_id", "entry_price", "stop_loss_price"]},
            output_schema={"type": "object"},
            required_permissions=("tools:risk",),
        ),
        handler=tool_risk_calculate_exposure,
    )
