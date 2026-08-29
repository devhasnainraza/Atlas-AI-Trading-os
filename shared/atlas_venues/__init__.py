"""atlas_venues — the venue-agnostic trading abstraction (Spec 03).

Every venue Atlas can trade — MT5, OANDA, Binance, Bybit, IBKR, and the paper simulator —
is reached through the single :class:`~atlas_venues.protocol.VenueAdapter` protocol. Trading
domain code imports this package and never a venue SDK, so venue-specific behaviour cannot
leak into the code that decides whether an order is safe to send.

Three invariants hold across every adapter, and each is asserted by the shared conformance
suite:

* **Decimal only.** Prices and quantities are ``Decimal``; floats are rejected at the
  boundary, not rounded (:mod:`atlas_venues.precision`).
* **Ambiguity is raised.** An unknown submission outcome raises
  :class:`~atlas_venues.errors.AmbiguousOutcomeError` and is never rendered as a fill or a
  rejection (FR-030).
* **Credentials are borrowed.** Material is fetched per operation and never cached on an
  adapter (:mod:`atlas_venues.credentials`, FR-008).
"""

from atlas_venues.enums import (
    AccountViewState,
    AssetClass,
    ConnectionHealth,
    DataFreshness,
    DiscrepancyClass,
    OrderSide,
    OrderState,
    OrderType,
    PositionSide,
    TimeInForce,
    VenueEnvironment,
)
from atlas_venues.errors import (
    AmbiguousOutcomeError,
    ErrorClass,
    PermissionDeniedError,
    RateLimitedError,
    TerminalRejectionError,
    TransientVenueError,
    UnsupportedCapabilityError,
    VenueError,
)
from atlas_venues.models import (
    AccountSnapshot,
    AmendRequest,
    Bar,
    Capabilities,
    InstrumentSpec,
    QuoteTick,
    RateLimitModel,
    SubmitRequest,
    SubmitResult,
    VenueFill,
    VenueOrder,
    VenuePosition,
    VenueTimeOffset,
)
from atlas_venues.protocol import VenueAdapter
from atlas_venues.registry import AdapterContext, VenueRegistry, registry

__all__ = [
    "AccountSnapshot",
    "AccountViewState",
    "AdapterContext",
    "AmbiguousOutcomeError",
    "AmendRequest",
    "AssetClass",
    "Bar",
    "Capabilities",
    "ConnectionHealth",
    "DataFreshness",
    "DiscrepancyClass",
    "ErrorClass",
    "InstrumentSpec",
    "OrderSide",
    "OrderState",
    "OrderType",
    "PermissionDeniedError",
    "PositionSide",
    "QuoteTick",
    "RateLimitModel",
    "RateLimitedError",
    "SubmitRequest",
    "SubmitResult",
    "TerminalRejectionError",
    "TimeInForce",
    "TransientVenueError",
    "UnsupportedCapabilityError",
    "VenueAdapter",
    "VenueEnvironment",
    "VenueError",
    "VenueFill",
    "VenueOrder",
    "VenuePosition",
    "VenueRegistry",
    "VenueTimeOffset",
    "registry",
]
