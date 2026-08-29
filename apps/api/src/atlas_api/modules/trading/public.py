"""The trading module's only legal import surface (docs/module-conventions.md)."""

from atlas_api.modules.trading.router import build_trading_module

__all__ = ["build_trading_module"]
