"""API contract tests for Communication Platform module (Spec 08 §9)."""

import pytest
from atlas_api.testing import build_test_app, make_client


@pytest.mark.asyncio
async def test_channels_and_preferences_api():
    app = build_test_app()
    async with make_client(app) as client:
        # Register Telegram channel
        reg_resp = await client.post(
            "/v1/communication/channels",
            json={
                "channel_type": "TELEGRAM",
                "destination": "987654321",
                "min_priority": "P1",
            },
        )
        assert reg_resp.status_code == 200
        chan_data = reg_resp.json()
        assert chan_data["channel_type"] == "TELEGRAM"
        assert chan_data["is_enabled"] is True
        chan_id = chan_data["id"]

        # List channels
        list_resp = await client.get("/v1/communication/channels")
        assert list_resp.status_code == 200
        assert any(c["id"] == chan_id for c in list_resp.json())

        # Update preferences
        pref_resp = await client.put(
            "/v1/communication/preferences",
            json={
                "quiet_hours_enabled": True,
                "quiet_hours_start": "23:00:00",
                "quiet_hours_end": "07:00:00",
                "timezone": "America/New_York",
                "emergency_phone": "+1234567890",
            },
        )
        assert pref_resp.status_code == 200
        p_data = pref_resp.json()
        assert p_data["quiet_hours_enabled"] is True
        assert p_data["timezone"] == "America/New_York"


@pytest.mark.asyncio
async def test_dispatch_and_action_execution_api():
    app = build_test_app()
    async with make_client(app) as client:
        # 1. Dispatch trade approval notification
        dispatch_resp = await client.post(
            "/v1/communication/dispatch",
            json={
                "priority": "P1",
                "title": "Trade Setup Proposal: BTC/USDT",
                "body": "78.5% confidence Long setup detected.",
                "action_type": "APPROVE_TRADE",
                "action_payload": {"proposal_id": "prop-uuid-99"},
            },
        )
        assert dispatch_resp.status_code == 200
        disp_data = dispatch_resp.json()
        assert disp_data["status"] == "DELIVERED"
        assert disp_data["action_token"] is not None
        assert "/actions/" in disp_data["action_url"]

        token_hash = disp_data["action_url"].split("/actions/")[1].split("/execute")[0]

        # 2. Execute 1-click action button
        exec_resp = await client.post(f"/v1/communication/actions/{token_hash}/execute")
        assert exec_resp.status_code == 200
        exec_data = exec_resp.json()
        assert exec_data["status"] == "EXECUTED"
        assert exec_data["action_type"] == "APPROVE_TRADE"
        assert "prop-uuid-99" in exec_data["message"]

        # 3. Second execution fails with 422 (ValidationError)
        exec_resp2 = await client.post(f"/v1/communication/actions/{token_hash}/execute")
        assert exec_resp2.status_code in (400, 422)


@pytest.mark.asyncio
async def test_inbound_chat_webhooks_api():
    app = build_test_app()
    async with make_client(app) as client:
        # Telegram /status command
        tg_resp = await client.post(
            "/v1/communication/webhooks/telegram",
            json={
                "channel_type": "TELEGRAM",
                "raw_text": "/status",
                "sender_id": "user-chat-1",
            },
        )
        assert tg_resp.status_code == 200
        tg_data = tg_resp.json()
        assert tg_data["command"] == "STATUS"
        assert "Atlas System Status" in tg_data["response_text"]

        # Discord /analyze command
        dc_resp = await client.post(
            "/v1/communication/webhooks/discord",
            json={
                "channel_type": "DISCORD",
                "raw_text": "/analyze ETH/USDT",
                "sender_id": "user-chat-1",
            },
        )
        assert dc_resp.status_code == 200
        dc_data = dc_resp.json()
        assert dc_data["command"] == "ANALYZE"
        assert "ETH/USDT" in dc_data["response_text"]
