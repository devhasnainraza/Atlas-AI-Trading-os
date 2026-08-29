"""Trading module request/response schemas — strict validation (FR-010).

Two module-wide rules:

* Writes set ``extra="forbid"``. A typo'd field name on an order must be a 422, not a silently
  ignored instruction — ``quantiy=5`` accepted as "no quantity given" is how a wrong-sized
  order reaches a venue.
* Money and quantity cross the wire as strings and are parsed to ``Decimal``. JSON has only
  binary floats, so a bare number would already have lost precision before it arrived.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from atlas_venues.enums import AssetClass, OrderType, TimeInForce, VenueEnvironment


class VenueCapabilitiesResponse(BaseModel):
    """What a venue can do, as the adapter declares it.

    ``enabled`` is the flag verdict, kept separate from the capability list: a venue can be
    fully capable and still switched off, and the UI needs to say which.
    """

    venue_code: str
    display_name: str
    enabled: bool
    requires_sidecar: bool
    asset_classes: list[AssetClass]
    order_types: list[OrderType]
    time_in_force: list[TimeInForce]
    environments: list[VenueEnvironment]
    supports_amend: bool
    supports_cancel: bool
    supports_close_position: bool
    supports_streaming_quotes: bool
    supports_streaming_account: bool
    supports_historical_bars: bool
    supports_fractional_quantity: bool
    supports_client_order_id: bool
    supports_stop_loss_take_profit: bool
    supports_short_selling: bool
    notes: str | None = None


class VenueListResponse(BaseModel):
    venues: list[VenueCapabilitiesResponse]


class RiskRuleDescriptor(BaseModel):
    """One rule the gate evaluates, exposed so a refusal can be explained before it happens."""

    code: str
    description: str


class RiskRulesResponse(BaseModel):
    """The full rule set, in evaluation order."""

    rules: list[RiskRuleDescriptor]


class LiveTradingStatusResponse(BaseModel):
    """Whether real-money orders can leave this deployment at all.

    Surfaced as a first-class endpoint rather than buried in a config dump: a user who thinks
    they are trading live while the transmitter is off has a silent failure, and one who thinks
    the opposite has a much worse one.
    """

    live_orders_enabled: bool
    require_step_up_for_live: bool
    intent_ttl_seconds: int
    submit_timeout_seconds: float
    reason: str


class PaperResetRequest(BaseModel):
    """Reset a paper book. Audit history is not affected (FR-051)."""

    model_config = ConfigDict(extra="forbid")

    starting_balance: Decimal | None = Field(
        default=None,
        gt=0,
        description="New starting balance as a decimal string; omit to reuse the configured one.",
    )


class PaperResetResponse(BaseModel):
    venue_account_ref: str
    starting_balance: Decimal
    reset_count: int


__all__ = [
    "LiveTradingStatusResponse",
    "PaperResetRequest",
    "PaperResetResponse",
    "RiskRuleDescriptor",
    "RiskRulesResponse",
    "VenueCapabilitiesResponse",
    "VenueListResponse",
]
