"""GitOps feature-flag ingestion (FR-040, US6).

Flag state lives in a Git-managed JSON file; a CD job writes it into the shared flag
volume. Two paths keep runtimes current, and both end in the same place:

* ``FlagSyncWatcher`` — polls the flag source for a content change (the pull path, which
  works even when webhooks are lost).
* ``ingest_flag_sync`` — called by the API's GitOps webhook endpoint (the push path, for
  fast propagation).

Both record what changed so a flag flip is always attributable. Values are recorded as
key lists only, never as payloads, because flag values may encode customer targeting.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path

from atlas_observability import get_logger

logger = get_logger("atlas_worker.flags")


@dataclass(frozen=True)
class FlagSyncResult:
    """What one sync observed. ``changed`` is False when the revision is already applied."""

    revision: str
    changed: bool
    added: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()
    updated: tuple[str, ...] = ()

    @property
    def touched_keys(self) -> tuple[str, ...]:
        return tuple(sorted({*self.added, *self.removed, *self.updated}))


def _revision(flags: dict[str, object]) -> str:
    """Content hash of the flag set — stable across reorderings of the same JSON."""
    canonical = json.dumps(flags, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def diff_flags(previous: dict[str, object], current: dict[str, object]) -> FlagSyncResult:
    """Compare two flag sets; the result is what gets audited."""
    prev_keys, cur_keys = set(previous), set(current)
    added = tuple(sorted(cur_keys - prev_keys))
    removed = tuple(sorted(prev_keys - cur_keys))
    updated = tuple(sorted(k for k in prev_keys & cur_keys if previous[k] != current[k]))
    revision = _revision(current)
    return FlagSyncResult(
        revision=revision,
        changed=bool(added or removed or updated),
        added=added,
        removed=removed,
        updated=updated,
    )


@dataclass
class FlagSyncWatcher:
    """Polls a JSON flag file and reports content-level changes.

    Content hashing rather than mtime: a CD job that rewrites the file unchanged (a
    redeploy with no flag edits) must not look like a flag change in the audit log.
    """

    source: Path
    interval_seconds: float = 5.0
    _flags: dict[str, object] = field(default_factory=dict, init=False)
    _revision: str = field(default="", init=False)
    _running: bool = field(default=False, init=False)

    @property
    def revision(self) -> str:
        """Currently applied revision; empty string before the first successful read."""
        return self._revision

    def _read_source(self) -> dict[str, object] | None:
        """Return parsed flags, or None when the source is missing or malformed.

        A broken flag file must never stop the watcher — the last good revision keeps
        serving (fail-safe, Constitution IX).
        """
        try:
            raw = self.source.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning("flag_source_unreadable", source=str(self.source), error=str(exc))
            return None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.error("flag_source_malformed", source=str(self.source), error=str(exc))
            return None
        if not isinstance(parsed, dict):
            logger.error("flag_source_not_an_object", source=str(self.source))
            return None
        return parsed

    def sync_once(self) -> FlagSyncResult | None:
        """One poll. Returns None when the source could not be read at all."""
        current = self._read_source()
        if current is None:
            return None

        result = diff_flags(self._flags, current)
        if not result.changed and result.revision == self._revision:
            return result

        self._flags, self._revision = current, result.revision
        logger.info(
            "flag_revision_applied",
            revision=result.revision,
            added=list(result.added),
            removed=list(result.removed),
            updated=list(result.updated),
        )
        return result

    async def run_forever(
        self, on_change: Callable[[FlagSyncResult], Awaitable[None]] | None = None
    ) -> None:
        self._running = True
        while self._running:
            result = self.sync_once()
            if result is not None and result.changed and on_change is not None:
                await on_change(result)
            await asyncio.sleep(self.interval_seconds)

    def stop(self) -> None:
        self._running = False


def ingest_flag_sync(
    payload: dict[str, object], watcher: FlagSyncWatcher | None = None
) -> FlagSyncResult:
    """Handle a GitOps webhook notification.

    The webhook is a *hint*, not a source of truth: it triggers a re-read of the flag
    source rather than trusting values in the request body, so a spoofed or stale payload
    cannot set flag state.
    """
    commit = str(payload.get("revision") or payload.get("after") or "unknown")
    logger.info("flag_webhook_received", commit=commit)

    if watcher is None:
        return FlagSyncResult(revision=commit, changed=False)

    result = watcher.sync_once()
    if result is None:
        return FlagSyncResult(revision=watcher.revision, changed=False)
    return result
