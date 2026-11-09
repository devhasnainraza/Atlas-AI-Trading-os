"""Unit tests for Circuit Breaker and News Embargo evaluation (Spec 06 §2, §4)."""

from datetime import datetime, timezone
from decimal import Decimal
import pytest
from atlas_api.modules.automation.domain.circuit_breaker import CircuitBreakerEvaluator
from atlas_api.modules.automation.domain.models import AutomationMandate


@pytest.fixture
def sample_mandate():
    return AutomationMandate(
        id="mandate-1",
        user_id="trader-1",
        account_id="acc-1",
        mode="FULLY_AUTOMATIC",
        allowed_symbols=("EUR/USD", "BTC/USDT"),
        max_capital_risk_pct=Decimal("1.50"),
        daily_loss_limit_usd=Decimal("300.00"),
        max_open_positions=3,
        news_protection=True,
        session_restrictions=("LONDON", "NEW_YORK"),
        mandate_signature="sig-authorized-123",
        is_active=True,
        expires_at=datetime.now(timezone.utc),
    )


def test_trade_intent_authorized_when_conditions_met(sample_mandate):
    evaluator = CircuitBreakerEvaluator()
    allowed, reason = evaluator.check_trade_intent(
        mandate=sample_mandate,
        symbol="BTC/USDT",
        risk_pct=Decimal("1.00"),
        daily_loss_usd=Decimal("50.00"),
        minutes_to_high_impact_news=45,
        current_session="LONDON",
    )
    assert allowed is True
    assert reason == "AUTHORIZED"


def test_trade_intent_rejected_on_daily_drawdown_limit(sample_mandate):
    evaluator = CircuitBreakerEvaluator()
    allowed, reason = evaluator.check_trade_intent(
        mandate=sample_mandate,
        symbol="BTC/USDT",
        risk_pct=Decimal("1.00"),
        daily_loss_usd=Decimal("320.00"),  # Exceeds limit of 300.00
    )
    assert allowed is False
    assert reason == "DAILY_DRAWDOWN_LIMIT_EXCEEDED"

    # Subsequent intent should be blocked by active tripped circuit breaker
    tripped, event = evaluator.is_tripped("trader-1")
    assert tripped is True
    assert event.breaker_type == "DAILY_DRAWDOWN"

    allowed2, reason2 = evaluator.check_trade_intent(
        mandate=sample_mandate,
        symbol="BTC/USDT",
        risk_pct=Decimal("0.50"),
        daily_loss_usd=Decimal("50.00"),
    )
    assert allowed2 is False
    assert "CIRCUIT_BREAKER_ACTIVE" in reason2


def test_news_protection_embargo_lockout(sample_mandate):
    evaluator = CircuitBreakerEvaluator()
    # 10 minutes prior to CPI announcement (within 15m window)
    allowed, reason = evaluator.check_trade_intent(
        mandate=sample_mandate,
        symbol="EUR/USD",
        risk_pct=Decimal("1.00"),
        daily_loss_usd=Decimal("0.00"),
        minutes_to_high_impact_news=10,
    )
    assert allowed is False
    assert "NEWS_EMBARGO_LOCKOUT" in reason


def test_symbol_not_whitelisted_in_mandate(sample_mandate):
    evaluator = CircuitBreakerEvaluator()
    allowed, reason = evaluator.check_trade_intent(
        mandate=sample_mandate,
        symbol="DOGE/USDT",
        risk_pct=Decimal("1.00"),
        daily_loss_usd=Decimal("0.00"),
    )
    assert allowed is False
    assert "SYMBOL_NOT_AUTHORIZED_IN_MANDATE" in reason


def test_risk_exceeds_mandate_cap(sample_mandate):
    evaluator = CircuitBreakerEvaluator()
    allowed, reason = evaluator.check_trade_intent(
        mandate=sample_mandate,
        symbol="BTC/USDT",
        risk_pct=Decimal("2.50"),  # Exceeds 1.50% cap
        daily_loss_usd=Decimal("0.00"),
    )
    assert allowed is False
    assert "RISK_EXCEEDS_MANDATE_CAP" in reason
