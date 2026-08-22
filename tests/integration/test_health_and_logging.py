"""US3 — health endpoints, dependency degradation, correlation traceability (T023)."""

from atlas_api.testing import build_test_app, make_client


async def test_liveness_always_up():
    app = build_test_app()
    async with make_client(app) as client:
        resp = await client.get("/v1/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "alive"}


async def test_readiness_ready_with_no_failing_dependencies():
    app = build_test_app()

    async def up() -> bool:
        return True

    app.state.runtime.dependencies.register("postgres", up)
    async with make_client(app) as client:
        resp = await client.get("/v1/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["dependencies"][0] == {
        "name": "postgres",
        "status": "up",
        "latency_ms": body["dependencies"][0]["latency_ms"],
    }


async def test_readiness_degrades_and_returns_503_when_dependency_down():
    app = build_test_app()

    async def up() -> bool:
        return True

    async def down() -> bool:
        raise ConnectionError("kafka unreachable")

    app.state.runtime.dependencies.register("postgres", up)
    app.state.runtime.dependencies.register("kafka", down)

    async with make_client(app) as client:
        resp = await client.get("/v1/health/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "degraded"
    statuses = {d["name"]: d["status"] for d in body["dependencies"]}
    assert statuses == {"kafka": "down", "postgres": "up"}


async def test_every_response_carries_correlation_id_header():
    app = build_test_app()
    async with make_client(app) as client:
        for path in ("/v1/health/live", "/v1/platform/modules"):
            resp = await client.get(path)
            assert resp.headers.get("X-Correlation-ID"), f"missing correlation header on {path}"
