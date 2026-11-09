"""API contract tests for Enterprise Features module (Spec 10 §9)."""

from decimal import Decimal
import pytest
from atlas_api.testing import build_test_app, make_client


@pytest.mark.asyncio
async def test_organization_and_membership_lifecycle_api():
    app = build_test_app()
    async with make_client(app) as client:
        # 1. Provision organization
        org_resp = await client.post(
            "/v1/enterprise/organizations",
            json={
                "name": "Apex Quant Capital",
                "slug": "apex-quant",
                "plan_tier": "INSTITUTIONAL",
                "max_seats": 25,
            },
        )
        assert org_resp.status_code == 200
        org_data = org_resp.json()
        assert org_data["name"] == "Apex Quant Capital"
        assert org_data["slug"] == "apex-quant"
        org_id = org_data["id"]

        # 2. Invite Junior Trader
        invite_resp = await client.post(
            f"/v1/enterprise/organizations/{org_id}/members",
            json={
                "user_id": "trader-alex-01",
                "role": "Junior_Trader",
                "max_lot_size": "2.00",
                "max_risk_per_trade_pct": "0.50",
                "requires_dual_approval": True,
            },
        )
        assert invite_resp.status_code == 200
        mem_data = invite_resp.json()
        assert mem_data["role"] == "Junior_Trader"
        assert mem_data["requires_dual_approval"] is True

        # 3. List members
        list_resp = await client.get(f"/v1/enterprise/organizations/{org_id}/members")
        assert list_resp.status_code == 200
        members = list_resp.json()
        assert any(m["user_id"] == "trader-alex-01" for m in members)


@pytest.mark.asyncio
async def test_organization_policy_and_webhooks_api():
    app = build_test_app()
    async with make_client(app) as client:
        # Provision org first
        org_resp = await client.post(
            "/v1/enterprise/organizations",
            json={"name": "Prop Trading Desk Alpha", "slug": "desk-alpha"},
        )
        org_id = org_resp.json()["id"]

        # Get risk policy
        pol_resp = await client.get(f"/v1/enterprise/organizations/{org_id}/policy")
        assert pol_resp.status_code == 200
        assert Decimal(str(pol_resp.json()["max_org_daily_drawdown_pct"])) == Decimal("4.00")

        # Update risk policy
        update_pol_resp = await client.put(
            f"/v1/enterprise/organizations/{org_id}/policy",
            json={
                "max_org_daily_drawdown_pct": "3.50",
                "max_portfolio_leverage": "4.00",
                "allowed_venues": ["binance", "ibkr"],
                "dual_approval_threshold_usd": "75000.00",
                "emergency_halt_active": False,
            },
        )
        assert update_pol_resp.status_code == 200
        assert Decimal(str(update_pol_resp.json()["max_org_daily_drawdown_pct"])) == Decimal("3.50")

        # Register Webhook
        wh_resp = await client.post(
            f"/v1/enterprise/organizations/{org_id}/webhooks",
            json={
                "target_url": "https://api.deskalpha.internal/hooks/atlas",
                "subscribed_events": ["trade.executed", "risk.limit_breached"],
            },
        )
        assert wh_resp.status_code == 200
        wh_data = wh_resp.json()
        assert "deskalpha.internal" in wh_data["target_url"]
        assert wh_data["is_active"] is True

        # White-Label config
        wl_resp = await client.put(
            f"/v1/enterprise/organizations/{org_id}/white-label",
            json={
                "custom_domain": "trading.deskalpha.com",
                "brand_name": "Desk Alpha OS",
                "logo_url": "https://cdn.deskalpha.com/logo.png",
                "primary_color": "#00FF66",
            },
        )
        assert wl_resp.status_code == 200
        assert wl_resp.json()["custom_domain"] == "trading.deskalpha.com"
