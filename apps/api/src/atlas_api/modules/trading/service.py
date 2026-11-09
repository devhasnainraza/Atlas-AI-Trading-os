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

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from atlas_api.modules.trading.domain.connections import (
    ConnectionHealth,
    VenueAccount,
    VenueConnection,
    intersect_capabilities,
)
from atlas_api.modules.trading.domain.risk import rule_descriptors
from atlas_api.modules.trading.errors import (
    CapabilityNotPermittedError,
    StepUpMfaRequiredError,
)
from atlas_api.modules.trading.repository.connections import ConnectionRepository
from atlas_core.audit import AuditLogEntry, AuditLogRepository
from atlas_api.modules.trading.schemas import (
    CapabilitiesModel,
    CreateVenueConnectionRequest,
    LiveTradingStatusResponse,
    PaperResetResponse,
    PositionListResponse,
    PositionResponse,
    RiskRuleDescriptor,
    RiskRulesResponse,
    VenueAccountListResponse,
    VenueAccountResponse,
    VenueCapabilitiesResponse,
    VenueConnectionListResponse,
    VenueConnectionResponse,
    VenueListResponse,
    VerifyVenueConnectionResponse,
)
from atlas_api.modules.trading.settings import TradingSettings
from atlas_api.modules.trading.venues import (
    VENUE_FLAG_DEFAULTS,
    VENUE_FLAG_KEYS,
    PaperBookStore,
)
from atlas_core.errors import NotFoundError
from atlas_core.feature_flags import FeatureFlags
from atlas_events import EventEnvelope, InMemoryEventBus, InMemoryOutbox
from atlas_venues.adapters.paper import PAPER_VENUE_CODE
from atlas_venues.enums import AccountViewState, VenueEnvironment
from atlas_venues.models import Capabilities
from atlas_venues.redaction import redact_text
from atlas_venues.registry import AdapterContext, VenueRegistry


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

class VenueConnectionService:
    """Manages user venue connections, permissions verification, and account exposure (Spec 03 US1)."""

    def __init__(
        self,
        repository: ConnectionRepository,
        registry: VenueRegistry,
        flags: FeatureFlags,
        catalog: VenueCatalogService,
        settings: TradingSettings,
        outbox: InMemoryOutbox | None = None,
        bus: InMemoryEventBus | None = None,
        audit_log: AuditLogRepository | None = None,
    ) -> None:
        self._repository = repository
        self._registry = registry
        self._flags = flags
        self._catalog = catalog
        self._settings = settings
        self._outbox = outbox
        self._bus = bus
        self._audit_log = audit_log

    async def create_connection(
        self,
        user_id: str,
        request: CreateVenueConnectionRequest,
        *,
        step_up_verified: bool = False,
    ) -> VenueConnectionResponse:
        self._catalog.require_enabled(request.venue_code)

        if (
            request.environment is VenueEnvironment.LIVE
            and self._settings.require_step_up_for_live
            and not step_up_verified
        ):
            raise StepUpMfaRequiredError(
                "Creating a live connection requires step-up MFA verification."
            )

        conn_id = str(uuid4())
        context = AdapterContext(
            connection_id=conn_id,
            venue_code=request.venue_code,
            environment=request.environment,
            credential_id=request.credential_id,
            venue_account_ref=request.label,
        )

        adapter = self._registry.build_adapter(context)
        declared_caps = adapter.capabilities()

        try:
            ok, detail = await adapter.verify_permissions()
        except Exception as exc:
            ok, detail = False, str(exc)

        sanitized_reason = redact_text(detail) if detail else None

        is_read_only = False
        if detail and any(token in detail.lower() for token in ("read_only", "read-only", "readonly")):
            is_read_only = True

        can_trade = ok and not is_read_only
        granted_caps = intersect_capabilities(
            declared_caps,
            granted_permissions={"can_trade": can_trade, "read_only": is_read_only},
        )

        health = ConnectionHealth.HEALTHY if ok else ConnectionHealth.FAILED

        connection = VenueConnection.create(
            connection_id=conn_id,
            user_id=user_id,
            venue_code=request.venue_code,
            label=request.label,
            environment=request.environment,
            credential_id=request.credential_id,
            granted_capabilities=granted_caps,
            health=health,
            health_reason=sanitized_reason if not ok else None,
        )

        created = await self._repository.create(connection)

        if ok:
            try:
                snapshot = await adapter.account_snapshot()
                account = VenueAccount(
                    id=str(uuid4()),
                    connection_id=created.id,
                    user_id=user_id,
                    venue_account_ref=request.label,
                    environment=request.environment,
                    base_currency=snapshot.currency,
                    balance=snapshot.balance,
                    equity=snapshot.equity,
                    margin_used=getattr(snapshot, "used_margin", getattr(snapshot, "margin_used", None)),
                    margin_available=getattr(snapshot, "available_margin", getattr(snapshot, "margin_available", None)),
                    unrealized_pnl=snapshot.unrealized_pnl,
                    leverage=None,
                    view_state=AccountViewState.LIVE,
                    synced_at=snapshot.venue_time,
                )
                await self._repository.upsert_accounts([account])
            except Exception:
                pass

        if self._audit_log:
            self._audit_log.append(
                AuditLogEntry(
                    actor=user_id,
                    action="trading.connection.created",
                    target=created.id,
                    correlation_id=str(uuid4()),
                    metadata={
                        "venue_code": created.venue_code,
                        "environment": created.environment.value,
                        "health": created.health.value,
                    },
                )
            )

        if self._outbox and self._bus:
            self._outbox.add(
                EventEnvelope(
                    event_type="atlas.trading.venue.connected",
                    producer="atlas-api.trading",
                    payload={
                        "connection_id": created.id,
                        "user_id": user_id,
                        "venue_code": created.venue_code,
                        "environment": created.environment.value,
                        "health": created.health.value,
                    },
                )
            )
            self._outbox.add(
                EventEnvelope(
                    event_type="atlas.trading.connection.created",
                    producer="atlas-api.trading",
                    payload={
                        "connection_id": created.id,
                        "user_id": user_id,
                        "venue_code": created.venue_code,
                        "environment": created.environment.value,
                        "health": created.health.value,
                    },
                )
            )
            await self._outbox.relay(self._bus)

        return self._to_connection_response(created)

    async def get_connection(self, connection_id: str, *, user_id: str) -> VenueConnectionResponse:
        conn = await self._repository.get(connection_id, user_id=user_id)
        if conn is None or conn.disconnected_at is not None:
            raise NotFoundError(f"Venue connection '{connection_id}' not found")
        return self._to_connection_response(conn)

    async def list_connections(
        self,
        user_id: str,
        *,
        environment: VenueEnvironment | None = None,
        health: ConnectionHealth | None = None,
    ) -> VenueConnectionListResponse:
        conns = await self._repository.list(user_id, environment=environment, health=health)
        return VenueConnectionListResponse(
            items=[self._to_connection_response(c) for c in conns]
        )

    async def delete_connection(self, connection_id: str, *, user_id: str) -> None:
        deleted = await self._repository.delete(connection_id, user_id=user_id)
        if not deleted:
            raise NotFoundError(f"Venue connection '{connection_id}' not found")

        if self._audit_log:
            self._audit_log.append(
                AuditLogEntry(
                    actor=user_id,
                    action="trading.connection.disconnected",
                    target=connection_id,
                    correlation_id=str(uuid4()),
                    metadata={"connection_id": connection_id},
                )
            )

        if self._outbox and self._bus:
            self._outbox.add(
                EventEnvelope(
                    event_type="atlas.trading.venue.disconnected",
                    producer="atlas-api.trading",
                    payload={"connection_id": connection_id, "user_id": user_id, "actor_type": "user"},
                )
            )
            self._outbox.add(
                EventEnvelope(
                    event_type="atlas.trading.connection.disconnected",
                    producer="atlas-api.trading",
                    payload={"connection_id": connection_id, "user_id": user_id},
                )
            )
            await self._outbox.relay(self._bus)

    async def verify_connection(
        self, connection_id: str, *, user_id: str
    ) -> VerifyVenueConnectionResponse:
        conn = await self._repository.get(connection_id, user_id=user_id)
        if conn is None or conn.disconnected_at is not None:
            raise NotFoundError(f"Venue connection '{connection_id}' not found")

        self._catalog.require_enabled(conn.venue_code)

        context = AdapterContext(
            connection_id=conn.id,
            venue_code=conn.venue_code,
            environment=conn.environment,
            credential_id=conn.credential_id,
            venue_account_ref=conn.label,
        )
        adapter = self._registry.build_adapter(context)
        declared_caps = adapter.capabilities()

        try:
            ok, detail = await adapter.verify_permissions()
        except Exception as exc:
            ok, detail = False, str(exc)

        sanitized_reason = redact_text(detail) if detail else None
        is_read_only = False
        if detail and any(token in detail.lower() for token in ("read_only", "read-only", "readonly")):
            is_read_only = True

        can_trade = ok and not is_read_only
        granted_caps = intersect_capabilities(
            declared_caps,
            granted_permissions={"can_trade": can_trade, "read_only": is_read_only},
        )

        now = datetime.now(UTC)
        if ok:
            updated = conn.mark_healthy(granted_caps, now=now)
        else:
            updated = conn.mark_failed(sanitized_reason or "Verification failed", now=now)

        await self._repository.update(updated)

        if self._audit_log:
            self._audit_log.append(
                AuditLogEntry(
                    actor=user_id,
                    action="trading.connection.verified" if ok else "trading.connection.degraded",
                    target=updated.id,
                    correlation_id=str(uuid4()),
                    metadata={"venue_code": updated.venue_code, "health": updated.health.value},
                )
            )

        if self._outbox and self._bus:
            if ok:
                self._outbox.add(
                    EventEnvelope(
                        event_type="atlas.trading.venue.verified",
                        producer="atlas-api.trading",
                        payload={
                            "connection_id": updated.id,
                            "capability_version": updated.capability_version,
                            "verified_at": now.isoformat(),
                        },
                    )
                )
            else:
                self._outbox.add(
                    EventEnvelope(
                        event_type="atlas.trading.venue.degraded",
                        producer="atlas-api.trading",
                        payload={
                            "connection_id": updated.id,
                            "venue_code": updated.venue_code,
                            "previous_health": conn.health.value,
                            "health": updated.health.value,
                            "reason_code": sanitized_reason,
                        },
                    )
                )
            await self._outbox.relay(self._bus)

        return VerifyVenueConnectionResponse(
            health=updated.health.value,
            health_reason=updated.health_reason,
            granted_capabilities=self._to_capabilities_model(updated.granted_capabilities),
            verified_at=now.isoformat(),
        )

    async def handle_credential_revoked(
        self, credential_id: str, *, reason: str = "credential_revoked", actor: str = "system"
    ) -> list[str]:
        """Quarantine connection: stops order routing and activates reconciliation (FR-011, T032, T043)."""
        conns = await self._repository.find_by_credential(credential_id)
        now = datetime.now(UTC)
        quarantined_ids: list[str] = []
        for conn in conns:
            quarantined = conn.mark_quarantined(reason=reason, now=now)
            await self._repository.update(quarantined)
            quarantined_ids.append(quarantined.id)

            if self._audit_log:
                self._audit_log.append(
                    AuditLogEntry(
                        actor=actor,
                        action="trading.connection.quarantined",
                        target=quarantined.id,
                        correlation_id=str(uuid4()),
                        metadata={"cause": reason, "venue_code": quarantined.venue_code},
                    )
                )

            if self._outbox and self._bus:
                self._outbox.add(
                    EventEnvelope(
                        event_type="atlas.trading.venue.quarantined",
                        producer="atlas-api.trading",
                        payload={"connection_id": quarantined.id, "cause": reason},
                    )
                )
                self._outbox.add(
                    EventEnvelope(
                        event_type="atlas.trading.reconciliation.requested",
                        producer="atlas-api.trading",
                        payload={"connection_id": quarantined.id, "reason": "credential_revoked"},
                    )
                )
        if self._outbox and self._bus and quarantined_ids:
            await self._outbox.relay(self._bus)
        return quarantined_ids

    async def handle_credential_rotated(self, credential_id: str) -> list[str]:
        """Re-verify any connection linked to rotated credential (T043)."""
        conns = await self._repository.find_by_credential(credential_id)
        reverified_ids: list[str] = []
        for conn in conns:
            await self.verify_connection(conn.id, user_id=conn.user_id)
            reverified_ids.append(conn.id)
        return reverified_ids

    async def list_accounts(
        self, connection_id: str, *, user_id: str, refresh: bool = False
    ) -> VenueAccountListResponse:
        conn = await self._repository.get(connection_id, user_id=user_id)
        if conn is None or conn.disconnected_at is not None:
            raise NotFoundError(f"Venue connection '{connection_id}' not found")

        if refresh and conn.health == ConnectionHealth.HEALTHY:
            context = AdapterContext(
                connection_id=conn.id,
                venue_code=conn.venue_code,
                environment=conn.environment,
                credential_id=conn.credential_id,
                venue_account_ref=conn.label,
            )
            adapter = self._registry.build_adapter(context)
            try:
                snapshot = await adapter.account_snapshot()
                acc = VenueAccount(
                    id=str(uuid4()),
                    connection_id=conn.id,
                    user_id=user_id,
                    venue_account_ref=conn.label,
                    environment=conn.environment,
                    base_currency=snapshot.currency,
                    balance=snapshot.balance,
                    equity=snapshot.equity,
                    margin_used=getattr(snapshot, "used_margin", getattr(snapshot, "margin_used", None)),
                    margin_available=getattr(snapshot, "available_margin", getattr(snapshot, "margin_available", None)),
                    unrealized_pnl=snapshot.unrealized_pnl,
                    leverage=None,
                    view_state=AccountViewState.LIVE,
                    synced_at=snapshot.venue_time,
                )
                await self._repository.upsert_accounts([acc])
            except Exception:
                pass

        accounts = await self._repository.list_accounts(connection_id, user_id=user_id)
        return VenueAccountListResponse(
            items=[self._to_account_response(a) for a in accounts]
        )

    async def list_positions(
        self, connection_id: str | None = None, *, user_id: str
    ) -> PositionListResponse:
        items: list[PositionResponse] = []
        conns = await self._repository.list_for_user(user_id)
        target_conns = [c for c in conns if connection_id is None or c.id == connection_id]

        for conn in target_conns:
            if conn.disconnected_at is not None:
                continue
            context = AdapterContext(
                connection_id=conn.id,
                venue_code=conn.venue_code,
                environment=conn.environment,
                credential_id=conn.credential_id,
                venue_account_ref=conn.label,
            )
            adapter = self._registry.build_adapter(context)
            try:
                venue_positions = await adapter.positions()
                for vp in venue_positions:
                    items.append(
                        PositionResponse(
                            connection_id=conn.id,
                            venue_symbol=vp.venue_symbol,
                            side=str(vp.side),
                            quantity=vp.quantity,
                            average_entry_price=vp.average_entry_price,
                            environment=str(vp.environment),
                            venue_position_ref=vp.venue_position_ref,
                            unrealized_pnl=vp.unrealized_pnl,
                            current_price=vp.current_price,
                            stop_loss=vp.stop_loss,
                            take_profit=vp.take_profit,
                            opened_externally=False,
                            state="open",
                            synced_at=vp.venue_time.isoformat() if vp.venue_time else None,
                        )
                    )
            except Exception:
                pass

        return PositionListResponse(items=items)

    def _to_capabilities_model(self, caps: Capabilities) -> CapabilitiesModel:
        return CapabilitiesModel(
            venue_code=caps.venue_code,
            display_name=caps.display_name,
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
            notes=caps.notes or None,
        )

    def _to_connection_response(self, conn: VenueConnection) -> VenueConnectionResponse:
        return VenueConnectionResponse(
            id=conn.id,
            venue_code=conn.venue_code,
            label=conn.label,
            environment=conn.environment,
            credential_id=conn.credential_id,
            granted_capabilities=self._to_capabilities_model(conn.granted_capabilities),
            health=conn.health.value,
            health_reason=conn.health_reason,
            routing_hold=conn.routing_hold,
            last_contact_at=conn.last_contact_at.isoformat() if conn.last_contact_at else None,
            created_at=conn.created_at.isoformat(),
        )

    def _to_account_response(self, acc: VenueAccount) -> VenueAccountResponse:
        return VenueAccountResponse(
            id=acc.id,
            connection_id=acc.connection_id,
            venue_account_ref=acc.venue_account_ref,
            environment=acc.environment,
            base_currency=acc.base_currency,
            balance=acc.balance,
            equity=acc.equity,
            margin_used=acc.margin_used,
            margin_available=acc.margin_available,
            unrealized_pnl=acc.unrealized_pnl,
            leverage=acc.leverage,
            view_state=acc.view_state.value,
            synced_at=acc.synced_at.isoformat() if acc.synced_at else None,
        )


__all__ = [
    "LiveTradingStatusService",
    "PaperAccountService",
    "RiskCatalogService",
    "VenueCatalogService",
    "VenueConnectionService",
]
