"""US6 — flag changes propagate without restart via file provider hot reload (T036 part 2)."""

import json
import os
import time

from atlas_api.testing import build_test_app, make_client
from atlas_core.feature_flags import FeatureFlags, FileFlagProvider


async def test_file_flag_change_propagates_without_restart(tmp_path):
    flag_file = tmp_path / "flags.json"
    flag_file.write_text(json.dumps({"sample.guarded_capability": False}))

    app = build_test_app()
    app.state.runtime.flags = FeatureFlags(FileFlagProvider(flag_file))

    async with make_client(app) as client:
        before = await client.get("/v1/sample/guarded")
        assert before.json()["enabled"] is False

        # Simulate the GitOps update: rewrite the file; ensure mtime moves.
        flag_file.write_text(json.dumps({"sample.guarded_capability": True}))
        os.utime(flag_file, (time.time() + 1, time.time() + 1))

        after = await client.get("/v1/sample/guarded")
        assert after.json() == {"enabled": True, "reason": "TARGETING_MATCH"}


async def test_flag_file_deleted_keeps_last_known_then_default(tmp_path):
    flag_file = tmp_path / "flags.json"
    flag_file.write_text(json.dumps({"sample.guarded_capability": True}))
    flags = FeatureFlags(FileFlagProvider(flag_file))

    assert flags.is_enabled("sample.guarded_capability") is True
    flag_file.unlink()
    # Provider keeps last loaded state (no crash); unknown keys still default safely.
    assert flags.is_enabled("sample.guarded_capability") is True
    assert flags.is_enabled("never.defined", default=False) is False


async def test_configuring_a_flags_file_is_enough_to_make_the_app_read_it(tmp_path):
    """`ATLAS_FEATURE_FLAGS_FILE` must be the only step an operator takes.

    The tests above install the provider by hand, which proves the provider works but not that
    `create_app` ever builds one. Without that wiring the committed `infra/flags/flags.json` would
    be a file nothing reads, and every venue gate would silently answer from its code default —
    fail-closed, so safe, but also unswitchable without a redeploy.
    """
    flag_file = tmp_path / "flags.json"
    flag_file.write_text(json.dumps({"sample.guarded_capability": True}))

    app = build_test_app(feature_flags_file=str(flag_file))
    async with make_client(app) as client:
        resp = await client.get("/v1/sample/guarded")
    assert resp.json()["enabled"] is True, "create_app did not install a file-backed provider"


async def test_without_the_setting_the_app_falls_back_to_the_callers_default(tmp_path):
    """No file configured is not an error; it means every gate answers with its own default."""
    app = build_test_app()
    async with make_client(app) as client:
        resp = await client.get("/v1/sample/guarded")
    assert resp.json()["enabled"] is False
