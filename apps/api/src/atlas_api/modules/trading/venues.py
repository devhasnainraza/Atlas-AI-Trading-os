"""Built-in venue registration (T012 wiring, US1, US6).

The registry maps a venue code to a factory. Registration is where the platform decides which
venues *could* exist; the feature flags in :class:`VenueCatalogService` decide which ones a
user may actually reach. Keeping those separate means turning a venue off is a flag flip, not
a deploy.

Paper is the only venue registered here. The five real venues (MT5, OANDA, Binance, Bybit,
IBKR) each need their live wire protocol verified against current vendor documentation before
an adapter is written — inventing request shapes from memory is how an order gets sent with
the wrong side. Each lands as its own module under ``atlas_venues/adapters/`` and passes the
same conformance suite paper already passes; nothing here changes when they do.
"""

from __future__ import annotations

from decimal import Decimal

from atlas_venues.adapters.paper import (
    PAPER_CAPABILITIES,
    PAPER_VENUE_CODE,
    PaperAdapter,
    PaperEngine,
    PaperFillModel,
)
from atlas_venues.enums import VenueEnvironment
from atlas_venues.protocol import VenueAdapter
from atlas_venues.registry import AdapterContext, VenueRegistry
from atlas_venues.timing import Clock, SystemClock

#: Flag key per venue. Absent from the map means "not gated" — which never applies, so a new
#: venue must add its key here before it can be reached.
VENUE_FLAG_KEYS: dict[str, str] = {
    PAPER_VENUE_CODE: "venue.paper.enabled",
    "mt5": "venue.mt5.enabled",
    "oanda": "venue.oanda.enabled",
    "binance": "venue.binance.enabled",
    "bybit": "venue.bybit.enabled",
    "ibkr": "venue.ibkr.enabled",
}

#: Safe default per venue when the flag store has no opinion. Paper is on because it cannot
#: lose money; everything that can is off (Constitution IX, FR-046).
VENUE_FLAG_DEFAULTS: dict[str, bool] = {
    PAPER_VENUE_CODE: True,
    "mt5": False,
    "oanda": False,
    "binance": False,
    "bybit": False,
    "ibkr": False,
}


class PaperBookStore:
    """One :class:`PaperEngine` per paper venue account.

    Engines are shared across adapters bound to the same account so two browser tabs see one
    consistent book rather than two divergent simulations.
    """

    def __init__(
        self,
        *,
        starting_balance: Decimal = Decimal("100000"),
        slippage_bps: Decimal = Decimal("1"),
        commission_bps: Decimal = Decimal("0"),
        clock: Clock | None = None,
    ) -> None:
        for name, value in (
            ("starting_balance", starting_balance),
            ("slippage_bps", slippage_bps),
            ("commission_bps", commission_bps),
        ):
            if not isinstance(value, Decimal):
                raise TypeError(f"{name} must be Decimal, got {type(value).__name__}")
        self._starting_balance = starting_balance
        self._fill_model = PaperFillModel(slippage_bps=slippage_bps, commission_bps=commission_bps)
        self._clock = clock or SystemClock()
        self._engines: dict[str, PaperEngine] = {}
        self._reset_counts: dict[str, int] = {}

    def engine(self, account_ref: str) -> PaperEngine:
        engine = self._engines.get(account_ref)
        if engine is None:
            engine = PaperEngine(
                account_ref=account_ref,
                starting_balance=self._starting_balance,
                fill_model=self._fill_model,
                clock=self._clock,
            )
            self._engines[account_ref] = engine
        return engine

    def reset(self, account_ref: str, *, starting_balance: Decimal | None = None) -> int:
        """Reset a book and return the new reset count (FR-051).

        Audit history lives outside the engine, so a reset clears the simulated book without
        erasing the record that the reset happened.
        """
        if starting_balance is not None and not isinstance(starting_balance, Decimal):
            raise TypeError("starting_balance must be Decimal")
        self.engine(account_ref).reset(starting_balance=starting_balance)
        self._reset_counts[account_ref] = self._reset_counts.get(account_ref, 0) + 1
        return self._reset_counts[account_ref]

    def reset_count(self, account_ref: str) -> int:
        return self._reset_counts.get(account_ref, 0)

    def known_accounts(self) -> tuple[str, ...]:
        return tuple(sorted(self._engines))


def register_builtin_venues(
    registry: VenueRegistry,
    *,
    books: PaperBookStore,
    clock: Clock | None = None,
) -> VenueRegistry:
    """Register every adapter this build ships. Idempotent per venue code."""

    def make_paper(context: AdapterContext) -> VenueAdapter:
        if context.environment is not VenueEnvironment.PAPER:
            # The registry already checks the declared environment set; this is the belt to
            # that braces, because a paper adapter reached in a live context would be a
            # simulator quietly standing in for a real venue.
            raise ValueError("paper venue serves only the paper environment")
        if not context.venue_account_ref:
            raise ValueError("a paper connection needs a venue_account_ref to key its book")
        return PaperAdapter(context, books.engine(context.venue_account_ref), clock=clock)

    if not registry.is_registered(PAPER_VENUE_CODE):
        registry.register(PAPER_VENUE_CODE, make_paper, PAPER_CAPABILITIES)
    return registry


__all__ = [
    "VENUE_FLAG_DEFAULTS",
    "VENUE_FLAG_KEYS",
    "PaperBookStore",
    "register_builtin_venues",
]
