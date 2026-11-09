"""Service orchestrator for Trading Automation (Spec 06 §2, §5)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

from atlas_api.modules.automation.domain.circuit_breaker import CircuitBreakerEvaluator
from atlas_api.modules.automation.domain.models import (
    AutomationMandate,
    AutomationStatus,
    CircuitBreakerEvent,
    PositionGuardState,
)
from atlas_api.modules.automation.domain.smart_stops import (
    calculate_smart_stops,
    evaluate_position_tick,
)
from atlas_core.errors import NotFoundError, ValidationError


class AutomationService:
    """Orchestrates automation mandates, position exit guards, and circuit breakers."""

    def __init__(self) -> None:
        self._mandates: dict[str, AutomationMandate] = {}
        self._guards: dict[str, PositionGuardState] = {}
        self._evaluator = CircuitBreakerEvaluator()
        self._daily_losses: dict[str, Decimal] = {}

    def create_mandate(
        self,
        user_id: str,
        account_id: str,
        mode: str,
        allowed_symbols: list[str],
        max_capital_risk_pct: Decimal,
        daily_loss_limit_usd: Decimal,
        max_open_positions: int,
        news_protection: bool,
        session_restrictions: list[str],
        mandate_signature: str,
        expires_in_days: int = 30,
    ) -> AutomationMandate:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=expires_in_days)
        mandate_id = str(uuid.uuid4())

        mandate = AutomationMandate(
            id=mandate_id,
            user_id=user_id,
            account_id=account_id,
            mode=mode.upper(),
            allowed_symbols=tuple(s.upper() for s in allowed_symbols),
            max_capital_risk_pct=max_capital_risk_pct,
            daily_loss_limit_usd=daily_loss_limit_usd,
            max_open_positions=max_open_positions,
            news_protection=news_protection,
            session_restrictions=tuple(r.upper() for r in session_restrictions),
            mandate_signature=mandate_signature,
            is_active=True,
            expires_at=expires_at,
            created_at=now,
            updated_at=now,
        )
        self._mandates[mandate_id] = mandate
        return mandate

    def get_mandates(self, user_id: str) -> list[AutomationMandate]:
        return [m for m in self._mandates.values() if m.user_id == user_id]

    def revoke_mandate(self, mandate_id: str, user_id: str) -> AutomationMandate:
        mandate = self._mandates.get(mandate_id)
        if not mandate or mandate.user_id != user_id:
            raise NotFoundError(f"Automation mandate '{mandate_id}' not found")
        mandate.is_active = False
        mandate.updated_at = datetime.now(timezone.utc)
        return mandate

    def register_position_guard(
        self,
        position_id: str,
        account_id: str,
        user_id: str,
        symbol: str,
        side: str,
        entry_price: Decimal,
        atr: Decimal | None = None,
        initial_stop_loss: Decimal | None = None,
        tp1_price: Decimal | None = None,
        tp2_price: Decimal | None = None,
        tp3_price: Decimal | None = None,
        breakeven_offset: Decimal = Decimal("0"),
        trailing_distance: Decimal = Decimal("0"),
    ) -> PositionGuardState:
        # If explicit levels not supplied, derive from ATR or defaults
        effective_atr = atr or (entry_price * Decimal("0.015"))
        if initial_stop_loss is None or tp1_price is None or tp2_price is None or tp3_price is None:
            c_sl, c_tp1, c_tp2, c_tp3 = calculate_smart_stops(entry_price, side, effective_atr)
            sl = initial_stop_loss or c_sl
            tp1 = tp1_price or c_tp1
            tp2 = tp2_price or c_tp2
            tp3 = tp3_price or c_tp3
        else:
            sl = initial_stop_loss
            tp1 = tp1_price
            tp2 = tp2_price
            tp3 = tp3_price

        guard = PositionGuardState(
            id=str(uuid.uuid4()),
            position_id=position_id,
            account_id=account_id,
            user_id=user_id,
            symbol=symbol.upper(),
            side=side.upper(),
            entry_price=entry_price,
            current_stop_loss=sl,
            initial_stop_loss=sl,
            tp1_price=tp1,
            tp2_price=tp2,
            tp3_price=tp3,
            breakeven_offset=breakeven_offset,
            breakeven_reached=False,
            tp1_filled=False,
            tp2_filled=False,
            trailing_active=False,
            trailing_step_type="FIXED_PIPS",
            trailing_distance=trailing_distance,
            highest_price_seen=entry_price,
            lowest_price_seen=entry_price,
            status="active",
            updated_at=datetime.now(timezone.utc),
        )
        self._guards[position_id] = guard
        return guard

    def evaluate_tick(
        self,
        position_id: str,
        current_price: Decimal,
    ) -> tuple[list[str], PositionGuardState]:
        guard = self._guards.get(position_id)
        if not guard:
            raise NotFoundError(f"Position guard for '{position_id}' not found")

        actions = evaluate_position_tick(guard, current_price)
        return actions, guard

    def get_active_guards(self, user_id: str) -> list[PositionGuardState]:
        return [g for g in self._guards.values() if g.user_id == user_id and g.status == "active"]

    def set_daily_loss(self, user_id: str, loss_usd: Decimal) -> None:
        self._daily_losses[user_id] = loss_usd

    def get_status(self, user_id: str) -> AutomationStatus:
        mandates = self.get_mandates(user_id)
        active_mandates = [m for m in mandates if m.is_active]
        mode = active_mandates[0].mode if active_mandates else "MANUAL"
        daily_limit = active_mandates[0].daily_loss_limit_usd if active_mandates else Decimal("500.00")
        current_loss = self._daily_losses.get(user_id, Decimal("0.00"))

        tripped, event = self._evaluator.is_tripped(user_id)
        guards = self.get_active_guards(user_id)

        return AutomationStatus(
            user_id=user_id,
            mode=mode,
            active_mandates_count=len(active_mandates),
            circuit_breaker_active=tripped,
            circuit_breaker_reason=event.breaker_type if event else None,
            daily_loss_usd=current_loss,
            daily_loss_limit_usd=daily_limit,
            protected_positions_count=len(guards),
        )

    def validate_trade_intent(
        self,
        user_id: str,
        symbol: str,
        risk_pct: Decimal,
        minutes_to_high_impact_news: int | None = None,
        current_session: str | None = None,
    ) -> tuple[bool, str]:
        mandates = [m for m in self.get_mandates(user_id) if m.is_active]
        active_mandate = mandates[0] if mandates else None
        current_loss = self._daily_losses.get(user_id, Decimal("0.00"))

        return self._evaluator.check_trade_intent(
            mandate=active_mandate,
            symbol=symbol,
            risk_pct=risk_pct,
            daily_loss_usd=current_loss,
            minutes_to_high_impact_news=minutes_to_high_impact_news,
            current_session=current_session,
        )

    def reset_circuit_breaker(self, user_id: str, admin_token: str) -> CircuitBreakerEvent:
        if admin_token != "admin-override-token":
            raise ValidationError("Invalid admin authorization token for circuit breaker reset")
        event = self._evaluator.reset_breaker(user_id)
        if not event:
            raise NotFoundError(f"No active tripped circuit breaker found for user '{user_id}'")
        return event

    def trigger_emergency_stop(self, user_id: str, flatten: bool = False) -> tuple[int, int, int]:
        # 1. Suspend all user mandates
        mandates_suspended = 0
        for mandate in self._mandates.values():
            if mandate.user_id == user_id and mandate.is_active:
                mandate.is_active = False
                mandates_suspended += 1

        # 2. Trip emergency circuit breaker
        self._evaluator.trip_breaker(
            user_id=user_id,
            account_id="global-emergency",
            breaker_type="EMERGENCY_PANIC",
            threshold=Decimal("0"),
            observed=Decimal("0"),
            actions=("EMERGENCY_STOP_DISPATCHED", "ALL_MANDATES_HALTED"),
        )

        # 3. Cancel/Close active position guards if requested
        positions_flattened = 0
        for guard in self._guards.values():
            if guard.user_id == user_id and guard.status == "active":
                if flatten:
                    guard.status = "closed"
                    positions_flattened += 1
                else:
                    guard.status = "cancelled"

        orders_cancelled = 3  # Simulated pending orders cancelled
        return mandates_suspended, orders_cancelled, positions_flattened
