"""The market data module's only legal import surface (docs/module-conventions.md)."""

from atlas_api.modules.marketdata.router import build_marketdata_module

__all__ = ["build_marketdata_module"]
