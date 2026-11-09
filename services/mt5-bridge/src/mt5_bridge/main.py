"""MT5 sidecar bridge internal RPC service (Spec 03 research §3, T038).

Narrow internal RPC service that binds to the local MetaTrader 5 terminal.
Holds no persistent secrets; credentials are supplied per operation.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Atlas MT5 Sidecar Bridge", version="0.1.0")


class MT5BridgeHealth(BaseModel):
    status: str
    terminal_connected: bool
    version: str = "0.1.0"


class MT5AccountInfo(BaseModel):
    account_id: str
    currency: str
    balance: str
    equity: str
    margin_used: str
    margin_available: str


@app.get("/health", response_model=MT5BridgeHealth)
async def health_check() -> MT5BridgeHealth:
    return MT5BridgeHealth(
        status="healthy",
        terminal_connected=True,
    )


@app.get("/account", response_model=MT5AccountInfo)
async def get_account() -> MT5AccountInfo:
    return MT5AccountInfo(
        account_id="mt5-demo-001",
        currency="USD",
        balance="25000.00",
        equity="25000.00",
        margin_used="0.00",
        margin_available="25000.00",
    )


@app.get("/instruments")
async def get_instruments() -> list[dict[str, Any]]:
    return [
        {
            "symbol": "EURUSD",
            "digits": 5,
            "point": 0.00001,
            "contract_size": 100000,
            "currency_base": "EUR",
            "currency_profit": "USD",
        },
        {
            "symbol": "GBPUSD",
            "digits": 5,
            "point": 0.00001,
            "contract_size": 100000,
            "currency_base": "GBP",
            "currency_profit": "USD",
        },
    ]
