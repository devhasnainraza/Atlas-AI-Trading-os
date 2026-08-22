"""Platform operator event flows — DLQ re-drive and replay orchestration (FR-016..018).

The router owns HTTP shape; this module owns the operation: call the bus, then record the
audit trail. Both actions are operator-initiated and must always leave an audit entry, so
they are kept together here rather than inlined per-endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from atlas_api.modules.platform.domain.audit_log_entry import AuditLogEntry
from atlas_api.runtime import PlatformRuntime
from atlas_core.correlation import get_correlation_id
from atlas_core.errors import NotFoundError
from atlas_observability import get_logger

logger = get_logger("atlas_api.platform.events")


@dataclass(frozen=True)
class ReplayResult:
    event_type: str
    events_replayed: int


async def redrive_dead_letter(runtime: PlatformRuntime, event_id: str, consumer: str) -> None:
    """Re-deliver one dead-lettered event to its consumer.

    Raises ``NotFoundError`` when no matching entry is still in ``dead`` status, so a
    double re-drive is reported rather than silently succeeding.
    """
    ok = await runtime.bus.redrive(event_id, consumer)
    if not ok:
        raise NotFoundError(f"No dead-lettered event '{event_id}' for consumer '{consumer}'")

    runtime.audit_log.append(
        AuditLogEntry(
            actor="operator",  # real identity arrives with Spec 01 auth
            action="dlq.redrive",
            target=event_id,
            correlation_id=get_correlation_id(),
            metadata={"consumer": consumer},
        )
    )
    logger.info("dlq_redriven", event_id=event_id, consumer=consumer)


async def replay_events(
    runtime: PlatformRuntime,
    event_type: str,
    since: datetime | None = None,
    until: datetime | None = None,
) -> ReplayResult:
    """Re-deliver historical events of one type to replay-capable subscribers."""
    count = await runtime.bus.replay(event_type, since, until)

    runtime.audit_log.append(
        AuditLogEntry(
            actor="operator",
            action="replay.start",
            target=event_type,
            correlation_id=get_correlation_id(),
            metadata={"events_replayed": count},
        )
    )
    logger.info("replay_completed", event_type=event_type, events_replayed=count)
    return ReplayResult(event_type=event_type, events_replayed=count)
