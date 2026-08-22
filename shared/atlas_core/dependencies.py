"""Dependency health probes for readiness reporting (Spec 00 FR-032, US3).

Services register named probes; the platform health endpoint aggregates them. A probe
returns (up, latency_ms). Probes must never raise — failures report ``up=False``.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

ProbeFn = Callable[[], Awaitable[bool]]

_PROBE_TIMEOUT_SECONDS = 3.0


@dataclass(frozen=True)
class DependencyStatus:
    name: str
    up: bool
    latency_ms: float


class DependencyRegistry:
    """Named health probes, checked concurrently at readiness time."""

    def __init__(self) -> None:
        self._probes: dict[str, ProbeFn] = {}

    def register(self, name: str, probe: ProbeFn) -> None:
        self._probes[name] = probe

    def names(self) -> list[str]:
        return sorted(self._probes)

    async def check_all(self) -> list[DependencyStatus]:
        async def run(name: str, probe: ProbeFn) -> DependencyStatus:
            start = time.perf_counter()
            try:
                up = await asyncio.wait_for(probe(), timeout=_PROBE_TIMEOUT_SECONDS)
            except Exception:
                up = False
            latency = (time.perf_counter() - start) * 1000
            return DependencyStatus(name=name, up=bool(up), latency_ms=round(latency, 2))

        return await asyncio.gather(*(run(n, p) for n, p in sorted(self._probes.items())))
