"""Behavioral analytics, R-multiple formulas, and bias diagnostic heuristics (Spec 07 §2, §4)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from atlas_api.modules.journal.domain.models import TradeJournalRecord


def calculate_r_multiple(
    entry_price: Decimal,
    exit_price: Decimal,
    stop_loss: Decimal,
    side: str,
) -> Decimal:
    """Calculates realized profit in multiples of initial stop-loss risk (R-Multiple)."""
    side_upper = side.upper()
    risk_unit = abs(entry_price - stop_loss)
    if risk_unit == Decimal("0"):
        return Decimal("0.00")

    if side_upper in ("LONG", "BUY"):
        profit_unit = exit_price - entry_price
    else:
        profit_unit = entry_price - exit_price

    r_multiple = profit_unit / risk_unit
    return r_multiple.quantize(Decimal("0.01"))


def detect_revenge_trading(
    recent_closed_trades: list[TradeJournalRecord],
    new_order_time: datetime,
) -> tuple[bool, str | None]:
    """Detects if an order is placed < 5 minutes after a losing trade."""
    if not recent_closed_trades:
        return False, None

    # Sort by exit_time descending
    sorted_trades = sorted(recent_closed_trades, key=lambda t: t.exit_time, reverse=True)
    last_trade = sorted_trades[0]

    # If last trade was a loss
    if last_trade.net_pnl < Decimal("0"):
        elapsed_seconds = (new_order_time - last_trade.exit_time).total_seconds()
        if 0 <= elapsed_seconds <= 300:  # within 5 minutes (300 seconds)
            return True, f"Revenge trading detected: Order initiated {int(elapsed_seconds)}s after losing trade on {last_trade.symbol}."

    return False, None


def detect_overtrading(
    daily_trades: list[TradeJournalRecord],
    max_daily_trades: int = 8,
) -> tuple[bool, str | None]:
    """Flags when trade frequency exceeds healthy discipline threshold."""
    if len(daily_trades) >= max_daily_trades:
        return True, f"Overtrading warning: {len(daily_trades)} trades executed today, exceeding recommended daily limit of {max_daily_trades}."
    return False, None


def calculate_performance_metrics(
    trades: list[TradeJournalRecord],
) -> tuple[Decimal, Decimal, Decimal, int]:
    """Calculates (net_pnl, profit_factor, win_rate, total_trades)."""
    if not trades:
        return Decimal("0.00"), Decimal("0.00"), Decimal("0.00"), 0

    total_trades = len(trades)
    net_pnl = sum(t.net_pnl for t in trades)
    winning_trades = [t for t in trades if t.net_pnl > Decimal("0")]
    losing_trades = [t for t in trades if t.net_pnl < Decimal("0")]

    win_rate = (Decimal(len(winning_trades)) / Decimal(total_trades) * Decimal("100.00")).quantize(Decimal("0.01"))

    gross_profit = sum(t.net_pnl for t in winning_trades)
    gross_loss = abs(sum(t.net_pnl for t in losing_trades))

    if gross_loss == Decimal("0"):
        profit_factor = Decimal("10.00") if gross_profit > Decimal("0") else Decimal("1.00")
    else:
        profit_factor = (gross_profit / gross_loss).quantize(Decimal("0.01"))

    return net_pnl.quantize(Decimal("0.01")), profit_factor, win_rate, total_trades
