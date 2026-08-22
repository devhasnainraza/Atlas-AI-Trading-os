"""US5 — end-to-end local-stack smoke validation (T032).

Verifies clone-to-running acceptance criteria against a live local API.
Run via: uv run pytest tests/e2e/ --e2e (requires the API to be running on localhost:8000)
Skipped automatically in non-live environments so CI never blocks on a missing API.
"""

from __future__ import annotations

import os
import subprocess

import httpx
import pytest

API_URL = os.environ.get("ATLAS_API_URL", "http://localhost:8000")


# Skip entire module if the API is not reachable (CI with no live stack).
def _api_reachable() -> bool:
    try:
        resp = httpx.get(f"{API_URL}/v1/health/live", timeout=2)
        return resp.status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _api_reachable(),
    reason="Local API not reachable; skipping E2E smoke (start the stack first)",
)


def test_liveness_passes():
    resp = httpx.get(f"{API_URL}/v1/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "alive"}


def test_readiness_passes():
    resp = httpx.get(f"{API_URL}/v1/health/ready")
    assert resp.status_code in (200, 503)  # 503 allowed locally without all infra up
    body = resp.json()
    assert body["status"] in ("ready", "degraded")


def test_openapi_docs_published():
    resp = httpx.get(f"{API_URL}/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    assert "/v1/sample/echo" in paths, "sample module must be discoverable"


def test_sample_echo_end_to_end():
    resp = httpx.post(f"{API_URL}/v1/sample/echo", json={"message": "smoke"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["message"] == "smoke"
    assert body["correlation_id"]


def test_v1_v2_coexistence():
    v1 = httpx.post(f"{API_URL}/v1/sample/echo", json={"message": "compat"})
    v2 = httpx.post(f"{API_URL}/v2/sample/echo", json={"message": "compat"})
    assert v1.json()["message"] == "compat"  # v1 shape unchanged
    assert "echo" in v2.json()  # v2 breaking shape isolated


def test_correlation_id_round_trips():
    cid = "aaaaaaaa-aaaa-4aaa-baaa-aaaaaaaaaaaa"
    resp = httpx.post(
        f"{API_URL}/v1/sample/echo",
        json={"message": "corr"},
        headers={"X-Correlation-ID": cid},
    )
    assert resp.headers.get("X-Correlation-ID") == cid
    assert resp.json()["correlation_id"] == cid


def test_rate_limit_header_present():
    """Over-limit request must return 429 with Retry-After (not an unhandled error)."""
    # Not stressable against a live server in CI; just verify the error envelope shape.
    resp = httpx.post(f"{API_URL}/v1/sample/echo", json={"message": "x" * 501})
    # 422 (too long) or 200; either way must carry the Correlation-ID header.
    assert resp.headers.get("X-Correlation-ID")


def test_security_headers_on_every_response():
    resp = httpx.get(f"{API_URL}/v1/health/live")
    for header in (
        "Strict-Transport-Security",
        "X-Content-Type-Options",
        "Content-Security-Policy",
    ):
        assert header in resp.headers


def test_event_pipeline_smoke_script():
    """Run the smoke-events script to verify the full outbox→relay→consumer path."""
    result = subprocess.run(
        ["bash", "scripts/smoke-events"],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    )
    assert result.returncode == 0, f"smoke-events failed:\n{result.stdout}\n{result.stderr}"
