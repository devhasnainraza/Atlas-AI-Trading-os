"""Unit tests for Smart SL/TP and Trailing Stop evaluation (Spec 06 §2, §4)."""

from decimal import Decimal
import pytest
from atlas_api.modules.automation.domain.models import PositionGuardState
from atlas_api.modules.automation.domain.smart_stops import (
    calculate_smart_stops,
    evaluate_position_tick,
)


def test_calculate_smart_stops_long_and_short():
    # Long test
    entry = Decimal("60000.00")
    atr = Decimal("1000.00")
    sl, tp1, tp2, tp3 = calculate_smart_stops(entry, "LONG", atr)
    assert sl == Decimal("58500.0000")  # entry - 1.5 * atr
    assert tp1 == Decimal("61500.0000")
    assert tp2 == Decimal("63000.0000")
    assert tp3 == Decimal("64500.0000")

    # Short test
    sl_s, tp1_s, tp2_s, tp3_s = calculate_smart_stops(entry, "SHORT", atr)
    assert sl_s == Decimal("61500.0000")  # entry + 1.5 * atr
    assert tp1_s == Decimal("58500.0000")
    assert tp2_s == Decimal("57000.0000")
    assert tp3_s == Decimal("55500.0000")


def test_long_position_lifecycle_breakeven_and_trailing():
    guard = PositionGuardState(
        id="guard-1",
        position_id="pos-101",
        account_id="acc-1",
        user_id="user-1",
        symbol="BTC/USDT",
        side="LONG",
        entry_price=Decimal("60000.00"),
        current_stop_loss=Decimal("58500.00"),
        initial_stop_loss=Decimal("58500.00"),
        tp1_price=Decimal("61500.00"),
        tp2_price=Decimal("63000.00"),
        tp3_price=Decimal("66000.00"),
        breakeven_offset=Decimal("50.00"),
        trailing_distance=Decimal("1000.00"),
    )

    # 1. Price below TP1 - nothing changes
    actions = evaluate_position_tick(guard, Decimal("60800.00"))
    assert actions == []
    assert guard.breakeven_reached is False
    assert guard.current_stop_loss == Decimal("58500.00")

    # 2. Price hits TP1 (61550) -> moves stop loss to entry + breakeven_offset (60050)
    actions = evaluate_position_tick(guard, Decimal("61550.00"))
    assert "TP1_FILLED_BREAKEVEN_LOCKED" in actions
    assert guard.tp1_filled is True
    assert guard.breakeven_reached is True
    assert guard.current_stop_loss == Decimal("60050.00")

    # 3. Price hits TP2 (63100) -> activates trailing stop
    actions = evaluate_position_tick(guard, Decimal("63100.00"))
    assert "TP2_FILLED_TRAILING_ACTIVATED" in actions
    assert guard.tp2_filled is True
    assert guard.trailing_active is True

    # 4. Price advances to 65000 -> trailing stop advances to 65000 - 1000 = 64000
    actions = evaluate_position_tick(guard, Decimal("65000.00"))
    assert "TRAILING_STOP_ADVANCED" in actions
    assert guard.current_stop_loss == Decimal("64000.0000")

    # 5. Price pulls back to 64500 -> stop loss does NOT retreat
    actions = evaluate_position_tick(guard, Decimal("64500.00"))
    assert "TRAILING_STOP_ADVANCED" not in actions
    assert guard.current_stop_loss == Decimal("64000.0000")

    # 6. Price drops to 63900 -> triggers stop loss close
    actions = evaluate_position_tick(guard, Decimal("63900.00"))
    assert "STOP_LOSS_TRIGGERED_CLOSE" in actions
    assert guard.status == "closed"
