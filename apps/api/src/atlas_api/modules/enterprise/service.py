"""Service implementation for Enterprise Features (Spec 10 §2, §5)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import uuid

from atlas_api.modules.enterprise.domain.models import (
    EnterpriseWebhook,
    Membership,
    Organization,
    OrgRiskPolicy,
    Team,
)
from atlas_api.modules.enterprise.domain.risk_hierarchy import validate_enterprise_order
from atlas_core.errors import NotFoundError, ValidationError


class EnterpriseService:
    """Orchestrates multi-tenant organizations, memberships, desk risk policies, and white-labeling."""

    def __init__(self) -> None:
        self._orgs: dict[str, Organization] = {}
        self._memberships: dict[str, Membership] = {}
        self._policies: dict[str, OrgRiskPolicy] = {}
        self._webhooks: dict[str, EnterpriseWebhook] = {}

    def create_organization(
        self,
        name: str,
        slug: str,
        plan_tier: str = "TEAM",
        max_seats: int = 10,
    ) -> Organization:
        for o in self._orgs.values():
            if o.slug == slug:
                raise ValidationError(f"Organization slug '{slug}' is already registered")

        org_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        org = Organization(
            id=org_id,
            name=name,
            slug=slug,
            plan_tier=plan_tier.upper(),
            custom_domain=None,
            white_label_settings={},
            max_seats=max_seats,
            created_at=now,
            updated_at=now,
        )
        self._orgs[org_id] = org

        # Seed default risk policy
        policy = OrgRiskPolicy(
            id=str(uuid.uuid4()),
            org_id=org_id,
            max_org_daily_drawdown_pct=Decimal("4.00"),
            max_portfolio_leverage=Decimal("5.00"),
            allowed_venues=("binance", "ibkr", "oanda"),
            dual_approval_threshold_usd=Decimal("100000.00"),
            emergency_halt_active=False,
            updated_at=now,
        )
        self._policies[org_id] = policy
        return org

    def get_organization(self, org_id: str) -> Organization:
        org = self._orgs.get(org_id)
        if not org:
            raise NotFoundError(f"Organization '{org_id}' not found")
        return org

    def invite_member(
        self,
        org_id: str,
        user_id: str,
        role: str = "Junior_Trader",
        max_lot_size: Decimal = Decimal("5.00"),
        max_risk_pct: Decimal = Decimal("0.50"),
        requires_dual: bool = False,
    ) -> Membership:
        self.get_organization(org_id)
        mem_id = str(uuid.uuid4())
        membership = Membership(
            id=mem_id,
            org_id=org_id,
            user_id=user_id,
            role=role,
            max_lot_size=max_lot_size,
            max_risk_per_trade_pct=max_risk_pct,
            requires_dual_approval=requires_dual,
            created_at=datetime.now(timezone.utc),
        )
        self._memberships[f"{org_id}:{user_id}"] = membership
        return membership

    def get_members(self, org_id: str) -> list[Membership]:
        return [m for m in self._memberships.values() if m.org_id == org_id]

    def get_member(self, org_id: str, user_id: str) -> Membership:
        membership = self._memberships.get(f"{org_id}:{user_id}")
        if not membership:
            raise NotFoundError(f"Member '{user_id}' not found in organization '{org_id}'")
        return membership

    def get_or_create_policy(self, org_id: str) -> OrgRiskPolicy:
        self.get_organization(org_id)
        if org_id not in self._policies:
            self._policies[org_id] = OrgRiskPolicy(
                id=str(uuid.uuid4()),
                org_id=org_id,
            )
        return self._policies[org_id]

    def update_policy(
        self,
        org_id: str,
        max_drawdown_pct: Decimal,
        max_leverage: Decimal,
        allowed_venues: list[str],
        dual_approval_threshold_usd: Decimal,
        emergency_halt_active: bool,
    ) -> OrgRiskPolicy:
        policy = self.get_or_create_policy(org_id)
        policy.max_org_daily_drawdown_pct = max_drawdown_pct
        policy.max_portfolio_leverage = max_leverage
        policy.allowed_venues = tuple(allowed_venues)
        policy.dual_approval_threshold_usd = dual_approval_threshold_usd
        policy.emergency_halt_active = emergency_halt_active
        policy.updated_at = datetime.now(timezone.utc)
        return policy

    def register_webhook(
        self,
        org_id: str,
        target_url: str,
        events: list[str],
    ) -> EnterpriseWebhook:
        self.get_organization(org_id)
        wh_id = str(uuid.uuid4())
        secret = uuid.uuid4().hex
        secret_hash = hashlib.sha256(secret.encode("utf-8")).hexdigest()

        webhook = EnterpriseWebhook(
            id=wh_id,
            org_id=org_id,
            target_url=target_url,
            secret_hash=secret_hash,
            subscribed_events=tuple(events),
            is_active=True,
            failure_count=0,
            created_at=datetime.now(timezone.utc),
        )
        self._webhooks[wh_id] = webhook
        return webhook

    def get_webhooks(self, org_id: str) -> list[EnterpriseWebhook]:
        return [w for w in self._webhooks.values() if w.org_id == org_id]

    def update_white_label(
        self,
        org_id: str,
        custom_domain: str,
        brand_name: str,
        logo_url: str | None,
        primary_color: str | None,
    ) -> Organization:
        org = self.get_organization(org_id)
        org.custom_domain = custom_domain
        org.white_label_settings = {
            "brand_name": brand_name,
            "logo_url": logo_url,
            "primary_color": primary_color or "#00F0FF",
        }
        org.updated_at = datetime.now(timezone.utc)
        return org

    def validate_order(
        self,
        org_id: str,
        user_id: str,
        lot_size: Decimal,
        risk_pct: Decimal,
        notional_usd: Decimal,
        senior_signature: str | None = None,
    ) -> tuple[bool, str]:
        policy = self.get_or_create_policy(org_id)
        membership = self.get_member(org_id, user_id)
        return validate_enterprise_order(
            policy=policy,
            membership=membership,
            lot_size=lot_size,
            risk_pct=risk_pct,
            notional_usd=notional_usd,
            senior_signature=senior_signature,
        )
