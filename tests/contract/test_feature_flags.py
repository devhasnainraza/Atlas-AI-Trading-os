"""US6 — feature flag evaluation contract and fail-safe defaults (T036 part 1)."""

import os

from atlas_api.testing import build_test_app, make_client
from atlas_core.feature_flags import FeatureFlags, FileFlagProvider, StaticFlagProvider


async def test_unknown_flag_evaluates_to_safe_default():
    app = build_test_app()
    async with make_client(app) as client:
        resp = await client.get("/v1/feature-flags/nonexistent.flag/evaluation")
    assert resp.status_code == 200
    body = resp.json()
    assert body["value"] is False
    assert body["reason"] == "DEFAULT"


async def test_defined_flag_evaluates_to_value():
    app = build_test_app()
    app.state.runtime.flags = FeatureFlags(StaticFlagProvider({"sample.guarded_capability": True}))
    async with make_client(app) as client:
        guarded = await client.get("/v1/sample/guarded")
    assert guarded.json() == {"enabled": True, "reason": "TARGETING_MATCH"}


async def test_provider_failure_falls_back_to_default():
    class ExplodingProvider:
        def resolve(self, flag_key, context=None):
            raise RuntimeError("flagd unreachable")

    flags = FeatureFlags(ExplodingProvider())
    evaluation = flags.evaluate("sample.guarded_capability", default=False)
    assert evaluation.value is False
    assert evaluation.reason == "ERROR_FALLBACK"


async def test_gitops_sync_webhook_records_audit_entry():
    app = build_test_app()
    async with make_client(app) as client:
        resp = await client.post(
            "/v1/platform/feature-flags/sync",
            json={"revision": "a1b2c3d", "source": "argocd"},
        )
        assert resp.status_code == 202
        assert resp.json() == {"status": "synced", "revision": "a1b2c3d"}

        audit = await client.get("/v1/platform/audit-log", params={"action": "feature_flags.sync"})

    entries = audit.json()["items"]
    assert len(entries) == 1
    assert entries[0]["actor"] == "gitops:argocd"
    assert entries[0]["target"] == "a1b2c3d"


async def test_gitops_sync_forces_provider_reread(tmp_path):
    """The webhook must not depend on mtime resolution: a same-second rewrite still
    propagates, which is the failure mode the pull path alone cannot cover."""
    import json

    flag_file = tmp_path / "flags.json"
    flag_file.write_text(json.dumps({"sample.guarded_capability": False}))

    app = build_test_app()
    provider = FileFlagProvider(flag_file)
    app.state.runtime.flags = FeatureFlags(provider)

    async with make_client(app) as client:
        assert (await client.get("/v1/sample/guarded")).json()["enabled"] is False

        # Rewrite without advancing mtime — mtime-based reload would miss this.
        mtime = flag_file.stat().st_mtime
        flag_file.write_text(json.dumps({"sample.guarded_capability": True}))
        os.utime(flag_file, (mtime, mtime))

        assert (await client.get("/v1/sample/guarded")).json()["enabled"] is False

        await client.post(
            "/v1/platform/feature-flags/sync", json={"revision": "deadbee", "source": "argocd"}
        )
        assert (await client.get("/v1/sample/guarded")).json()["enabled"] is True
