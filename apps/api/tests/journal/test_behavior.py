"""Unit tests for behavioral analytics and R-multiple calculations (Spec 07 §2, §4)."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from atlas_api.modules.journal.domain.behavior import (
    calculate_performance_metrics,
    calculate_r_multiple,
    detect_overtrading,
    detect_revenge_trading,
)
from atlas_api.modules.journal.domain.models import TradeJournalRecord


def test_calculate_r_multiple():
    # Long win: entry 100, SL 90, exit 125 -> (125-100) / 10 = +2.50R
    r_long = calculate_r_multiple(
        entry_price=Decimal("100.00"),
        exit_price=Decimal("125.00"),
        stop_loss=Decimal("90.00"),
        side="LONG",
    )
    assert r_long == Decimal("2.50")

    # Short win: entry 100, SL 110, exit 80 -> (100-80) / 10 = +2.00R
    r_short = calculate_r_multiple(
        entry_price=Decimal("100.00"),
        exit_price=Decimal("80.00"),
        stop_loss=Decimal("110.00"),
        side="SHORT",
    )
    assert r_short == Decimal("2.00")

    # Long loss: entry 100, SL 90, exit 90 -> (90-100) / 10 = -1.00R
    r_loss = calculate_r_multiple(
        entry_price=Decimal("100.00"),
        exit_price=Decimal("90.00"),
        stop_loss=Decimal("90.00"),
        side="LONG",
    )
    assert r_loss == Decimal("-1.00")


def test_detect_revenge_trading():
    now = datetime.now(timezone.utc)
    losing_trade = TradeJournalRecord(
        id="j-1",
        user_id="trader-1",
        order_id="o-1",
        account_id="acc-1",
        symbol="BTC/USDT",
        side="LONG",
        entry_price=Decimal("60000.00"),
        exit_price=Decimal("59000.00"),
        entry_time=now - timedelta(minutes=15),
        exit_time=now - timedelta(minutes=2),  # 2 minutes ago
        net_pnl=Decimal("-250.00"),
        r_multiple=Decimal("-1.00"),
        fees_usd=Decimal("5.00"),
        slippage_pips=Decimal("0.50"),
        chart_image_url="https://storage/j-1.webp",
        technical_indicators={},
        ai_post_mortem="Loss",
    )

    # Placing order 2 minutes after loss -> flags revenge trading
    flagged, message = detect_revenge_trading([losing_trade], now)
    assert flagged is True
    assert "Revenge trading detected" in message

    # Placing order 10 minutes after loss -> not flagged
    flagged_late, _ = detect_revenge_trading([losing_trade], now + timedelta(minutes=8))
    assert flagged_late is False


def test_calculate_performance_metrics():
    now = datetime.now(timezone.utc)
    trades = [
        TradeJournalRecord(
            id=f"j-{i}",
            user_id="trader-1",
            order_id=f"o-{i}",
            account_id="acc-1",
            symbol="EUR/USD",
            side="LONG",
            entry_price=Decimal("1.0800"),
            exit_price=Decimal("1.0850" if i < 3 else "1.0750"),
            entry_time=now,
            exit_time=now,
            net_pnl=Decimal("150.00" if i < 3 else "-100.00"),  # 3 wins ($450), 1 loss ($100)
            r_multiple=Decimal("1.50" if i < 3 else "-1.00"),
            fees_usd=Decimal("2.00"),
            slippage_pips=Decimal("0.10"),
            chart_image_url="",
            technical_indicators={},
            ai_post_mortem="",
        )
        for i in range(4)
    ]

    net_pnl, profit_factor, win_rate, total = calculate_performance_metrics(trades)
    assert net_pnl == Decimal("350.00")  # 450 - 100
    assert profit_factor == Decimal("4.50")  # 450 / 100
    assert win_rate == Decimal("75.00")  # 3/4
    assert total == 4
