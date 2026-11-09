"""Integration tests for User Story 3: Account and position sync (T060, T061, T062).

Guarantees asserted:
- T060: Externally opened position imported with opened_externally: True and counted in exposure math (FR-017).
- T061: Sync failure ⇒ view_state: stale with age; never-synced ⇒ unknown (FR-019).
- T062: Out-of-order account updates never overwrite newer state.
- Zero float money (Constitution X).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from atlas_api.modules.trading.domain.accounts import (
    AccountProjection,
    AccountViewState,
    derive_account_view_state,
)
from atlas_api.modules.trading.domain.positions import PositionProjection, PositionRegistry
from atlas_venues.enums import PositionSide, VenueEnvironment
from atlas_venues.models import AccountSnapshot, VenuePosition


class TestAccountAndPositionSync:
    """T060, T061, T062 integration test suite."""

    def test_externally_opened_position_imported_and_included_in_exposure(self) -> None:
        """T060: Externally opened position discovered, flagged opened_externally, counted in exposure (FR-017)."""
        registry = PositionRegistry(is_hedging=False)
        conn_id = "conn-binance-01"
        user_id = "usr-trader-01"
        now = datetime.now(UTC)

        # 1. Position originated by Atlas
        atlas_pos = VenuePosition(
            venue_code="binance",
            venue_account_ref="acc-01",
            venue_symbol="BTCUSDT",
            side=PositionSide.LONG,
            quantity=Decimal("1.5"),
            average_entry_price=Decimal("60000.00"),
            environment=VenueEnvironment.DEMO,
            venue_time=now,
            venue_position_ref="pos-atlas-01",
            current_price=Decimal("62000.00"),
        )
        registry.register_atlas_position("pos-atlas-01")
        p1 = registry.apply_venue_position(conn_id, user_id, atlas_pos)
        assert p1.opened_externally is False
        assert p1.exposure_notional == Decimal("1.5") * Decimal("62000.00")  # 93,000

        # 2. Position discovered from venue that was NOT created by Atlas (e.g. mobile app or web)
        external_pos = VenuePosition(
            venue_code="binance",
            venue_account_ref="acc-01",
            venue_symbol="ETHUSDT",
            side=PositionSide.SHORT,
            quantity=Decimal("10.0"),
            average_entry_price=Decimal("3000.00"),
            environment=VenueEnvironment.DEMO,
            venue_time=now,
            venue_position_ref="pos-external-99",
            current_price=Decimal("3100.00"),
        )
        p2 = registry.apply_venue_position(conn_id, user_id, external_pos)
        assert p2.opened_externally is True
        assert p2.exposure_notional == Decimal("10.0") * Decimal("3100.00")  # 31,000

        # Exposure math must include both positions
        total_exp = registry.total_exposure_notional(conn_id)
        assert total_exp == Decimal("93000.00") + Decimal("31000.00")
        assert total_exp == Decimal("124000.00")

    def test_account_sync_failure_marks_stale_never_synced_unknown(self) -> None:
        """T061: Never synced ⇒ unknown; sync failure or age > threshold ⇒ stale with age (FR-019)."""
        conn_id = "conn-oanda-01"
        user_id = "usr-trader-01"
        now = datetime(2026, 9, 26, 12, 0, 0, tzinfo=UTC)

        # 1. Never synced account ⇒ view_state: UNKNOWN
        acc = AccountProjection.create_unknown(
            connection_id=conn_id,
            user_id=user_id,
            venue_account_ref="oanda-acc-01",
            environment=VenueEnvironment.DEMO,
        )
        assert acc.view_state is AccountViewState.UNKNOWN
        assert acc.synced_at is None
        assert acc.age_seconds is None

        # 2. Successful sync within freshness window (e.g. 5 seconds ago) ⇒ view_state: LIVE
        t_recent = now - timedelta(seconds=5)
        snap = AccountSnapshot(
            venue_code="oanda",
            venue_account_ref="oanda-acc-01",
            environment=VenueEnvironment.DEMO,
            currency="USD",
            balance=Decimal("100000.00"),
            equity=Decimal("102500.00"),
            venue_time=t_recent,
            available_margin=Decimal("95000.00"),
            used_margin=Decimal("5000.00"),
        )
        applied = acc.apply_snapshot(snap, now=now, freshness_target_seconds=30.0)
        assert applied is True
        assert acc.view_state is AccountViewState.LIVE
        assert acc.age_seconds == 5.0

        # 3. Time passes (> 30s freshness target) or sync fails ⇒ view_state: STALE with age
        t_future = now + timedelta(seconds=60)
        state, age = derive_account_view_state(acc.synced_at, now=t_future, freshness_target_seconds=30.0)
        assert state is AccountViewState.STALE
        assert age == 65.0

        acc.mark_stale_on_failure(now=t_future)
        assert acc.view_state is AccountViewState.STALE
        assert acc.age_seconds == 65.0

    def test_out_of_order_account_and_position_updates_prevented(self) -> None:
        """T062: Out-of-order account/position updates never overwrite newer state."""
        conn_id = "conn-bybit-01"
        user_id = "usr-trader-01"
        t_newer = datetime(2026, 9, 26, 12, 10, 0, tzinfo=UTC)
        t_older = datetime(2026, 9, 26, 12, 9, 50, tzinfo=UTC)

        acc = AccountProjection.create_unknown(
            connection_id=conn_id,
            user_id=user_id,
            venue_account_ref="bybit-acc-01",
        )

        newer_snap = AccountSnapshot(
            venue_code="bybit",
            venue_account_ref="bybit-acc-01",
            environment=VenueEnvironment.DEMO,
            currency="USDT",
            balance=Decimal("75000.00"),
            equity=Decimal("75000.00"),
            venue_time=t_newer,
        )
        assert acc.apply_snapshot(newer_snap, now=t_newer) is True
        assert acc.balance == Decimal("75000.00")

        # Older snapshot received late (e.g. out of order network packet)
        older_snap = AccountSnapshot(
            venue_code="bybit",
            venue_account_ref="bybit-acc-01",
            environment=VenueEnvironment.DEMO,
            currency="USDT",
            balance=Decimal("74000.00"),
            equity=Decimal("74000.00"),
            venue_time=t_older,
        )
        applied = acc.apply_snapshot(older_snap, now=t_newer)
        assert applied is False
        assert acc.balance == Decimal("75000.00")  # Retained newer balance

        # Positions out-of-order protection
        reg = PositionRegistry(is_hedging=False)
        pos_newer = VenuePosition(
            venue_code="bybit",
            venue_account_ref="bybit-acc-01",
            venue_symbol="BTCUSDT",
            side=PositionSide.LONG,
            quantity=Decimal("2.0"),
            average_entry_price=Decimal("65000.00"),
            environment=VenueEnvironment.DEMO,
            venue_time=t_newer,
        )
        p = reg.apply_venue_position(conn_id, user_id, pos_newer)
        assert p.quantity == Decimal("2.0")

        pos_older = VenuePosition(
            venue_code="bybit",
            venue_account_ref="bybit-acc-01",
            venue_symbol="BTCUSDT",
            side=PositionSide.LONG,
            quantity=Decimal("1.0"),
            average_entry_price=Decimal("64000.00"),
            environment=VenueEnvironment.DEMO,
            venue_time=t_older,
        )
        p_reapplied = reg.apply_venue_position(conn_id, user_id, pos_older)
        assert p_reapplied.quantity == Decimal("2.0")  # Retained newer quantity
