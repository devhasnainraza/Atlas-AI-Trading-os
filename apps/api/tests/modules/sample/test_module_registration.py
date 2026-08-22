"""US1 — module scaffold, registration, and shared-service consumption (T013)."""

from atlas_api.modules.sample import events as sample_events
from atlas_api.testing import build_test_app, make_client


async def test_sample_module_is_registered_and_listed():
    app = build_test_app()
    async with make_client(app) as client:
        resp = await client.get("/v1/platform/modules")
    assert resp.status_code == 200
    names = {m["name"] for m in resp.json()}
    assert {"platform", "sample"} <= names


async def test_sample_echo_serves_through_unified_api_and_publishes_event():
    app = build_test_app()
    sample_events.received.clear()
    async with make_client(app) as client:
        resp = await client.post("/v1/sample/echo", json={"message": "hello atlas"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["message"] == "hello atlas"
    assert body["correlation_id"]
    # The proof event flowed outbox → relay → bus → subscriber (US1 + US2 seam).
    assert len(sample_events.received) == 1
    assert sample_events.received[0].payload == {"message_length": len("hello atlas")}


async def test_correlation_id_roundtrip_header():
    app = build_test_app()
    supplied = "11111111-1111-4111-8111-111111111111"
    async with make_client(app) as client:
        resp = await client.post(
            "/v1/sample/echo",
            json={"message": "x"},
            headers={"X-Correlation-ID": supplied},
        )
    assert resp.headers["X-Correlation-ID"] == supplied
    assert resp.json()["correlation_id"] == supplied


async def test_module_registration_is_additive_no_duplicate_names():
    app = build_test_app()
    runtime = app.state.runtime
    import pytest

    from atlas_api.modules.public import ModuleDef

    with pytest.raises(ValueError):
        runtime.modules.register(ModuleDef(name="sample", version="9.9.9", owner="x"))
