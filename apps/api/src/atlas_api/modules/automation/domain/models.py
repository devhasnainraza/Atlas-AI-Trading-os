"""Domain models for Trading Automation (Spec 06 §2, §5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
import uuid


@dataclass
class AutomationMandate:
    id: str
    user_id: str
    account_id: str
    mode: str  # MANUAL | SEMI_AUTOMATIC | FULLY_AUTOMATIC
    allowed_symbols: tuple[str, ...]
    max_capital_risk_pct: Decimal
    daily_loss_limit_usd: Decimal
    max_open_positions: int
    news_protection: bool
    session_restrictions: tuple[str, ...]
    mandate_signature: str
    is_active: bool
    expires_at: datetime
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PositionGuardState:
    id: str
    position_id: str
    account_id: str
    user_id: str
    symbol: str
    side: str  # LONG | SHORT
    entry_price: Decimal
    current_stop_loss: Decimal
    initial_stop_loss: Decimal
    tp1_price: Decimal
    tp2_price: Decimal
    tp3_price: Decimal
    breakeven_offset: Decimal = Decimal("0")
    breakeven_reached: bool = False
    tp1_filled: bool = False
    tp2_filled: bool = False
    trailing_active: bool = False
    trailing_step_type: str = "FIXED_PIPS"  # ATR | CHANDELIER | FIXED_PIPS
    trailing_distance: Decimal = Decimal("0")
    highest_price_seen: Decimal = Decimal("0")
    lowest_price_seen: Decimal = Decimal("0")
    status: str = "active"  # active | closed | cancelled
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class CircuitBreakerEvent:
    id: str
    user_id: str
    account_id: str
    breaker_type: str  # DAILY_DRAWDOWN | CONSECUTIVE_LOSS | NEWS_LOCKOUT | VENUE_LATENCY | EMERGENCY_PANIC
    threshold_value: Decimal
    observed_value: Decimal
    actions_taken: tuple[str, ...]
    triggered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reset_at: datetime | None = None


@dataclass(frozen=True)
class AutomationStatus:
    user_id: str
    mode: str
    active_mandates_count: int
    circuit_breaker_active: bool
    circuit_breaker_reason: str | None
    daily_loss_usd: Decimal
    daily_loss_limit_usd: Decimal
    protected_positions_count: int
