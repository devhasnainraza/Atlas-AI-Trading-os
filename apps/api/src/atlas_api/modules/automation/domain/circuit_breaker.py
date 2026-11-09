"""Circuit breaker and embargo evaluation logic (Spec 06 §2, §4)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import uuid

from atlas_api.modules.automation.domain.models import AutomationMandate, CircuitBreakerEvent


class CircuitBreakerEvaluator:
    """Evaluates trading permission against user mandates and protective circuit breakers."""

    def __init__(self) -> None:
        self._tripped_breakers: dict[str, CircuitBreakerEvent] = {}

    def is_tripped(self, user_id: str) -> tuple[bool, CircuitBreakerEvent | None]:
        event = self._tripped_breakers.get(user_id)
        if event and event.reset_at is None:
            return True, event
        return False, None

    def trip_breaker(
        self,
        user_id: str,
        account_id: str,
        breaker_type: str,
        threshold: Decimal,
        observed: Decimal,
        actions: tuple[str, ...],
    ) -> CircuitBreakerEvent:
        event = CircuitBreakerEvent(
            id=str(uuid.uuid4()),
            user_id=user_id,
            account_id=account_id,
            breaker_type=breaker_type,
            threshold_value=threshold,
            observed_value=observed,
            actions_taken=actions,
            triggered_at=datetime.now(timezone.utc),
            reset_at=None,
        )
        self._tripped_breakers[user_id] = event
        return event

    def reset_breaker(self, user_id: str) -> CircuitBreakerEvent | None:
        event = self._tripped_breakers.get(user_id)
        if not event or event.reset_at is not None:
            return None

        updated_event = CircuitBreakerEvent(
            id=event.id,
            user_id=event.user_id,
            account_id=event.account_id,
            breaker_type=event.breaker_type,
            threshold_value=event.threshold_value,
            observed_value=event.observed_value,
            actions_taken=(*event.actions_taken, "MANUAL_RESET_AUTHORIZED"),
            triggered_at=event.triggered_at,
            reset_at=datetime.now(timezone.utc),
        )
        self._tripped_breakers[user_id] = updated_event
        return updated_event

    def check_trade_intent(
        self,
        mandate: AutomationMandate | None,
        symbol: str,
        risk_pct: Decimal,
        daily_loss_usd: Decimal,
        minutes_to_high_impact_news: int | None = None,
        current_session: str | None = None,
    ) -> tuple[bool, str]:
        """Validates whether a trade intent can proceed through automation gates.

        Returns (allowed: bool, reason: str).
        """
        if mandate is None or not mandate.is_active:
            return False, "NO_ACTIVE_AUTOMATION_MANDATE"

        # 1. Existing circuit breaker trip check
        tripped, event = self.is_tripped(mandate.user_id)
        if tripped and event:
            return False, f"CIRCUIT_BREAKER_ACTIVE:{event.breaker_type}"

        # 2. Daily Loss / Drawdown limit check
        if daily_loss_usd >= mandate.daily_loss_limit_usd:
            self.trip_breaker(
                user_id=mandate.user_id,
                account_id=mandate.account_id,
                breaker_type="DAILY_DRAWDOWN",
                threshold=mandate.daily_loss_limit_usd,
                observed=daily_loss_usd,
                actions=("HALT_MANDATES", "CANCEL_PENDING_ORDERS"),
            )
            return False, "DAILY_DRAWDOWN_LIMIT_EXCEEDED"

        # 3. Symbol authorization check
        if symbol not in mandate.allowed_symbols:
            return False, f"SYMBOL_NOT_AUTHORIZED_IN_MANDATE:{symbol}"

        # 4. Capital risk cap per trade check
        if risk_pct > mandate.max_capital_risk_pct:
            return False, f"RISK_EXCEEDS_MANDATE_CAP:{risk_pct}%>{mandate.max_capital_risk_pct}%"

        # 5. Macroeconomic News Protection Embargo Check (15 min window before/after)
        if mandate.news_protection and minutes_to_high_impact_news is not None:
            if abs(minutes_to_high_impact_news) <= 15:
                return False, f"NEWS_EMBARGO_LOCKOUT:High impact release in {minutes_to_high_impact_news}m"

        # 6. Session restriction check
        if mandate.session_restrictions and current_session is not None:
            if current_session not in mandate.session_restrictions:
                return False, f"SESSION_OUTSIDE_MANDATE_HOURS:{current_session}"

        return True, "AUTHORIZED"
