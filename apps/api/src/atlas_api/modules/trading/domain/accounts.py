"""Account projection and view-state derivation (Spec 03 US3, T063; FR-017..020).

Enforces:
- View-state derivation: synced_at is null ⇒ unknown; age > freshness_target ⇒ stale with age;
  else live (FR-019).
- Out-of-order protection: older updates never overwrite newer venue state (T062).
- Zero float money (Constitution X).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from atlas_venues.enums import AccountViewState, VenueEnvironment
from atlas_venues.models import AccountSnapshot


def derive_account_view_state(
    synced_at: datetime | None,
    now: datetime | None = None,
    freshness_target_seconds: float = 30.0,
) -> tuple[AccountViewState, float | None]:
    """Derive account view state and age from sync timestamp (FR-019).

    Never-synced ⇒ unknown (age is None).
    Older than freshness target ⇒ stale with age.
    Within freshness target ⇒ live with age.
    """
    if synced_at is None:
        return AccountViewState.UNKNOWN, None

    current_time = now or datetime.now(UTC)
    age_seconds = max(0.0, (current_time - synced_at).total_seconds())

    if age_seconds > freshness_target_seconds:
        return AccountViewState.STALE, age_seconds

    return AccountViewState.LIVE, age_seconds


@dataclass
class AccountProjection:
    """Venue-authoritative account projection."""

    connection_id: str
    user_id: str
    venue_account_ref: str
    environment: VenueEnvironment
    base_currency: str
    balance: Decimal
    equity: Decimal
    available_margin: Decimal | None
    used_margin: Decimal | None
    unrealized_pnl: Decimal | None
    synced_at: datetime | None
    view_state: AccountViewState = AccountViewState.UNKNOWN
    age_seconds: float | None = None

    @classmethod
    def create_unknown(
        cls,
        *,
        connection_id: str,
        user_id: str,
        venue_account_ref: str,
        environment: VenueEnvironment = VenueEnvironment.DEMO,
        base_currency: str = "USD",
    ) -> AccountProjection:
        return cls(
            connection_id=connection_id,
            user_id=user_id,
            venue_account_ref=venue_account_ref,
            environment=environment,
            base_currency=base_currency,
            balance=Decimal("0.00"),
            equity=Decimal("0.00"),
            available_margin=None,
            used_margin=None,
            unrealized_pnl=None,
            synced_at=None,
            view_state=AccountViewState.UNKNOWN,
            age_seconds=None,
        )

    def apply_snapshot(
        self,
        snapshot: AccountSnapshot,
        now: datetime | None = None,
        freshness_target_seconds: float = 30.0,
    ) -> bool:
        """Apply a new snapshot. Returns True if applied, False if rejected as out-of-order."""
        # Out-of-order guard (T062): older venue timestamps cannot overwrite newer state
        if self.synced_at is not None and snapshot.venue_time < self.synced_at:
            return False

        current_time = now or datetime.now(UTC)
        view_state, age = derive_account_view_state(
            snapshot.venue_time, current_time, freshness_target_seconds
        )

        self.balance = snapshot.balance
        self.equity = snapshot.equity
        self.available_margin = snapshot.available_margin
        self.used_margin = snapshot.used_margin
        self.unrealized_pnl = snapshot.unrealized_pnl
        self.base_currency = snapshot.currency
        self.environment = snapshot.environment
        self.synced_at = snapshot.venue_time
        self.view_state = view_state
        self.age_seconds = age
        return True

    def mark_stale_on_failure(self, now: datetime | None = None) -> None:
        """Called when a sync attempt fails to transition view to stale."""
        current_time = now or datetime.now(UTC)
        if self.synced_at is None:
            self.view_state = AccountViewState.UNKNOWN
            self.age_seconds = None
        else:
            self.view_state = AccountViewState.STALE
            self.age_seconds = max(0.0, (current_time - self.synced_at).total_seconds())


__all__ = ["AccountProjection", "AccountViewState", "derive_account_view_state"]
