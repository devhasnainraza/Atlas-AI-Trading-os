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
