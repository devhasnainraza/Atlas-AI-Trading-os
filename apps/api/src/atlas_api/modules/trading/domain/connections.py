"""Domain entities and business rules for venue connections and accounts (Spec 03 US1, FR-004..FR-011).

Invariants enforced here:
- No venue connection stores credential secrets — only a reference ID (FR-008).
- The granted capability matrix is the narrower of the adapter's declared capabilities
  and the venue-verified permissions (FR-005). If permissions are read-only, trading
  capabilities are stripped.
- Transitions between connection health states are tracked with sanitized reasons (FR-004).
- All balance, equity, and margin values are Decimal — floats are banned (Constitution X, T007).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import uuid4

from atlas_venues.enums import AccountViewState, VenueEnvironment
from atlas_venues.models import Capabilities
from atlas_venues.precision import ZERO


class ConnectionHealth(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    EXPIRED = "expired"
    FAILED = "failed"
    QUARANTINED = "quarantined"


@dataclass(frozen=True, slots=True)
class VenueAccount:
    """An account exposed by a venue connection."""

    id: str
    connection_id: str
    user_id: str
    venue_account_ref: str
    environment: VenueEnvironment
    base_currency: str
    balance: Decimal
    equity: Decimal
    margin_used: Decimal | None = None
    margin_available: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    leverage: Decimal | None = None
    view_state: AccountViewState = AccountViewState.LIVE
    synced_at: datetime | None = None

    def __post_init__(self) -> None:
        for name in ("balance", "equity"):
            val = getattr(self, name)
            if not isinstance(val, Decimal):
                raise TypeError(f"VenueAccount.{name} must be Decimal, got {type(val).__name__}")
        for opt in ("margin_used", "margin_available", "unrealized_pnl", "leverage"):
            opt_val = getattr(self, opt)
            if opt_val is not None and not isinstance(opt_val, Decimal):
                raise TypeError(f"VenueAccount.{opt} must be Decimal or None, got {type(opt_val).__name__}")


@dataclass(frozen=True, slots=True)
class VenueConnection:
    """A user's authenticated link to one venue. Contains zero secret material."""

    id: str
    user_id: str
    venue_code: str
    label: str
    environment: VenueEnvironment
    credential_id: str
    granted_capabilities: Capabilities
    capability_version: int = 1
    health: ConnectionHealth = ConnectionHealth.HEALTHY
    health_reason: str | None = None
    routing_hold: bool = False
    last_contact_at: datetime | None = None
    last_verified_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    disconnected_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        user_id: str,
        venue_code: str,
        label: str,
        environment: VenueEnvironment,
        credential_id: str,
        granted_capabilities: Capabilities,
        connection_id: str | None = None,
        health: ConnectionHealth = ConnectionHealth.HEALTHY,
        health_reason: str | None = None,
        now: datetime | None = None,
    ) -> VenueConnection:
        created = now or datetime.now(UTC)
        return cls(
            id=connection_id or str(uuid4()),
            user_id=user_id,
            venue_code=venue_code,
            label=label,
            environment=environment,
            credential_id=credential_id,
            granted_capabilities=granted_capabilities,
            health=health,
            health_reason=health_reason,
            last_verified_at=created if health == ConnectionHealth.HEALTHY else None,
            created_at=created,
        )

    def mark_healthy(self, verified_caps: Capabilities, now: datetime | None = None) -> VenueConnection:
        t = now or datetime.now(UTC)
        return replace(
            self,
            health=ConnectionHealth.HEALTHY,
            health_reason=None,
            granted_capabilities=verified_caps,
            last_verified_at=t,
            last_contact_at=t,
        )

    def mark_degraded(self, reason: str, now: datetime | None = None) -> VenueConnection:
        t = now or datetime.now(UTC)
        return replace(
            self,
            health=ConnectionHealth.DEGRADED,
            health_reason=reason,
            last_contact_at=t,
        )

    def mark_failed(self, reason: str, now: datetime | None = None) -> VenueConnection:
        t = now or datetime.now(UTC)
        return replace(
            self,
            health=ConnectionHealth.FAILED,
            health_reason=reason,
            last_contact_at=t,
        )

    def mark_expired(self, reason: str, now: datetime | None = None) -> VenueConnection:
        t = now or datetime.now(UTC)
        return replace(
            self,
            health=ConnectionHealth.EXPIRED,
            health_reason=reason,
            last_contact_at=t,
        )

    def mark_quarantined(self, reason: str, now: datetime | None = None) -> VenueConnection:
        """Quarantine connection: stops order routing and activates reconciliation (FR-011)."""
        t = now or datetime.now(UTC)
        return replace(
            self,
            health=ConnectionHealth.QUARANTINED,
            health_reason=reason,
            routing_hold=True,
            last_contact_at=t,
        )

    def disconnect(self, now: datetime | None = None) -> VenueConnection:
        t = now or datetime.now(UTC)
        return replace(
            self,
            disconnected_at=t,
            routing_hold=True,
        )


def intersect_capabilities(
    declared: Capabilities,
    granted_permissions: Mapping[str, bool] | set[str] | None,
) -> Capabilities:
    """Compute the narrower of declared ∧ granted permissions (FR-005).

    If the credential grants read-only access (no trade permission), all execution-bearing
    capabilities are cleared so the connection cannot be selected for routing.
    """
    if granted_permissions is None:
        return declared

    # Determine if trade/execution is granted
    can_trade = True
    if isinstance(granted_permissions, Mapping):
        can_trade = granted_permissions.get("can_trade", True) and not granted_permissions.get("read_only", False)
    elif isinstance(granted_permissions, set):
        if "trade" not in granted_permissions and "orders" not in granted_permissions:
            can_trade = False

    if can_trade:
        return declared

    # Read-only key: strip execution capabilities
    return replace(
        declared,
        order_types=frozenset(),
        supports_amend=False,
        supports_cancel=False,
        supports_close_position=False,
        supports_stop_loss_take_profit=False,
        supports_short_selling=False,
        notes=(declared.notes + " [READ-ONLY: Trading disabled per credential permissions]").strip(),
    )


__all__ = [
    "AccountViewState",
    "ConnectionHealth",
    "VenueAccount",
    "VenueConnection",
    "intersect_capabilities",
]
