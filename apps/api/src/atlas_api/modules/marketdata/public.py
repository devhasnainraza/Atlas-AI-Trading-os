"""The market data module's only legal import surface (docs/module-conventions.md)."""

from atlas_api.modules.marketdata.repository.quotes import AttributedQuote
from atlas_api.modules.marketdata.router import build_marketdata_module
from atlas_api.modules.marketdata.service import MarketDataService

__all__ = [
    "AttributedQuote",
    "MarketDataService",
    "build_marketdata_module",
]

