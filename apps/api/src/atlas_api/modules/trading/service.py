"""Trading service layer — the only layer that touches repositories, adapters, and events.

What lives here in this slice: the venue catalog (flag-gated), the risk-rule catalog, live
transmission status, and paper-book resets. Order intent/confirm/submit arrive with US4 and go
through the same seams.

The catalog is the interesting part. ``registry`` says which venues a build *ships*; the flags
say which ones a deployment *permits*. Keeping those apart means an emergency shutdown of one
venue is a flag flip, and a venue that is off still reports honest capabilities to the UI
instead of vanishing — a user whose venue silently disappeared would reasonably assume the
platform is broken.
"""

from __future__ import annotations

from decimal import Decimal

from atlas_api.modules.trading.domain.risk import rule_descriptors
from atlas_api.modules.trading.errors import CapabilityNotPermittedError
from atlas_api.modules.trading.schemas import (
    LiveTradingStatusResponse,
    PaperResetResponse,
    RiskRuleDescriptor,
    RiskRulesResponse,
    VenueCapabilitiesResponse,
    VenueListResponse,
)
from atlas_api.modules.trading.settings import TradingSettings
from atlas_api.modules.trading.venues import (
    VENUE_FLAG_DEFAULTS,
    VENUE_FLAG_KEYS,
    PaperBookStore,
)
from atlas_core.feature_flags import FeatureFlags
from atlas_events import EventEnvelope, InMemoryEventBus, InMemoryOutbox
from atlas_venues.adapters.paper import PAPER_VENUE_CODE
from atlas_venues.models import Capabilities
from atlas_venues.registry import VenueRegistry


class VenueCatalogService:
    """Reads the registry, applies the flags, and reports both."""

    def __init__(self, registry: VenueRegistry, flags: FeatureFlags) -> None:
        self._registry = registry
        self._flags = flags

    def is_enabled(self, venue_code: str) -> bool:
        """Flag verdict for one venue.

        An unmapped venue code is disabled. A venue whose flag key nobody added is a venue
        nobody decided to allow, and the safe reading of "no decision" is "no".
        """
        code = venue_code.lower()
        key = VENUE_FLAG_KEYS.get(code)
        if key is None:
            return False
        return self._flags.is_enabled(key, default=VENUE_FLAG_DEFAULTS.get(code, False))

    def require_enabled(self, venue_code: str) -> None:
        """Raise the taxonomy error rather than a bare 403, so the client can act on it."""
        if not self.is_enabled(venue_code):
            raise CapabilityNotPermittedError(
                f"Venue '{venue_code}' is not enabled in this deployment.",
                internal_context={"venue_code": venue_code},
            )

    def list_venues(self) -> VenueListResponse:
        return VenueListResponse(
            venues=[self._to_response(caps) for caps in self._registry.all_capabilities()]
        )

    def _to_response(self, caps: Capabilities) -> VenueCapabilitiesResponse:
        return VenueCapabilitiesResponse(
            venue_code=caps.venue_code,
            display_name=caps.display_name,
            enabled=self.is_enabled(caps.venue_code),
            requires_sidecar=caps.requires_sidecar,
            # Sorted so the payload is stable across runs — an unordered set would make the
            # response body differ between processes and break response snapshots.
            asset_classes=sorted(caps.asset_classes),
            order_types=sorted(caps.order_types),
            time_in_force=sorted(caps.time_in_force),
            environments=sorted(caps.environments),
            supports_amend=caps.supports_amend,
            supports_cancel=caps.supports_cancel,
            supports_close_position=caps.supports_close_position,
            supports_streaming_quotes=caps.supports_streaming_quotes,
            supports_streaming_account=caps.supports_streaming_account,
            supports_historical_bars=caps.supports_historical_bars,
            supports_fractional_quantity=caps.supports_fractional_quantity,
            supports_client_order_id=caps.supports_client_order_id,
            supports_stop_loss_take_profit=caps.supports_stop_loss_take_profit,
            supports_short_selling=caps.supports_short_selling,
            notes=caps.notes,
        )


class RiskCatalogService:
    """Exposes the rule set the gate will evaluate, before anything is submitted."""

    def rules(self) -> RiskRulesResponse:
        return RiskRulesResponse(
            rules=[
                RiskRuleDescriptor(code=code, description=description)
                for code, description in rule_descriptors()
            ]
        )


class LiveTradingStatusService:
    """Answers 'can a real order leave this deployment right now?'."""

    def __init__(self, settings: TradingSettings, flags: FeatureFlags) -> None:
        self._settings = settings
        self._flags = flags

    def status(self) -> LiveTradingStatusResponse:
        # Two independent switches, and both must be on. Config alone is not enough: a flag
        # can be flipped in seconds during an incident, a redeploy cannot.
        flag_on = self._flags.is_enabled("trading.live_orders.enabled", default=False)
        settings_on = self._settings.live_orders_enabled
        enabled = flag_on and settings_on

        if enabled:
            reason = "Live order transmission is enabled."
        elif not settings_on and not flag_on:
            reason = "Live order transmission is disabled by configuration and by feature flag."
        elif not settings_on:
            reason = "Live order transmission is disabled by configuration."
        else:
            reason = "Live order transmission is disabled by feature flag."

        return LiveTradingStatusResponse(
            live_orders_enabled=enabled,
            require_step_up_for_live=self._settings.require_step_up_for_live,
            intent_ttl_seconds=self._settings.intent_ttl_seconds,
            submit_timeout_seconds=self._settings.submit_timeout_seconds,
            reason=reason,
        )


class PaperAccountService:
    """Resets paper books and records that the reset happened."""

    def __init__(
        self,
        books: PaperBookStore,
        settings: TradingSettings,
        outbox: InMemoryOutbox,
        bus: InMemoryEventBus,
    ) -> None:
        self._books = books
        self._settings = settings
        self._outbox = outbox
        self._bus = bus

    async def reset(
        self, venue_account_ref: str, *, starting_balance: Decimal | None = None
    ) -> PaperResetResponse:
        balance = starting_balance or self._settings.paper_starting_balance
        reset_count = self._books.reset(venue_account_ref, starting_balance=balance)
        self._outbox.add(
            EventEnvelope(
                event_type="atlas.trading.paper.reset",
                producer="atlas-api.trading",
                payload={
                    "connection_id": venue_account_ref,
                    # Serialized as a string: the event log must carry the exact decimal the
                    # book was set to, and JSON numbers are binary floats.
                    "starting_balance": str(balance),
                    "reset_count": reset_count,
                },
            )
        )
        await self._outbox.relay(self._bus)
        return PaperResetResponse(
            venue_account_ref=venue_account_ref,
            starting_balance=balance,
            reset_count=reset_count,
        )

    def paper_venue_code(self) -> str:
        return PAPER_VENUE_CODE


__all__ = [
    "LiveTradingStatusService",
    "PaperAccountService",
    "RiskCatalogService",
    "VenueCatalogService",
]
