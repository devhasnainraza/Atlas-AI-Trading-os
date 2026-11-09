"""Instrument normalization service and domain model (Spec 03 plan §5, T051).

Provides canonical ↔ venue symbol mapping, spec versions, and session state tracking.
Invariants:
- All tick sizes, quantity steps, min/max quantities, and contract sizes are strict Decimal.
- Cross-venue attribution is strictly preserved.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Sequence
from uuid import uuid4

from atlas_venues.enums import AssetClass
from atlas_venues.models import InstrumentSpec
from atlas_venues.precision import ZERO


@dataclass(frozen=True, slots=True)
class NormalizedInstrument:
    """Canonical instrument with venue-specific specifications."""

    id: str
    venue_code: str
    canonical_symbol: str
    venue_symbol: str
    asset_class: str
    base_currency: str | None
    quote_currency: str | None
    price_precision: int
    quantity_precision: int
    tick_size: Decimal
    quantity_step: Decimal
    min_quantity: Decimal
    max_quantity: Decimal | None
    min_notional: Decimal | None
    contract_size: Decimal
    max_leverage: Decimal
    session_state: str  # open, closed, pre, halted, suspended
    tradable: bool
    spec_version: int
    refreshed_at: datetime
    next_session_change_at: datetime | None = None

    def __post_init__(self) -> None:
        for name in ("tick_size", "quantity_step", "min_quantity", "contract_size", "max_leverage"):
            val = getattr(self, name)
            if not isinstance(val, Decimal):
                raise TypeError(f"NormalizedInstrument.{name} must be Decimal, got {type(val).__name__}")
            if val <= ZERO:
                raise ValueError(f"NormalizedInstrument.{name} must be positive, got {val}")


class InstrumentRegistry:
    """Thread-safe catalog of known instruments and symbol mappings."""

    def __init__(self) -> None:
        self._by_id: dict[str, NormalizedInstrument] = {}
        # (venue_code, canonical_symbol) -> instrument
        self._by_canonical: dict[tuple[str, str], NormalizedInstrument] = {}
        # (venue_code, venue_symbol) -> instrument
        self._by_venue_sym: dict[tuple[str, str], NormalizedInstrument] = {}
        self._versions: dict[tuple[str, str], int] = {}

    def register(self, spec: InstrumentSpec, *, id: str | None = None) -> NormalizedInstrument:
        """Register or update an instrument specification."""
        key = (spec.venue_code.lower(), spec.canonical_symbol.upper())
        current_version = self._versions.get(key, 0) + 1
        self._versions[key] = current_version

        instrument_id = id or str(uuid4())
        norm = NormalizedInstrument(
            id=instrument_id,
            venue_code=spec.venue_code.lower(),
            canonical_symbol=spec.canonical_symbol.upper(),
            venue_symbol=spec.venue_symbol,
            asset_class=str(spec.asset_class),
            base_currency=spec.base_currency,
            quote_currency=spec.quote_currency,
            price_precision=spec.price_precision,
            quantity_precision=spec.quantity_precision,
            tick_size=spec.tick_size,
            quantity_step=spec.quantity_step,
            min_quantity=spec.min_quantity,
            max_quantity=spec.max_quantity,
            min_notional=spec.min_notional,
            contract_size=spec.contract_size or Decimal("1"),
            max_leverage=Decimal("20") if spec.asset_class == AssetClass.FOREX else Decimal("10"),
            session_state="open",
            tradable=spec.is_tradable,
            spec_version=current_version,
            refreshed_at=datetime.now(UTC),
        )

        self._by_id[norm.id] = norm
        self._by_canonical[key] = norm
        self._by_venue_sym[(norm.venue_code, norm.venue_symbol)] = norm
        return norm

    def get_by_id(self, instrument_id: str) -> NormalizedInstrument | None:
        return self._by_id.get(instrument_id)

    def find(self, venue_code: str, symbol: str) -> NormalizedInstrument | None:
        """Look up by venue code and either canonical or venue symbol."""
        vc = venue_code.lower()
        key_can = (vc, symbol.upper())
        if key_can in self._by_canonical:
            return self._by_canonical[key_can]
        key_ven = (vc, symbol)
        return self._by_venue_sym.get(key_ven)

    def list_for_venue(
        self,
        venue_code: str,
        *,
        asset_class: str | None = None,
        query: str | None = None,
    ) -> Sequence[NormalizedInstrument]:
        results: list[NormalizedInstrument] = []
        vc = venue_code.lower()
        for norm in self._by_id.values():
            if norm.venue_code != vc:
                continue
            if asset_class and norm.asset_class.lower() != asset_class.lower():
                continue
            if query:
                q = query.upper()
                if q not in norm.canonical_symbol and q not in norm.venue_symbol.upper():
                    continue
            results.append(norm)
        return tuple(results)


__all__ = ["InstrumentRegistry", "NormalizedInstrument"]
