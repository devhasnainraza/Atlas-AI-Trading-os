"""Smart Stop Loss, Take Profit, and Trailing Stop evaluation logic (Spec 06 §2, §4)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from atlas_api.modules.automation.domain.models import PositionGuardState


def calculate_smart_stops(
    entry_price: Decimal,
    side: str,
    atr: Decimal,
    risk_reward_multiplier: Decimal = Decimal("1.5"),
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Calculates Initial SL, TP1, TP2, TP3 based on ATR volatility and risk multiples."""
    side_upper = side.upper()
    risk_unit = (atr * Decimal("1.5")).quantize(Decimal("0.0001"))

    if side_upper in ("LONG", "BUY"):
        stop_loss = entry_price - risk_unit
        tp1 = entry_price + (risk_unit * Decimal("1.0"))
        tp2 = entry_price + (risk_unit * Decimal("2.0"))
        tp3 = entry_price + (risk_unit * risk_reward_multiplier * Decimal("2.0"))
    else:  # SHORT / SELL
        stop_loss = entry_price + risk_unit
        tp1 = entry_price - (risk_unit * Decimal("1.0"))
        tp2 = entry_price - (risk_unit * Decimal("2.0"))
        tp3 = entry_price - (risk_unit * risk_reward_multiplier * Decimal("2.0"))

    return (
        stop_loss.quantize(Decimal("0.0001")),
        tp1.quantize(Decimal("0.0001")),
        tp2.quantize(Decimal("0.0001")),
        tp3.quantize(Decimal("0.0001")),
    )


def evaluate_position_tick(
    guard: PositionGuardState,
    current_price: Decimal,
) -> list[str]:
    """Evaluates incoming price tick against active position guard state.

    Updates guard state in-place and returns an audit list of actions triggered.
    """
    if guard.status != "active":
        return []

    actions: list[str] = []
    side = guard.side.upper()
    now = datetime.now(timezone.utc)
    guard.updated_at = now

    # Initial watermark initialization
    if guard.highest_price_seen == Decimal("0"):
        guard.highest_price_seen = max(guard.entry_price, current_price)
    if guard.lowest_price_seen == Decimal("0"):
        guard.lowest_price_seen = min(guard.entry_price, current_price)

    # 1. Update watermarks
    if current_price > guard.highest_price_seen:
        guard.highest_price_seen = current_price
    if current_price < guard.lowest_price_seen:
        guard.lowest_price_seen = current_price

    if side in ("LONG", "BUY"):
        # Stop-loss breach check
        if current_price <= guard.current_stop_loss:
            guard.status = "closed"
            actions.append("STOP_LOSS_TRIGGERED_CLOSE")
            return actions

        # TP1 check -> Lock Breakeven
        if not guard.tp1_filled and current_price >= guard.tp1_price:
            guard.tp1_filled = True
            breakeven_target = guard.entry_price + guard.breakeven_offset
            if breakeven_target > guard.current_stop_loss:
                guard.current_stop_loss = breakeven_target
                guard.breakeven_reached = True
                actions.append("TP1_FILLED_BREAKEVEN_LOCKED")

        # TP2 check -> Activate Trailing Stop
        if guard.tp1_filled and not guard.tp2_filled and current_price >= guard.tp2_price:
            guard.tp2_filled = True
            guard.trailing_active = True
            if guard.trailing_distance <= Decimal("0"):
                # Default trailing distance: distance between TP1 and TP2
                guard.trailing_distance = (guard.tp2_price - guard.tp1_price).quantize(Decimal("0.0001"))
            actions.append("TP2_FILLED_TRAILING_ACTIVATED")

        # Dynamic Trailing Stop advancement
        if guard.trailing_active and guard.trailing_distance > Decimal("0"):
            dynamic_stop = guard.highest_price_seen - guard.trailing_distance
            if dynamic_stop > guard.current_stop_loss:
                guard.current_stop_loss = dynamic_stop.quantize(Decimal("0.0001"))
                actions.append("TRAILING_STOP_ADVANCED")

        # TP3 check -> Runner target reached
        if current_price >= guard.tp3_price:
            guard.status = "closed"
            actions.append("TP3_RUNNER_TARGET_REACHED")

    else:  # SHORT / SELL
        # Stop-loss breach check
        if current_price >= guard.current_stop_loss:
            guard.status = "closed"
            actions.append("STOP_LOSS_TRIGGERED_CLOSE")
            return actions

        # TP1 check -> Lock Breakeven
        if not guard.tp1_filled and current_price <= guard.tp1_price:
            guard.tp1_filled = True
            breakeven_target = guard.entry_price - guard.breakeven_offset
            if breakeven_target < guard.current_stop_loss:
                guard.current_stop_loss = breakeven_target
                guard.breakeven_reached = True
                actions.append("TP1_FILLED_BREAKEVEN_LOCKED")

        # TP2 check -> Activate Trailing Stop
        if guard.tp1_filled and not guard.tp2_filled and current_price <= guard.tp2_price:
            guard.tp2_filled = True
            guard.trailing_active = True
            if guard.trailing_distance <= Decimal("0"):
                guard.trailing_distance = (guard.tp1_price - guard.tp2_price).quantize(Decimal("0.0001"))
            actions.append("TP2_FILLED_TRAILING_ACTIVATED")

        # Dynamic Trailing Stop advancement
        if guard.trailing_active and guard.trailing_distance > Decimal("0"):
            dynamic_stop = guard.lowest_price_seen + guard.trailing_distance
            if dynamic_stop < guard.current_stop_loss:
                guard.current_stop_loss = dynamic_stop.quantize(Decimal("0.0001"))
                actions.append("TRAILING_STOP_ADVANCED")

        # TP3 check -> Runner target reached
        if current_price <= guard.tp3_price:
            guard.status = "closed"
            actions.append("TP3_RUNNER_TARGET_REACHED")

    return actions
