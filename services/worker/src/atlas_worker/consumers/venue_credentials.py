"""Venue credential lifecycle consumer (Spec 03 US1, T043; plan §8, §12).

Listens for credential revocation and rotation from Spec 01 (atlas_credentials):
- atlas.credentials.credential.revoked: transitions matching venue connections to QUARANTINED,
  stops active routing, and emits atlas.trading.venue.quarantined + atlas.trading.reconciliation.requested (FR-011).
- atlas.credentials.credential.rotated: re-verifies matching venue connections (T043).

Handlers are idempotent via the event ledger so redeliveries are safely de-duplicated.
"""

from __future__ import annotations

from typing import Protocol

from atlas_events.bus import EventBus
from atlas_events.envelope import EventEnvelope
from atlas_observability import get_logger

logger = get_logger("atlas_worker.venue_credentials")


class ConnectionQuarantineHandler(Protocol):
    """Protocol for quarantining connections associated with a revoked credential."""

    async def handle_credential_revoked(
        self, credential_id: str, *, reason: str = "credential_revoked", actor: str = "system"
    ) -> list[str]: ...

    async def handle_credential_rotated(self, credential_id: str) -> list[str]: ...


class VenueCredentialConsumer:
    """Consumes credential revocation/rotation events and triggers venue connection quarantine/re-verify."""

    def __init__(self, service: ConnectionQuarantineHandler) -> None:
        self._service = service

    async def on_credential_revoked(self, envelope: EventEnvelope) -> None:
        credential_id = envelope.payload.get("credential_id")
        if not credential_id:
            logger.warning("credential_revoked_missing_id", event_id=envelope.event_id)
            return

        cause = envelope.payload.get("cause") or envelope.payload.get("reason", "credential_revoked")
        quarantined = await self._service.handle_credential_revoked(
            credential_id, reason=cause, actor=envelope.payload.get("user_id", "system")
        )
        logger.info(
            "connections_quarantined_for_revoked_credential",
            event_id=envelope.event_id,
            credential_id=credential_id,
            affected_connections=quarantined,
        )

    async def on_credential_rotated(self, envelope: EventEnvelope) -> None:
        credential_id = envelope.payload.get("credential_id")
        if not credential_id:
            logger.warning("credential_rotated_missing_id", event_id=envelope.event_id)
            return

        reverified = await self._service.handle_credential_rotated(credential_id)
        logger.info(
            "connections_reverified_for_rotated_credential",
            event_id=envelope.event_id,
            credential_id=credential_id,
            affected_connections=reverified,
        )

    def register(self, bus: EventBus) -> None:
        bus.subscribe(
            consumer="atlas_worker.venue_credentials",
            event_type="atlas.credentials.credential.revoked",
            handler=self.on_credential_revoked,
            replay_capable=True,
        )
        bus.subscribe(
            consumer="atlas_worker.venue_credentials",
            event_type="atlas.credentials.credential.rotated",
            handler=self.on_credential_rotated,
            replay_capable=True,
        )


__all__ = ["ConnectionQuarantineHandler", "VenueCredentialConsumer"]
