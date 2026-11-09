"""Enterprise Features API router and endpoints (Spec 10 §2, §9)."""

from __future__ import annotations

from dataclasses import dataclass
from fastapi import APIRouter, Depends, Path, Request

from atlas_api.modules.enterprise.domain.models import (
    EnterpriseWebhook,
    Membership,
    Organization,
    OrgRiskPolicy,
)
from atlas_api.modules.enterprise.schemas import (
    CreateOrganizationRequest,
    EnterpriseWebhookResponse,
    InviteMemberRequest,
    MembershipResponse,
    OrganizationResponse,
    OrgRiskPolicyResponse,
    RegisterEnterpriseWebhookRequest,
    UpdateOrgRiskPolicyRequest,
    WhiteLabelConfigRequest,
    WhiteLabelConfigResponse,
)
from atlas_api.modules.enterprise.service import EnterpriseService
from atlas_core.errors import InternalError

router = APIRouter(prefix="/enterprise", tags=["enterprise"])

STATE_KEY = "enterprise_context"


@dataclass(frozen=True)
class EnterpriseModuleContext:
    service: EnterpriseService


def get_enterprise_context(request: Request) -> EnterpriseModuleContext:
    context = getattr(request.app.state, STATE_KEY, None)
    if not isinstance(context, EnterpriseModuleContext):
        raise InternalError(
            internal_context={"detail": "enterprise module accessed before composition"}
        )
    return context


def get_enterprise_service(
    context: EnterpriseModuleContext = Depends(get_enterprise_context),
) -> EnterpriseService:
    return context.service


def _format_org(org: Organization) -> OrganizationResponse:
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        plan_tier=org.plan_tier,
        custom_domain=org.custom_domain,
        max_seats=org.max_seats,
        created_at=org.created_at.isoformat(),
    )


def _format_member(mem: Membership) -> MembershipResponse:
    return MembershipResponse(
        id=mem.id,
        org_id=mem.org_id,
        user_id=mem.user_id,
        role=mem.role,
        max_lot_size=mem.max_lot_size,
        max_risk_per_trade_pct=mem.max_risk_per_trade_pct,
        requires_dual_approval=mem.requires_dual_approval,
        created_at=mem.created_at.isoformat(),
    )


def _format_policy(p: OrgRiskPolicy) -> OrgRiskPolicyResponse:
    return OrgRiskPolicyResponse(
        org_id=p.org_id,
        max_org_daily_drawdown_pct=p.max_org_daily_drawdown_pct,
        max_portfolio_leverage=p.max_portfolio_leverage,
        allowed_venues=list(p.allowed_venues),
        dual_approval_threshold_usd=p.dual_approval_threshold_usd,
        emergency_halt_active=p.emergency_halt_active,
    )


def _format_webhook(wh: EnterpriseWebhook) -> EnterpriseWebhookResponse:
    return EnterpriseWebhookResponse(
        id=wh.id,
        org_id=wh.org_id,
        target_url=wh.target_url,
        subscribed_events=list(wh.subscribed_events),
        is_active=wh.is_active,
        created_at=wh.created_at.isoformat(),
    )


@router.post("/organizations", response_model=OrganizationResponse)
async def create_organization(
    body: CreateOrganizationRequest,
    service: EnterpriseService = Depends(get_enterprise_service),
) -> OrganizationResponse:
    """Provisions a new multi-tenant enterprise organization."""
    org = service.create_organization(
        name=body.name,
        slug=body.slug,
        plan_tier=body.plan_tier,
        max_seats=body.max_seats,
    )
    return _format_org(org)


@router.get("/organizations/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: str = Path(..., description="Organization UUID"),
    service: EnterpriseService = Depends(get_enterprise_service),
) -> OrganizationResponse:
    """Retrieves organization details."""
    org = service.get_organization(org_id=org_id)
    return _format_org(org)


@router.post("/organizations/{org_id}/members", response_model=MembershipResponse)
async def invite_member(
    org_id: str = Path(..., description="Organization UUID"),
    body: InviteMemberRequest = ...,
    service: EnterpriseService = Depends(get_enterprise_service),
) -> MembershipResponse:
    """Invites a trader or officer to the organization with assigned risk ceilings."""
    member = service.invite_member(
        org_id=org_id,
        user_id=body.user_id,
        role=body.role,
        max_lot_size=body.max_lot_size,
        max_risk_pct=body.max_risk_per_trade_pct,
        requires_dual=body.requires_dual_approval,
    )
    return _format_member(member)


@router.get("/organizations/{org_id}/members", response_model=list[MembershipResponse])
async def list_members(
    org_id: str = Path(..., description="Organization UUID"),
    service: EnterpriseService = Depends(get_enterprise_service),
) -> list[MembershipResponse]:
    """Lists team members and role limits for the organization."""
    members = service.get_members(org_id=org_id)
    return [_format_member(m) for m in members]


@router.get("/organizations/{org_id}/policy", response_model=OrgRiskPolicyResponse)
async def get_risk_policy(
    org_id: str = Path(..., description="Organization UUID"),
    service: EnterpriseService = Depends(get_enterprise_service),
) -> OrgRiskPolicyResponse:
    """Returns top-down desk risk governance policies."""
    policy = service.get_or_create_policy(org_id=org_id)
    return _format_policy(policy)


@router.put("/organizations/{org_id}/policy", response_model=OrgRiskPolicyResponse)
async def update_risk_policy(
    org_id: str = Path(..., description="Organization UUID"),
    body: UpdateOrgRiskPolicyRequest = ...,
    service: EnterpriseService = Depends(get_enterprise_service),
) -> OrgRiskPolicyResponse:
    """Updates organization-wide loss limits and dual-approval thresholds."""
    policy = service.update_policy(
        org_id=org_id,
        max_drawdown_pct=body.max_org_daily_drawdown_pct,
        max_leverage=body.max_portfolio_leverage,
        allowed_venues=body.allowed_venues,
        dual_approval_threshold_usd=body.dual_approval_threshold_usd,
        emergency_halt_active=body.emergency_halt_active,
    )
    return _format_policy(policy)


@router.post("/organizations/{org_id}/webhooks", response_model=EnterpriseWebhookResponse)
async def register_webhook(
    org_id: str = Path(..., description="Organization UUID"),
    body: RegisterEnterpriseWebhookRequest = ...,
    service: EnterpriseService = Depends(get_enterprise_service),
) -> EnterpriseWebhookResponse:
    """Subscribes an HTTPS target to institutional real-time event webhooks."""
    webhook = service.register_webhook(
        org_id=org_id,
        target_url=body.target_url,
        events=body.subscribed_events,
    )
    return _format_webhook(webhook)


@router.get("/organizations/{org_id}/webhooks", response_model=list[EnterpriseWebhookResponse])
async def list_webhooks(
    org_id: str = Path(..., description="Organization UUID"),
    service: EnterpriseService = Depends(get_enterprise_service),
) -> list[EnterpriseWebhookResponse]:
    """Lists registered enterprise webhooks."""
    webhooks = service.get_webhooks(org_id=org_id)
    return [_format_webhook(w) for w in webhooks]


@router.put("/organizations/{org_id}/white-label", response_model=WhiteLabelConfigResponse)
async def update_white_label(
    org_id: str = Path(..., description="Organization UUID"),
    body: WhiteLabelConfigRequest = ...,
    service: EnterpriseService = Depends(get_enterprise_service),
) -> WhiteLabelConfigResponse:
    """Configures white-label custom domain and corporate branding."""
    org = service.update_white_label(
        org_id=org_id,
        custom_domain=body.custom_domain,
        brand_name=body.brand_name,
        logo_url=body.logo_url,
        primary_color=body.primary_color,
    )
    return WhiteLabelConfigResponse(
        org_id=org.id,
        custom_domain=org.custom_domain or body.custom_domain,
        brand_name=body.brand_name,
        logo_url=body.logo_url,
        primary_color=body.primary_color,
    )
