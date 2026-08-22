"""US4 — unified API contract: validation envelope, rate limits, version coexistence,
security headers (T027)."""

from atlas_api.testing import build_test_app, make_client


async def test_malformed_request_returns_standard_error_envelope():
    app = build_test_app()
    async with make_client(app) as client:
        resp = await client.post("/v1/sample/echo", json={"message": "", "extra_field": 1})
    assert resp.status_code == 422
    error = resp.json()["error"]
    assert error["code"] == "ATLAS-VAL-001"
    assert error["correlation_id"]
    fields = {d["field"] for d in error["details"]}
    assert any("message" in f for f in fields)
    assert any("extra_field" in f for f in fields), "unknown fields must be rejected"
    assert "stack" not in resp.text.lower()


async def test_unknown_route_and_internal_errors_never_leak_details():
    app = build_test_app()
    async with make_client(app) as client:
        resp = await client.get("/v1/does-not-exist")
    assert resp.status_code == 404
    assert "Traceback" not in resp.text


async def test_rate_limit_enforced_with_retry_after():
    app = build_test_app(rate_limit_default_per_minute=3)
    async with make_client(app) as client:
        for _ in range(3):
            ok = await client.post("/v1/sample/echo", json={"message": "hi"})
            assert ok.status_code == 200
        limited = await client.post("/v1/sample/echo", json={"message": "hi"})
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "ATLAS-RL-001"
    assert "Retry-After" in limited.headers


async def test_health_endpoints_exempt_from_rate_limits():
    app = build_test_app(rate_limit_default_per_minute=1)
    async with make_client(app) as client:
        for _ in range(5):
            resp = await client.get("/v1/health/live")
            assert resp.status_code == 200


async def test_v1_and_v2_coexist_with_different_shapes():
    app = build_test_app()
    async with make_client(app) as client:
        v1 = await client.post("/v1/sample/echo", json={"message": "hello"})
        v2 = await client.post("/v2/sample/echo", json={"message": "hello"})
    assert v1.status_code == 200 and v2.status_code == 200
    assert v1.json()["message"] == "hello"  # v1 contract unchanged
    assert v2.json()["echo"] == {"message": "hello"}  # breaking shape isolated to v2


async def test_security_headers_present_on_responses():
    app = build_test_app()
    async with make_client(app) as client:
        resp = await client.get("/v1/platform/modules")
    for header in (
        "Strict-Transport-Security",
        "X-Content-Type-Options",
        "Content-Security-Policy",
        "Referrer-Policy",
    ):
        assert header in resp.headers, f"missing security header {header}"


async def test_openapi_document_is_published():
    app = build_test_app()
    async with make_client(app) as client:
        resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    assert "/v1/sample/echo" in paths and "/v2/sample/echo" in paths
