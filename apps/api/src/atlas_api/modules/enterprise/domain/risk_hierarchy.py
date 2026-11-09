"""Hierarchical risk policy evaluation and dual-approval enforcement (Spec 10 §2, §4)."""

from __future__ import annotations

from decimal import Decimal
from atlas_api.modules.enterprise.domain.models import Membership, OrgRiskPolicy


def validate_enterprise_order(
    policy: OrgRiskPolicy,
    membership: Membership,
    lot_size: Decimal,
    risk_pct: Decimal,
    notional_usd: Decimal,
    senior_signature: str | None = None,
) -> tuple[bool, str]:
    """Evaluates hierarchical pre-trade risk limits and dual-approval gates."""
    # 1. Organization emergency halt
    if policy.emergency_halt_active:
        return False, "ORGANIZATION_EMERGENCY_HALT_ACTIVE"

    # 2. Member personal risk cap
    if risk_pct > membership.max_risk_per_trade_pct:
        return (
            False,
            f"ORDER_EXCEEDS_MEMBER_RISK_CAP: {risk_pct}% > allowed {membership.max_risk_per_trade_pct}%",
        )

    # 3. Member personal lot size cap
    if lot_size > membership.max_lot_size:
        return (
            False,
            f"ORDER_EXCEEDS_MEMBER_LOT_CAP: {lot_size} lots > allowed {membership.max_lot_size} lots",
        )

    # 4. Dual-approval requirement
    needs_dual = (
        membership.requires_dual_approval
        or notional_usd >= policy.dual_approval_threshold_usd
    )
    if needs_dual and not senior_signature:
        return (
            False,
            "DUAL_APPROVAL_REQUIRED_FROM_SENIOR_TRADER: Escalated order requires secondary supervisor signature",
        )

    return True, "AUTHORIZED"
