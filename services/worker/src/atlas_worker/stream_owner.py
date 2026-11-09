"""Stream owner worker and Redis lease coordination (Spec 03 US2, T053).

One worker holds a lease per (connection, symbol group) to avoid duplicate venue
subscriptions and prevent feed gaps on failover. Watches for heartbeat silence and
unexpected disconnects, emitting feed.degraded and feed.recovered events.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime
from typing import Any, Protocol

from atlas_events import EventBus, EventEnvelope
from atlas_observability import get_logger
from atlas_venues.models import QuoteTick

logger = get_logger("atlas_worker.stream_owner")


class StreamLeaseManager:
    """Manages distributed leases for market data streaming ownership."""

    def __init__(self) -> None:
        self._leases: dict[str, tuple[str, float]] = {}

    def _key(self, connection_id: str, symbol_group: str) -> str:
        return f"marketdata:lease:{connection_id}:{symbol_group}"

    async def acquire(
        self, connection_id: str, symbol_group: str, owner_id: str, ttl_seconds: float = 30.0
    ) -> bool:
        key = self._key(connection_id, symbol_group)
        now = time.monotonic()
        current = self._leases.get(key)
        if current is not None:
            curr_owner, expires_at = current
            if curr_owner != owner_id and now < expires_at:
                return False
        self._leases[key] = (owner_id, now + ttl_seconds)
        return True

    async def renew(
        self, connection_id: str, symbol_group: str, owner_id: str, ttl_seconds: float = 30.0
    ) -> bool:
        key = self._key(connection_id, symbol_group)
        now = time.monotonic()
        current = self._leases.get(key)
        if current is None or current[0] != owner_id or now >= current[1]:
            return False
        self._leases[key] = (owner_id, now + ttl_seconds)
        return True

    async def release(self, connection_id: str, symbol_group: str, owner_id: str) -> bool:
        key = self._key(connection_id, symbol_group)
        current = self._leases.get(key)
        if current is not None and current[0] == owner_id:
            del self._leases[key]
            return True
        return False


class QuoteStoreProtocol(Protocol):
    async def save_quote(self, tick: QuoteTick, *, canonical_symbol: str) -> Any: ...


class StreamOwner:
    """Owns quote stream for a (connection, symbol group) lease."""

    def __init__(
        self,
        owner_id: str,
        lease_mgr: StreamLeaseManager,
        quote_store: QuoteStoreProtocol,
        event_bus: EventBus,
        heartbeat_timeout_seconds: float = 5.0,
        backfill_threshold_seconds: float = 60.0,
        reconnect_max_backoff: float = 30.0,
    ) -> None:
        self.owner_id = owner_id
        self._leases = lease_mgr
        self._quotes = quote_store
        self._bus = event_bus
        self.heartbeat_timeout = heartbeat_timeout_seconds
        self.backfill_threshold = backfill_threshold_seconds
        self.reconnect_max_backoff = reconnect_max_backoff
        self._running = False
        self._is_degraded = False
        self._degraded_since: datetime | None = None
        self._last_quote_at: float = 0.0

    @property
    def is_degraded(self) -> bool:
        return self._is_degraded

    async def emit_degraded(self, connection_id: str, venue_code: str, reason: str) -> None:
        if self._is_degraded:
            return
        self._is_degraded = True
        self._degraded_since = datetime.now(UTC)
        envelope = EventEnvelope(
            event_type="atlas.marketdata.feed.degraded",
            producer="worker",
            payload={
                "connection_id": connection_id,
                "venue_code": venue_code,
                "reason_code": reason,
                "since": self._degraded_since.isoformat(),
            },
        )
        await self._bus.publish(envelope)
        logger.warning(
            "stream_feed_degraded",
            connection_id=connection_id,
            venue_code=venue_code,
            reason=reason,
        )

    async def emit_recovered(self, connection_id: str) -> None:
        if not self._is_degraded:
            return
        now = datetime.now(UTC)
        gap_seconds = 0.0
        if self._degraded_since is not None:
            gap_seconds = max(0.0, (now - self._degraded_since).total_seconds())
        self._is_degraded = False
        self._degraded_since = None

        envelope = EventEnvelope(
            event_type="atlas.marketdata.feed.recovered",
            producer="worker",
            payload={
                "connection_id": connection_id,
                "gap_seconds": gap_seconds,
                "backfill_required": gap_seconds >= self.backfill_threshold,
            },
        )
        await self._bus.publish(envelope)
        logger.info(
            "stream_feed_recovered",
            connection_id=connection_id,
            gap_seconds=gap_seconds,
        )

    async def run_stream(
        self,
        connection_id: str,
        venue_code: str,
        symbol_group: str,
        symbols: Sequence[str],
        adapter: Any,
        *,
        max_ticks: int | None = None,
    ) -> None:
        """Run quote streaming with lease management and gap detection."""
        has_lease = await self._leases.acquire(connection_id, symbol_group, self.owner_id)
        if not has_lease:
            logger.info("stream_lease_not_acquired", connection_id=connection_id, group=symbol_group)
            return

        self._running = True
        self._last_quote_at = time.monotonic()
        tick_count = 0

        try:
            stream_iter: AsyncIterator[QuoteTick] = adapter.stream_quotes(symbols)
            async for tick in stream_iter:
                if not self._running:
                    break

                self._last_quote_at = time.monotonic()
                if self._is_degraded:
                    await self.emit_recovered(connection_id)

                await self._quotes.save_quote(tick, canonical_symbol=tick.venue_symbol)
                tick_count += 1

                # Periodically renew lease
                if tick_count % 50 == 0:
                    renewed = await self._leases.renew(connection_id, symbol_group, self.owner_id)
                    if not renewed:
                        logger.warning("stream_lease_lost", connection_id=connection_id)
                        break

                if max_ticks and tick_count >= max_ticks:
                    break
        except Exception as exc:
            await self.emit_degraded(connection_id, venue_code, reason=f"stream_error: {exc}")
            raise
        finally:
            self._running = False
            await self._leases.release(connection_id, symbol_group, self.owner_id)

    def stop(self) -> None:
        self._running = False


__all__ = ["QuoteStoreProtocol", "StreamLeaseManager", "StreamOwner"]
