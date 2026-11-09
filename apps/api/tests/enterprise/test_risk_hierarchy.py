"""Unit tests for enterprise hierarchical risk policy and dual approval (Spec 10 §2, §4)."""

from datetime import datetime, timezone
from decimal import Decimal
import pytest
from atlas_api.modules.enterprise.domain.models import Membership, OrgRiskPolicy
from atlas_api.modules.enterprise.domain.risk_hierarchy import validate_enterprise_order


@pytest.fixture
def sample_desk_policy():
    return OrgRiskPolicy(
        id="policy-1",
        org_id="org-hedgefund-01",
        max_org_daily_drawdown_pct=Decimal("4.00"),
        max_portfolio_leverage=Decimal("5.00"),
        allowed_venues=("binance", "ibkr", "oanda"),
        dual_approval_threshold_usd=Decimal("50000.00"),
        emergency_halt_active=False,
    )


@pytest.fixture
def junior_member():
    return Membership(
        id="mem-junior-1",
        org_id="org-hedgefund-01",
        user_id="trader-junior-01",
        role="Junior_Trader",
        max_lot_size=Decimal("2.00"),
        max_risk_per_trade_pct=Decimal("0.50"),
        requires_dual_approval=False,
    )


def test_order_authorized_when_within_member_bounds(sample_desk_policy, junior_member):
    allowed, reason = validate_enterprise_order(
        policy=sample_desk_policy,
        membership=junior_member,
        lot_size=Decimal("1.00"),
        risk_pct=Decimal("0.40"),
        notional_usd=Decimal("25000.00"),
    )
    assert allowed is True
    assert reason == "AUTHORIZED"


def test_order_rejected_on_emergency_halt(sample_desk_policy, junior_member):
    sample_desk_policy.emergency_halt_active = True
    allowed, reason = validate_enterprise_order(
        policy=sample_desk_policy,
        membership=junior_member,
        lot_size=Decimal("1.00"),
        risk_pct=Decimal("0.20"),
        notional_usd=Decimal("10000.00"),
    )
    assert allowed is False
    assert reason == "ORGANIZATION_EMERGENCY_HALT_ACTIVE"


def test_order_rejected_when_exceeding_risk_or_lot_cap(sample_desk_policy, junior_member):
    # Exceeding risk cap (0.50%)
    allowed_risk, reason_risk = validate_enterprise_order(
        policy=sample_desk_policy,
        membership=junior_member,
        lot_size=Decimal("1.00"),
        risk_pct=Decimal("0.80"),
        notional_usd=Decimal("10000.00"),
    )
    assert allowed_risk is False
    assert "ORDER_EXCEEDS_MEMBER_RISK_CAP" in reason_risk

    # Exceeding lot cap (2.00 lots)
    allowed_lot, reason_lot = validate_enterprise_order(
        policy=sample_desk_policy,
        membership=junior_member,
        lot_size=Decimal("3.50"),
        risk_pct=Decimal("0.30"),
        notional_usd=Decimal("10000.00"),
    )
    assert allowed_lot is False
    assert "ORDER_EXCEEDS_MEMBER_LOT_CAP" in reason_lot


def test_dual_approval_escalation(sample_desk_policy, junior_member):
    # Notional USD >= 50,000 threshold requires senior signature
    allowed, reason = validate_enterprise_order(
        policy=sample_desk_policy,
        membership=junior_member,
        lot_size=Decimal("1.50"),
        risk_pct=Decimal("0.40"),
        notional_usd=Decimal("75000.00"),
        senior_signature=None,
    )
    assert allowed is False
    assert "DUAL_APPROVAL_REQUIRED_FROM_SENIOR_TRADER" in reason

    # When senior signature provided -> Authorized
    allowed_approved, reason_approved = validate_enterprise_order(
        policy=sample_desk_policy,
        membership=junior_member,
        lot_size=Decimal("1.50"),
        risk_pct=Decimal("0.40"),
        notional_usd=Decimal("75000.00"),
        senior_signature="sig-senior-trader-approved",
    )
    assert allowed_approved is True
    assert reason_approved == "AUTHORIZED"
