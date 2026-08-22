"""Platform module API: health, module listing, DLQ administration, replay, audit query,
feature-flag evaluation (Spec 00 FR-016..018, FR-032, FR-040, FR-047)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field

from atlas_api.deps import get_runtime
from atlas_api.modules.platform.domain.audit_log_entry import AuditLogEntry
from atlas_api.modules.platform.events import redrive_dead_letter, replay_events
from atlas_api.modules.public import ModuleDef
from atlas_api.runtime import PlatformRuntime
from atlas_core.correlation import get_correlation_id

router = APIRouter(tags=["platform"])
health_router = APIRouter(tags=["health"])


# -- Health (FR-032) ----------------------------------------------------------
@health_router.get("/health/live")
async def liveness() -> dict[str, str]:
    return {"status": "alive"}


@health_router.get("/health/ready")
async def readiness(
    response: Response, runtime: PlatformRuntime = Depends(get_runtime)
) -> dict[str, Any]:
    statuses = await runtime.dependencies.check_all()
    all_up = all(s.up for s in statuses)
    if not all_up:
        response.status_code = 503
    return {
        "status": "ready" if all_up else "degraded",
        "dependencies": [
            {"name": s.name, "status": "up" if s.up else "down", "latency_ms": s.latency_ms}
            for s in statuses
        ],
    }


# -- Modules ------------------------------------------------------------------
@router.get("/platform/modules")
async def list_modules(runtime: PlatformRuntime = Depends(get_runtime)) -> list[dict[str, str]]:
    return [
        {"name": m.name, "version": m.version, "owner": m.owner}
        for m in runtime.modules.all_modules()
    ]


# -- Dead letter administration (FR-016/017) -----------------------------------
@router.get("/platform/dead-letter-events")
async def list_dead_letter_events(
    status: str = "dead",
    runtime: PlatformRuntime = Depends(get_runtime),
) -> dict[str, Any]:
    entries = runtime.bus.dead_letters(status=status)
    return {
        "items": [
            {
                "event_id": d.envelope.event_id,
                "event_type": d.envelope.event_type,
                "consumer": d.consumer,
                "failure_reason": d.failure_reason,
                "attempts": d.attempts,
                "status": d.status,
            }
            for d in entries
        ],
        "total": len(entries),
    }


@router.post("/platform/dead-letter-events/{event_id}/redrive", status_code=202)
async def redrive_dead_letter_event(
    event_id: str,
    consumer: str,
    runtime: PlatformRuntime = Depends(get_runtime),
) -> dict[str, str]:
    await redrive_dead_letter(runtime, event_id, consumer)
    return {"status": "redriven", "event_id": event_id}


# -- Replay (FR-018) -----------------------------------------------------------
class ReplayRequest(BaseModel):
    event_type: str
    since: datetime | None = None
    until: datetime | None = None


@router.post("/platform/event-replays", status_code=202)
async def start_event_replay(
    body: ReplayRequest,
    runtime: PlatformRuntime = Depends(get_runtime),
) -> dict[str, Any]:
    result = await replay_events(runtime, body.event_type, body.since, body.until)
    return {"status": "completed", "events_replayed": result.events_replayed}


# -- Audit query (FR-047) --------------------------------------------------------
@router.get("/platform/audit-log")
async def query_audit_log(
    actor: str | None = None,
    action: str | None = None,
    limit: int = 100,
    runtime: PlatformRuntime = Depends(get_runtime),
) -> dict[str, Any]:
    entries = runtime.audit_log.query(actor=actor, action=action, limit=min(limit, 500))
    return {
        "items": [
            {
                "id": e.id,
                "actor": e.actor,
                "action": e.action,
                "target": e.target,
                "correlation_id": e.correlation_id,
                "metadata": e.metadata,
                "occurred_at": e.occurred_at.isoformat(),
            }
            for e in entries
        ],
        "total": len(entries),
    }


# -- Feature flags (FR-040) -------------------------------------------------------
class FlagEvaluationResponse(BaseModel):
    flag_key: str
    value: Any
    reason: str = Field(examples=["TARGETING_MATCH", "DEFAULT", "ERROR_FALLBACK"])


@router.get("/feature-flags/{flag_key}/evaluation", response_model=FlagEvaluationResponse)
async def evaluate_feature_flag(
    flag_key: str,
    runtime: PlatformRuntime = Depends(get_runtime),
) -> FlagEvaluationResponse:
    result = runtime.flags.evaluate(flag_key, default=False)
    return FlagEvaluationResponse(
        flag_key=result.flag_key, value=result.value, reason=result.reason
    )


class FlagSyncRequest(BaseModel):
    """GitOps webhook notification. Values are never taken from the body — the revision is
    a hint that triggers a provider re-read, so a spoofed payload cannot set flag state."""

    revision: str = Field(examples=["a1b2c3d"], max_length=200)
    source: str = Field(default="gitops", max_length=100)


@router.post("/platform/feature-flags/sync", status_code=202)
async def sync_feature_flags(
    body: FlagSyncRequest,
    runtime: PlatformRuntime = Depends(get_runtime),
) -> dict[str, str]:
    """Force flag re-evaluation after a Git-managed flag change (FR-040).

    Propagation does not depend on this call — providers also reload on their own poll —
    but the webhook shortens the window and gives the change an audit record.
    """
    runtime.flags.refresh()
    runtime.audit_log.append(
        AuditLogEntry(
            actor=f"gitops:{body.source}",
            action="feature_flags.sync",
            target=body.revision,
            correlation_id=get_correlation_id(),
            metadata={"source": body.source},
        )
    )
    return {"status": "synced", "revision": body.revision}


def build_platform_module() -> ModuleDef:
    return ModuleDef(
        name="platform",
        version="1.0.0",
        owner="platform-team",
        router=router,
        routers_extra=(health_router,),
    )
