"""Position projection from venue state (Spec 03 US3, T064; FR-017, FR-020, FR-021).

Enforces:
- Venue-authoritative positions: local state is a correctable projection (FR-020).
- External position discovery: positions opened outside Atlas are imported, flagged with
  opened_externally: True, and included in exposure math (FR-017).
- Netting vs Hedging keying: netting keys on (connection_id, venue_symbol, side); hedging
  keys on venue_position_ref (plan §11).
- Out-of-order protection: older updates never overwrite newer state (T062).
- Zero float money (Constitution X).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Sequence

from atlas_venues.enums import PositionSide, VenueEnvironment
from atlas_venues.models import VenuePosition
from atlas_venues.precision import ZERO


@dataclass
class PositionProjection:
    """Venue-authoritative position projection."""

    connection_id: str
    user_id: str
    venue_symbol: str
    side: PositionSide
    quantity: Decimal
    average_entry_price: Decimal
    environment: VenueEnvironment
    venue_position_ref: str | None = None
    unrealized_pnl: Decimal | None = None
    realized_pnl: Decimal | None = None
    current_price: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    opened_externally: bool = False
    state: str = "open"  # open | closing | closed
    synced_at: datetime | None = None
    closed_at: datetime | None = None

    @property
    def exposure_notional(self) -> Decimal:
        """Total notional exposure: quantity * (current_price or average_entry_price)."""
        price = self.current_price if self.current_price is not None else self.average_entry_price
        return self.quantity * price


class PositionRegistry:
    """In-memory or repository projection registry managing position sync."""

    def __init__(self, is_hedging: bool = False) -> None:
        self.is_hedging = is_hedging
        # Key: venue_position_ref if hedging else (connection_id, venue_symbol, side)
        self._positions: dict[str | tuple[str, str, PositionSide], PositionProjection] = {}
        self._known_atlas_refs: set[str] = set()

    def register_atlas_position(self, venue_position_ref: str) -> None:
        """Track that an order originated in Atlas."""
        self._known_atlas_refs.add(venue_position_ref)

    def _key(self, pos: VenuePosition) -> str | tuple[str, str, PositionSide]:
        if self.is_hedging and pos.venue_position_ref:
            return pos.venue_position_ref
        return (pos.venue_code, pos.venue_symbol, pos.side)

    def apply_venue_position(
        self,
        connection_id: str,
        user_id: str,
        pos: VenuePosition,
    ) -> PositionProjection:
        """Project a venue position into Atlas, flagging external origin if not created by Atlas."""
        key = self._key(pos)
        existing = self._positions.get(key)

        # Out-of-order protection (T062): do not overwrite if existing is newer
        if existing and existing.synced_at and pos.venue_time < existing.synced_at:
            return existing

        is_external = True
        if pos.venue_position_ref and pos.venue_position_ref in self._known_atlas_refs:
            is_external = False
        elif existing:
            is_external = existing.opened_externally

        proj = PositionProjection(
            connection_id=connection_id,
            user_id=user_id,
            venue_symbol=pos.venue_symbol,
            side=pos.side,
            quantity=pos.quantity,
            average_entry_price=pos.average_entry_price,
            environment=pos.environment,
            venue_position_ref=pos.venue_position_ref,
            unrealized_pnl=pos.unrealized_pnl,
            current_price=pos.current_price,
            stop_loss=pos.stop_loss,
            take_profit=pos.take_profit,
            opened_externally=is_external,
            state="open",
            synced_at=pos.venue_time,
        )
        self._positions[key] = proj
        return proj

    def reconcile_snapshot(
        self,
        connection_id: str,
        user_id: str,
        venue_positions: Sequence[VenuePosition],
        reconcile_time: datetime,
    ) -> list[PositionProjection]:
        """Full reconciliation: update open positions and mark absent ones as closed."""
        seen_keys: set[str | tuple[str, str, PositionSide]] = set()
        results: list[PositionProjection] = []

        for vp in venue_positions:
            proj = self.apply_venue_position(connection_id, user_id, vp)
            seen_keys.add(self._key(vp))
            results.append(proj)

        # Mark positions no longer present at venue as closed
        for key, p in list(self._positions.items()):
            if p.connection_id == connection_id and p.state == "open" and key not in seen_keys:
                p.state = "closed"
                p.closed_at = reconcile_time

        return results

    def list_open(self, connection_id: str | None = None) -> list[PositionProjection]:
        return [
            p
            for p in self._positions.values()
            if p.state == "open" and (connection_id is None or p.connection_id == connection_id)
        ]

    def total_exposure_notional(self, connection_id: str | None = None) -> Decimal:
        """Sum of all open position notionals, including external positions (FR-017)."""
        open_pos = self.list_open(connection_id)
        total = ZERO
        for p in open_pos:
            total += p.exposure_notional
        return total


__all__ = ["PositionProjection", "PositionRegistry"]
