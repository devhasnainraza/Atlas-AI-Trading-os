"""Feature flags (Spec 00 FR-040, US6).

OpenFeature-shaped minimal API: providers resolve flag values; every evaluation carries a
safe default used when the provider fails or the flag is unknown (fail-safe, Constitution
IX). ``FileFlagProvider`` reloads on mtime change, so a GitOps-managed file propagates
without restart; flagd/Redis providers implement the same protocol in deployed envs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class FlagEvaluation:
    flag_key: str
    value: Any
    reason: str  # TARGETING_MATCH | DEFAULT | DISABLED | ERROR_FALLBACK


class FlagProvider(Protocol):
    def resolve(self, flag_key: str, context: dict[str, Any] | None = None) -> Any | None:
        """Return the flag value, or None when the flag is not defined."""
        ...


class StaticFlagProvider:
    """Fixed in-memory flags — the default for tests and bare local boots."""

    def __init__(self, flags: dict[str, Any] | None = None) -> None:
        self._flags = dict(flags or {})

    def set(self, flag_key: str, value: Any) -> None:
        self._flags[flag_key] = value

    def resolve(self, flag_key: str, context: dict[str, Any] | None = None) -> Any | None:
        return self._flags.get(flag_key)


class FileFlagProvider:
    """JSON-file-backed flags with mtime-based hot reload (GitOps-friendly)."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._mtime: float = -1.0
        self._flags: dict[str, Any] = {}

    def _maybe_reload(self) -> None:
        try:
            mtime = self._path.stat().st_mtime
        except OSError:
            return
        if mtime != self._mtime:
            self._flags = json.loads(self._path.read_text(encoding="utf-8"))
            self._mtime = mtime

    def refresh(self) -> None:
        """Force a re-read on the next resolve — used by the GitOps webhook path, where
        the file may change within the filesystem's mtime resolution."""
        self._mtime = -1.0

    def resolve(self, flag_key: str, context: dict[str, Any] | None = None) -> Any | None:
        self._maybe_reload()
        return self._flags.get(flag_key)


class FeatureFlags:
    """Evaluation facade: provider errors and unknown flags fall back to the caller's
    declared default — a flag can never take a service down."""

    def __init__(self, provider: FlagProvider) -> None:
        self._provider = provider

    def evaluate(
        self,
        flag_key: str,
        default: Any,
        context: dict[str, Any] | None = None,
    ) -> FlagEvaluation:
        try:
            value = self._provider.resolve(flag_key, context)
        except Exception:
            return FlagEvaluation(flag_key, default, "ERROR_FALLBACK")
        if value is None:
            return FlagEvaluation(flag_key, default, "DEFAULT")
        return FlagEvaluation(flag_key, value, "TARGETING_MATCH")

    def is_enabled(self, flag_key: str, default: bool = False, **context: Any) -> bool:
        return bool(self.evaluate(flag_key, default, context or None).value)

    def refresh(self) -> None:
        """Ask the provider to drop cached state. Providers without a refresh hook (static,
        remote-push) are a no-op — the caller does not need to know which kind it holds."""
        refresh = getattr(self._provider, "refresh", None)
        if callable(refresh):
            refresh()
