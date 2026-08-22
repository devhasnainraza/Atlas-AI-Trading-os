"""Worker GitOps flag ingestion — revision diffing, fail-safe reads, webhook path (T034)."""

from __future__ import annotations

import json

from atlas_worker.flags import FlagSyncWatcher, diff_flags, ingest_flag_sync


def _write(path, flags) -> None:
    path.write_text(json.dumps(flags), encoding="utf-8")


def test_first_sync_reports_all_keys_as_added(tmp_path):
    source = tmp_path / "flags.json"
    _write(source, {"a": True, "b": False})

    result = FlagSyncWatcher(source=source).sync_once()

    assert result is not None
    assert result.changed is True
    assert result.added == ("a", "b")
    assert result.removed == () and result.updated == ()


def test_unchanged_rewrite_is_not_a_flag_change(tmp_path):
    """A redeploy that rewrites the file identically must not pollute the audit trail."""
    source = tmp_path / "flags.json"
    _write(source, {"a": True})
    watcher = FlagSyncWatcher(source=source)
    watcher.sync_once()

    _write(source, {"a": True})  # same content, new mtime
    second = watcher.sync_once()

    assert second is not None
    assert second.changed is False
    assert second.touched_keys == ()


def test_key_reorder_is_not_a_flag_change(tmp_path):
    source = tmp_path / "flags.json"
    source.write_text('{"a": true, "b": false}', encoding="utf-8")
    watcher = FlagSyncWatcher(source=source)
    first = watcher.sync_once()

    source.write_text('{"b": false, "a": true}', encoding="utf-8")
    second = watcher.sync_once()

    assert first is not None and second is not None
    assert second.changed is False
    assert second.revision == first.revision


def test_diff_classifies_added_removed_and_updated():
    result = diff_flags({"keep": 1, "drop": 2, "flip": False}, {"keep": 1, "flip": True, "new": 3})

    assert result.added == ("new",)
    assert result.removed == ("drop",)
    assert result.updated == ("flip",)
    assert result.touched_keys == ("drop", "flip", "new")


def test_malformed_source_keeps_last_good_revision(tmp_path):
    source = tmp_path / "flags.json"
    _write(source, {"a": True})
    watcher = FlagSyncWatcher(source=source)
    watcher.sync_once()
    good_revision = watcher.revision

    source.write_text("{not json", encoding="utf-8")

    assert watcher.sync_once() is None
    assert watcher.revision == good_revision


def test_missing_source_does_not_raise(tmp_path):
    watcher = FlagSyncWatcher(source=tmp_path / "absent.json")

    assert watcher.sync_once() is None
    assert watcher.revision == ""


def test_non_object_source_is_rejected(tmp_path):
    source = tmp_path / "flags.json"
    source.write_text("[1, 2, 3]", encoding="utf-8")

    assert FlagSyncWatcher(source=source).sync_once() is None


def test_webhook_triggers_reread_and_ignores_body_values(tmp_path):
    """The payload is a hint only: flag state comes from the source, never the request."""
    source = tmp_path / "flags.json"
    _write(source, {"a": False})
    watcher = FlagSyncWatcher(source=source)
    watcher.sync_once()

    _write(source, {"a": True})
    result = ingest_flag_sync({"revision": "abc123", "flags": {"a": "spoofed"}}, watcher)

    assert result.changed is True
    assert result.updated == ("a",)
    assert result.revision == watcher.revision


def test_webhook_without_watcher_is_inert():
    result = ingest_flag_sync({"after": "sha-from-github"})

    assert result.changed is False
    assert result.revision == "sha-from-github"
