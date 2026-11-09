"""Venue adapter implementations.

Every adapter in this package implements :class:`atlas_venues.protocol.VenueAdapter` and is
verified by the shared conformance suite. :mod:`atlas_venues.adapters.paper` is the reference
implementation: it is fully deterministic, needs no network, and is what the conformance suite
itself is validated against.
"""

from atlas_venues.adapters.binance import (
    BINANCE_CAPABILITIES,
    BINANCE_VENUE_CODE,
    BinanceAdapter,
)
from atlas_venues.adapters.bybit import (
    BYBIT_CAPABILITIES,
    BYBIT_VENUE_CODE,
    BybitAdapter,
)
from atlas_venues.adapters.ibkr import (
    IBKR_CAPABILITIES,
    IBKR_VENUE_CODE,
    IbkrAdapter,
)
from atlas_venues.adapters.mt5 import (
    MT5_CAPABILITIES,
    MT5_VENUE_CODE,
    Mt5Adapter,
)
from atlas_venues.adapters.oanda import (
    OANDA_CAPABILITIES,
    OANDA_VENUE_CODE,
    OandaAdapter,
)
from atlas_venues.adapters.paper import (
    PAPER_CAPABILITIES,
    PAPER_VENUE_CODE,
    PaperAdapter,
    PaperEngine,
    PaperFillModel,
)

__all__ = [
    "BINANCE_CAPABILITIES",
    "BINANCE_VENUE_CODE",
    "BYBIT_CAPABILITIES",
    "BYBIT_VENUE_CODE",
    "IBKR_CAPABILITIES",
    "IBKR_VENUE_CODE",
    "MT5_CAPABILITIES",
    "MT5_VENUE_CODE",
    "OANDA_CAPABILITIES",
    "OANDA_VENUE_CODE",
    "PAPER_CAPABILITIES",
    "PAPER_VENUE_CODE",
    "BinanceAdapter",
    "BybitAdapter",
    "IbkrAdapter",
    "Mt5Adapter",
    "OandaAdapter",
    "PaperAdapter",
    "PaperEngine",
    "PaperFillModel",
]

