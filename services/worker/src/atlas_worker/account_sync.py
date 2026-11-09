"""Account and position synchronization service & worker (Spec 03 US3, T065, T066).

Features:
- Periodic scheduled sync & snapshot reconciliation on reconnect (T066).
- Account streaming with polling fallback for adapters that lack private streams (MT5/Paper) (T065).
- Emits atlas.trading.account.synced, position.opened, position.updated, position.closed.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from atlas_api.modules.trading.domain.accounts import AccountProjection, derive_account_view_state
from atlas_api.modules.trading.domain.positions import PositionProjection, PositionRegistry
from atlas_events import EventBus, EventEnvelope
from atlas_observability import get_logger
from atlas_venues.errors import UnsupportedCapabilityError
from atlas_venues.models import AccountSnapshot, VenueOrder, VenuePosition
from atlas_venues.protocol import VenueAdapter

logger = get_logger("atlas_worker.account_sync")


class AccountSyncWorker:
    """Manages sync, stream consumption, and reconciliation for accounts and positions."""

    def __init__(
        self,
        event_bus: EventBus | None = None,
        freshness_target_seconds: float = 30.0,
    ) -> None:
        self._bus = event_bus
        self.freshness_target = freshness_target_seconds
        self._running = False

    async def sync_connection(
        self,
        connection_id: str,
        user_id: str,
        adapter: VenueAdapter,
        account_proj: AccountProjection,
        position_reg: PositionRegistry,
    ) -> bool:
        """Execute one snapshot sync and reconciliation pass (T066)."""
        now = datetime.now(UTC)
        try:
            snapshot = await adapter.account_snapshot()
            applied = account_proj.apply_snapshot(
                snapshot, now=now, freshness_target_seconds=self.freshness_target
            )
            if applied and self._bus is not None:
                venue_account_id = f"{connection_id}:{snapshot.venue_account_ref}"
                envelope = EventEnvelope(
                    event_type="atlas.trading.account.synced",
                    producer="worker",
                    payload={
                        "venue_account_id": venue_account_id,
                        "view_state": str(account_proj.view_state),
                        "synced_at": snapshot.venue_time.isoformat(),
                    },
                )
                await self._bus.publish(envelope)

            # Positions reconciliation
            venue_positions = await adapter.positions()
            reconciled = position_reg.reconcile_snapshot(
                connection_id=connection_id,
                user_id=user_id,
                venue_positions=venue_positions,
                reconcile_time=now,
            )

            if self._bus is not None:
                for p in reconciled:
                    if p.state == "open" and p.synced_at == now:
                        env_pos = EventEnvelope(
                            event_type="atlas.trading.position.opened",
                            producer="worker",
                            payload={
                                "position_id": f"{connection_id}:{p.venue_symbol}:{p.side}",
                                "side": str(p.side),
                                "quantity": str(p.quantity),
                            },
                        )
                        await self._bus.publish(env_pos)
                    elif p.state == "closed":
                        env_close = EventEnvelope(
                            event_type="atlas.trading.position.closed",
                            producer="worker",
                            payload={
                                "position_id": f"{connection_id}:{p.venue_symbol}:{p.side}",
                                "realized_pnl": str(p.realized_pnl or "0.00"),
                                "closed_at": p.closed_at.isoformat() if p.closed_at else now.isoformat(),
                            },
                        )
                        await self._bus.publish(env_close)

            logger.info("account_sync_success", connection_id=connection_id)
            return True

        except Exception as exc:
            logger.warning("account_sync_failed", connection_id=connection_id, error=str(exc))
            account_proj.mark_stale_on_failure(now=now)
            return False

    async def run_streaming_or_polling(
        self,
        connection_id: str,
        user_id: str,
        adapter: VenueAdapter,
        account_proj: AccountProjection,
        position_reg: PositionRegistry,
        *,
        polling_interval: float = 30.0,
        max_cycles: int | None = None,
    ) -> None:
        """Stream account updates where supported; fall back to polling for MT5/Paper (T065)."""
        self._running = True
        cycles = 0

        # Try streaming first
        can_stream = True
        try:
            stream_iter = adapter.stream_account()
            async for item in stream_iter:
                if not self._running:
                    break
                now = datetime.now(UTC)
                if isinstance(item, AccountSnapshot):
                    account_proj.apply_snapshot(
                        item, now=now, freshness_target_seconds=self.freshness_target
                    )
                elif isinstance(item, VenuePosition):
                    position_reg.apply_venue_position(connection_id, user_id, item)

                cycles += 1
                if max_cycles and cycles >= max_cycles:
                    return
        except UnsupportedCapabilityError:
            can_stream = False

        # Polling fallback (MT5 / Paper)
        if not can_stream:
            while self._running:
                await self.sync_connection(
                    connection_id=connection_id,
                    user_id=user_id,
                    adapter=adapter,
                    account_proj=account_proj,
                    position_reg=position_reg,
                )
                cycles += 1
                if max_cycles and cycles >= max_cycles:
                    break
                await asyncio.sleep(polling_interval)

    def stop(self) -> None:
        self._running = False


__all__ = ["AccountSyncWorker"]
