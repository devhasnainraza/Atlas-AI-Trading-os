"""The ``VenueAdapter`` protocol — the only contract Atlas trading code knows (plan §2).

Every venue (MT5, OANDA, Binance, Bybit, IBKR, and the paper simulator) is reachable *only*
through this protocol. Domain code, the risk gate, and both API modules import this file and
never a venue SDK, which is what keeps venue-specific behaviour from leaking into the parts
of the system that decide whether an order is safe to send.

Two rules bind every implementation:

1. **Ambiguity is raised, not guessed.** When a call's effect at the venue is unknown, raise
   :class:`atlas_venues.errors.AmbiguousOutcomeError`. Never return a plausible result
   (FR-030).
2. **Credentials are borrowed, never held.** Adapters fetch material per operation through
   :mod:`atlas_venues.credentials` and must not cache it on the instance (FR-008).

Every implementation is verified against the shared conformance suite
(``shared/tests/venues/conformance/``); an adapter that passes it is substitutable everywhere.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable

from atlas_venues.errors import ErrorClass
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
    VenueOrder,
    VenuePosition,
    VenueTimeOffset,
)


@runtime_checkable
class VenueAdapter(Protocol):
    """The venue-agnostic contract (plan §2).

    Grouped into five areas: discovery, market data, account, execution, and semantics.
    Adapters raise :class:`atlas_venues.errors.UnsupportedCapabilityError` for anything their
    :meth:`capabilities` does not advertise, so an unsupported call fails loudly at the
    boundary instead of silently doing something approximate.
    """

    # -- Discovery ---------------------------------------------------------------------

    def capabilities(self) -> Capabilities:
        """What this venue supports. Pure and synchronous — must not perform I/O."""
        ...

    async def verify_permissions(self) -> tuple[bool, str]:
        """Prove the stored credentials still work and carry the scopes we need.

        Returns ``(ok, detail)``. Called at connection time and on a schedule; a failure here
        moves the connection to ``expired`` or ``failed`` rather than surfacing at the moment
        an order is being sent (FR-011).
        """
        ...

    async def instruments(self) -> Sequence[InstrumentSpec]:
        """The venue's full tradable universe, with its precision rules."""
        ...

    async def instrument(self, symbol: str) -> InstrumentSpec:
        """One instrument by venue or canonical symbol."""
        ...

    # -- Market data -------------------------------------------------------------------

    async def quote(self, symbols: Sequence[str]) -> Sequence[QuoteTick]:
        """Current top of book. Respects ``max_symbols_per_quote_call``."""
        ...

    async def bars(
        self,
        symbol: str,
        interval: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> Sequence[Bar]:
        """Closed candles only, oldest first. The in-progress candle is never returned."""
        ...

    def stream_quotes(self, symbols: Sequence[str]) -> AsyncIterator[QuoteTick]:
        """Live quotes. The iterator reconnects internally and signals gaps to the caller."""
        ...

    # -- Account -----------------------------------------------------------------------

    async def account_snapshot(self) -> AccountSnapshot:
        """Balances and margin as the venue reports them right now."""
        ...

    async def positions(self) -> Sequence[VenuePosition]:
        """All open positions, including any opened outside Atlas (FR-021)."""
        ...

    async def open_orders(self) -> Sequence[VenueOrder]:
        """All working orders, including any placed outside Atlas."""
        ...

    def stream_account(self) -> AsyncIterator[AccountSnapshot | VenuePosition | VenueOrder]:
        """Push updates for balances, positions, and orders where the venue offers them."""
        ...

    # -- Execution ---------------------------------------------------------------------

    async def submit(self, request: SubmitRequest) -> SubmitResult:
        """Transmit one order.

        The caller has already run the risk gate and recorded a submission ledger row keyed
        by ``request.client_order_id``; this method performs exactly one transmission attempt
        and does not retry internally. On an unknown outcome it must raise
        :class:`atlas_venues.errors.AmbiguousOutcomeError` (FR-026, FR-030).
        """
        ...

    async def amend(self, request: AmendRequest) -> SubmitResult:
        """Modify a working order. Only for venues advertising ``supports_amend``."""
        ...

    async def cancel(
        self, venue_order_ref: str, *, client_order_id: str | None = None
    ) -> SubmitResult:
        """Cancel a working order. Cancelling an already-terminal order is not an error."""
        ...

    async def close_position(
        self, venue_position_ref: str, *, quantity: object | None = None
    ) -> SubmitResult:
        """Flatten a position, wholly or partly. Only where ``supports_close_position``."""
        ...

    async def order_status(
        self, *, venue_order_ref: str | None = None, client_order_id: str | None = None
    ) -> VenueOrder:
        """Look up one order — the resolution path out of ``unresolved`` (FR-030).

        Lookup by ``client_order_id`` is what lets us discover whether an ambiguous
        submission actually reached the venue, without sending anything new.
        """
        ...

    # -- Semantics ---------------------------------------------------------------------

    async def server_time_offset(self) -> VenueTimeOffset:
        """Measured clock skew, applied to every venue timestamp before comparison."""
        ...

    def rate_limit_model(self) -> RateLimitModel:
        """How this venue meters us. Pure and synchronous."""
        ...

    def classify_error(self, exc: BaseException) -> ErrorClass:
        """Map a venue-native exception onto the shared taxonomy.

        Must be conservative: anything that *could* have reached the venue is
        :attr:`ErrorClass.AMBIGUOUS`, never ``RETRYABLE_TRANSIENT``.
        """
        ...


__all__ = ["VenueAdapter"]
