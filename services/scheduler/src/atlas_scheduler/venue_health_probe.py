"""Venue connection health probe job (Spec 03 US1, T042; plan §8).

Periodically evaluates active venue connections according to per-venue probe cadence:
- If healthy connection fails permission/reachability check: marks connection degraded/failed
  and emits atlas.trading.venue.degraded (FR-004, FR-011).
- If degraded connection recovers: marks connection healthy and emits atlas.trading.venue.verified.
"""

from __future__ import annotations

from typing import Any, Protocol, Sequence

from atlas_observability import get_logger

logger = get_logger("atlas_scheduler.venue_health_probe")


class VerifiableConnection(Protocol):
    id: str
    venue_code: str
    user_id: str


class ConnectionProbeService(Protocol):
    """Protocol for probing and re-verifying venue connections."""

    async def list_active_connections(self) -> Sequence[VerifiableConnection]: ...

    async def verify_connection(self, connection_id: str, *, user_id: str) -> Any: ...


async def probe_all_connections(service: ConnectionProbeService) -> dict[str, int]:
    """Execute one health probe pass across all active venue connections."""
    conns = await service.list_active_connections()
    verified_count = 0
    failed_count = 0

    for conn in conns:
        try:
            result = await service.verify_connection(conn.id, user_id=conn.user_id)
            health = getattr(result, "health", "healthy")
            if health in ("healthy", "verified"):
                verified_count += 1
            else:
                failed_count += 1
        except Exception as exc:
            failed_count += 1
            logger.warning(
                "connection_health_probe_failed",
                connection_id=conn.id,
                venue_code=conn.venue_code,
                error=str(exc),
            )

    logger.info(
        "venue_health_probe_completed",
        total=len(conns),
        verified=verified_count,
        failed=failed_count,
    )
    return {"total": len(conns), "verified": verified_count, "failed": failed_count}


__all__ = ["ConnectionProbeService", "VerifiableConnection", "probe_all_connections"]
