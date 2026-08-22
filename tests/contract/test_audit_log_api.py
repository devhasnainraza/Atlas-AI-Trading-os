"""US3 — audit log: sensitive platform actions recorded and queryable (T023 part 2)."""

from atlas_api.testing import build_test_app, make_client
from atlas_events import EventEnvelope

ECHO = "atlas.sample.echo.requested"


async def test_redrive_and_replay_are_audited():
    app = build_test_app()
    runtime = app.state.runtime

    async def poison(env: EventEnvelope) -> None:
        raise RuntimeError("poison")

    runtime.bus.subscribe("audit.poison", ECHO, poison, max_attempts=1)
    await runtime.bus.publish(
        EventEnvelope(event_type=ECHO, producer="test", payload={"message_length": 1})
    )
    dead = runtime.bus.dead_letters()[0]

    async with make_client(app) as client:
        redrive = await client.post(
            f"/v1/platform/dead-letter-events/{dead.envelope.event_id}/redrive",
            params={"consumer": "audit.poison"},
        )
        assert redrive.status_code == 202

        replay = await client.post("/v1/platform/event-replays", json={"event_type": ECHO})
        assert replay.status_code == 202

        audit = await client.get("/v1/platform/audit-log")
    actions = [e["action"] for e in audit.json()["items"]]
    assert "dlq.redrive" in actions and "replay.start" in actions
    for entry in audit.json()["items"]:
        assert entry["correlation_id"], "audit entries must be correlation-joined"


async def test_redrive_unknown_event_returns_not_found_envelope():
    app = build_test_app()
    async with make_client(app) as client:
        resp = await client.post(
            "/v1/platform/dead-letter-events/00000000-0000-0000-0000-000000000000/redrive",
            params={"consumer": "nobody"},
        )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "ATLAS-NF-001"


def test_audit_log_rejects_secret_shaped_metadata():
    import pytest

    from atlas_api.modules.platform.domain.audit_log_entry import AuditLogEntry
    from atlas_api.modules.platform.repository.audit_log import InMemoryAuditLog

    log = InMemoryAuditLog()
    with pytest.raises(ValueError):
        log.append(
            AuditLogEntry(
                actor="x",
                action="test.action",
                target="t",
                correlation_id="c",
                metadata={"api_key": "leak"},
            )
        )
