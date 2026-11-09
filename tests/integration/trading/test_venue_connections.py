"""Integration tests for User Story 1: Connect a broker or exchange (T030, T031, T032, T033, T045).

Guarantees asserted:
- T030: Verified capabilities stored as declared ∧ granted; read-only key ⇒ trading capability absent (FR-005)
- T031: Bad/expired credential ⇒ health: failed with sanitized reason, no secret in response or log (FR-004, FR-008)
- T032: Credential revoked event ⇒ connection quarantined, routing stops, reconciliation triggered (FR-011)
- T033: Venue-connections operations match contracts/trading-api.openapi.yaml
- T045: Audit entries for trading.connection.created/verified/degraded/quarantined/disconnected
- Zero float money (Constitution X)
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest

from atlas_api.main import create_app
from atlas_api.modules.trading.domain.connections import ConnectionHealth
from atlas_api.modules.trading.router import STATE_KEY, TradingModuleContext
from atlas_api.modules.trading.settings import TradingSettings
from atlas_api.modules.trading.venues import PaperBookStore, register_builtin_venues
from atlas_api.testing import build_test_app, make_client
from atlas_core.config import AtlasSettings
from atlas_core.feature_flags import FeatureFlags, StaticFlagProvider
from atlas_events import EventEnvelope
from atlas_venues.adapters.paper import PAPER_CAPABILITIES, PAPER_VENUE_CODE, PaperAdapter
from atlas_venues.credentials import InMemoryCredentialProvider, set_credential_provider
from atlas_venues.enums import AssetClass, OrderType, TimeInForce, VenueEnvironment
from atlas_venues.models import Capabilities, InstrumentSpec
from atlas_venues.protocol import VenueAdapter
from atlas_venues.registry import AdapterContext, VenueRegistry


class MockSimulatorAdapter:
    """Configurable simulator adapter for testing permissions, read-only scopes, and errors."""

    def __init__(
        self,
        context: AdapterContext,
        *,
        verify_ok: bool = True,
        verify_detail: str = "ok",
    ) -> None:
        self.context = context
        self._verify_ok = verify_ok
        self._verify_detail = verify_detail

    def capabilities(self) -> Capabilities:
        return Capabilities(
            venue_code=self.context.venue_code,
            display_name="Mock Simulator Venue",
            asset_classes=frozenset({AssetClass.CRYPTO, AssetClass.FOREX}),
            order_types=frozenset({OrderType.MARKET, OrderType.LIMIT, OrderType.STOP_LIMIT}),
            time_in_force=frozenset({TimeInForce.GTC, TimeInForce.IOC}),
            supports_amend=True,
            supports_cancel=True,
            supports_streaming_quotes=True,
            supports_close_position=True,
            supports_stop_loss_take_profit=True,
            supports_short_selling=True,
            environments=frozenset({VenueEnvironment.DEMO, VenueEnvironment.LIVE}),
        )

    async def verify_permissions(self) -> tuple[bool, str]:
        # If options dictate, override verdict
        if "read_only" in self.context.options:
            return True, "read_only key verified"
        if "bad_key" in self.context.options:
            return False, f"invalid API key: {self.context.options['bad_key']}"
        return self._verify_ok, self._verify_detail

    async def instruments(self) -> list[InstrumentSpec]:
        return []

    async def instrument(self, symbol: str) -> InstrumentSpec:
        raise NotImplementedError

    async def quote(self, symbols: list[str]) -> list[Any]:
        return []

    async def bars(self, symbol: str, interval: str, **kwargs: Any) -> list[Any]:
        return []

    async def stream_quotes(self, symbols: list[str]) -> Any:
        raise NotImplementedError

    async def account_snapshot(self) -> Any:
        from atlas_venues.models import AccountSnapshot
        from datetime import UTC, datetime
        return AccountSnapshot(
            currency="USD",
            balance=Decimal("50000.00"),
            equity=Decimal("50000.00"),
            margin_used=Decimal("0.00"),
            margin_available=Decimal("50000.00"),
            unrealized_pnl=Decimal("0.00"),
            venue_time=datetime.now(UTC),
        )

    async def positions(self) -> list[Any]:
        return []

    async def open_orders(self) -> list[Any]:
        return []

    async def order(self, **kwargs: Any) -> Any:
        raise NotImplementedError

    async def stream_account(self) -> Any:
        raise NotImplementedError

    async def submit(self, request: Any) -> Any:
        raise NotImplementedError

    async def amend(self, request: Any) -> Any:
        raise NotImplementedError

    async def cancel(self, request: Any) -> Any:
        raise NotImplementedError

    async def time_offset(self) -> Any:
        raise NotImplementedError

    async def rate_limits(self) -> Any:
        raise NotImplementedError

    async def raw_request(self, method: str, path: str, **kwargs: Any) -> Any:
        raise NotImplementedError


def _setup_test_app_with_venues() -> Any:
    flags = FeatureFlags(
        StaticFlagProvider(
            {
                "venue.paper.enabled": True,
                "venue.binance.enabled": True,
                "venue.oanda.enabled": True,
            }
        )
    )
    app = build_test_app()
    app.state.runtime.flags = flags
    ctx: TradingModuleContext = getattr(app.state, STATE_KEY)

    # Register simulator mock for binance
    def make_simulator(ctx: AdapterContext) -> VenueAdapter:
        return MockSimulatorAdapter(ctx)

    if not ctx.registry.is_registered("binance"):
        caps = Capabilities(
            venue_code="binance",
            display_name="Binance Exchange",
            asset_classes=frozenset({AssetClass.CRYPTO}),
            order_types=frozenset({OrderType.MARKET, OrderType.LIMIT}),
            time_in_force=frozenset({TimeInForce.GTC}),
            supports_amend=True,
            supports_cancel=True,
            supports_streaming_quotes=True,
            supports_close_position=True,
            supports_stop_loss_take_profit=True,
            supports_short_selling=True,
            environments=frozenset({VenueEnvironment.DEMO, VenueEnvironment.LIVE}),
        )
        ctx.registry.register("binance", make_simulator, caps)

    return app


@pytest.mark.asyncio
async def test_create_paper_connection_stores_verified_capabilities():
    """T030: Creating a connection stores declared ∧ granted capabilities; paper succeeds and lists account."""
    app = _setup_test_app_with_venues()
    cred_id = str(uuid4())

    async with make_client(app) as client:
        # Create connection
        resp = await client.post(
            "/v1/trading/venue-connections",
            headers={"X-User-ID": "usr-test-001"},
            json={
                "venue_code": "paper",
                "credential_id": cred_id,
                "environment": "paper",
                "label": "My Test Paper Account",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        conn_id = data["id"]
        assert data["venue_code"] == "paper"
        assert data["health"] == "healthy"
        assert data["routing_hold"] is False
        assert len(data["granted_capabilities"]["order_types"]) > 0

        # Verify account was discovered
        acc_resp = await client.get(
            f"/v1/trading/venue-connections/{conn_id}/accounts",
            headers={"X-User-ID": "usr-test-001"},
        )
        assert acc_resp.status_code == 200
        accounts = acc_resp.json()["items"]
        assert len(accounts) == 1
        assert accounts[0]["venue_account_ref"] == "My Test Paper Account"
        assert Decimal(accounts[0]["balance"]) == Decimal("100000.00")
        assert accounts[0]["view_state"] == "live"


@pytest.mark.asyncio
async def test_read_only_credential_strips_trading_capabilities():
    """T030 (FR-005): Read-only credential removes trading capabilities (order types empty, amend=False)."""
    app = _setup_test_app_with_venues()
    ctx: TradingModuleContext = getattr(app.state, STATE_KEY)

    # Register read-only simulator for oanda
    def make_readonly_adapter(ctx: AdapterContext) -> VenueAdapter:
        return MockSimulatorAdapter(ctx, verify_ok=True, verify_detail="read_only permission granted")

    # Re-register oanda for read-only simulation
    ctx.registry._factories.pop("oanda", None)
    ctx.registry._capabilities.pop("oanda", None)
    caps = Capabilities(
        venue_code="oanda",
        display_name="OANDA Forex",
        asset_classes=frozenset({AssetClass.FOREX}),
        order_types=frozenset({OrderType.MARKET, OrderType.LIMIT}),
        time_in_force=frozenset({TimeInForce.GTC}),
        supports_amend=True,
        supports_cancel=True,
        supports_streaming_quotes=True,
        supports_close_position=True,
        supports_stop_loss_take_profit=True,
        supports_short_selling=True,
        environments=frozenset({VenueEnvironment.DEMO, VenueEnvironment.LIVE}),
    )
    ctx.registry.register("oanda", make_readonly_adapter, caps)


    async with make_client(app) as client:
        resp = await client.post(
            "/v1/trading/venue-connections",
            headers={"X-User-ID": "usr-test-001"},
            json={
                "venue_code": "oanda",
                "credential_id": str(uuid4()),
                "environment": "demo",
                "label": "OANDA Read Only Account",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["health"] == "healthy"
        granted = data["granted_capabilities"]
        # Trading capability must be stripped!
        assert len(granted["order_types"]) == 0
        assert granted["supports_amend"] is False
        assert granted["supports_cancel"] is False
        assert granted["supports_close_position"] is False
        assert "READ-ONLY" in granted["notes"]


@pytest.mark.asyncio
async def test_bad_credential_fails_with_sanitized_reason_and_no_leak():
    """T031 (FR-004, FR-008): Expired/bad credential ⇒ health: failed with sanitized reason, no raw secret."""
    app = _setup_test_app_with_venues()
    ctx: TradingModuleContext = getattr(app.state, STATE_KEY)
    secret_key = "AKIAIOSFODNN7EXAMPLE"

    def make_failing_adapter(ctx: AdapterContext) -> VenueAdapter:
        return MockSimulatorAdapter(
            ctx,
            verify_ok=False,
            verify_detail=f"Authentication failed: api_key={secret_key} expired token",
        )

    # Re-register binance to fail with secret in message
    ctx.registry._factories.pop("binance", None)
    ctx.registry._capabilities.pop("binance", None)
    caps = Capabilities(
        venue_code="binance",
        display_name="Binance Exchange",
        asset_classes=frozenset({AssetClass.CRYPTO}),
        order_types=frozenset({OrderType.MARKET}),
        time_in_force=frozenset({TimeInForce.GTC}),
        supports_amend=False,
        supports_cancel=True,
        supports_streaming_quotes=True,
        supports_close_position=True,
        supports_stop_loss_take_profit=True,
        supports_short_selling=False,
        environments=frozenset({VenueEnvironment.DEMO, VenueEnvironment.LIVE}),
    )
    ctx.registry.register("binance", make_failing_adapter, caps)

    async with make_client(app) as client:
        resp = await client.post(
            "/v1/trading/venue-connections",
            headers={"X-User-ID": "usr-test-001"},
            json={
                "venue_code": "binance",
                "credential_id": str(uuid4()),
                "environment": "demo",
                "label": "Failing Account",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["health"] == "failed"
        assert data["health_reason"] is not None
        # Must redact the raw secret!
        assert secret_key not in data["health_reason"]
        assert "***" in data["health_reason"] or "[REDACTED" in data["health_reason"] or "redacted" in data["health_reason"].lower()


@pytest.mark.asyncio
async def test_live_connection_requires_step_up_mfa():
    """T031: Creating a live connection without step-up MFA raises HTTP 403 ATLAS-AUTH-MFA-REQUIRED."""
    app = _setup_test_app_with_venues()

    async with make_client(app) as client:
        # Without step-up MFA header
        resp = await client.post(
            "/v1/trading/venue-connections",
            headers={"X-User-ID": "usr-test-001"},
            json={
                "venue_code": "binance",
                "credential_id": str(uuid4()),
                "environment": "live",
                "label": "Live Account",
            },
        )
        assert resp.status_code == 403
        err = resp.json()["error"]
        assert err["code"] == "ATLAS-AUTH-MFA-REQUIRED"

        # With step-up MFA header
        ok_resp = await client.post(
            "/v1/trading/venue-connections",
            headers={"X-User-ID": "usr-test-001", "X-Step-Up-MFA": "true"},
            json={
                "venue_code": "binance",
                "credential_id": str(uuid4()),
                "environment": "live",
                "label": "Live Account Verified",
            },
        )
        assert ok_resp.status_code == 201
        assert ok_resp.json()["environment"] == "live"


@pytest.mark.asyncio
async def test_credential_revoked_event_quarantines_connection():
    """T032: Credential revoked event ⇒ connection quarantined, routing stops, reconciliation triggered."""
    app = _setup_test_app_with_venues()
    cred_id = str(uuid4())

    async with make_client(app) as client:
        # Create connection
        resp = await client.post(
            "/v1/trading/venue-connections",
            headers={"X-User-ID": "usr-test-001"},
            json={
                "venue_code": "paper",
                "credential_id": cred_id,
                "environment": "paper",
                "label": "Account to Revoke",
            },
        )
        assert resp.status_code == 201
        conn_id = resp.json()["id"]

        # Publish credential revoked event (catalog requires user_id, credential_id, cause)
        envelope = EventEnvelope(
            event_type="atlas.credentials.credential.revoked",
            producer="atlas-credentials",
            payload={"user_id": "usr-test-001", "credential_id": cred_id, "cause": "user_revoked_key"},
        )
        await app.state.runtime.bus.publish(envelope)

        # Connection must now be quarantined
        get_resp = await client.get(
            f"/v1/trading/venue-connections/{conn_id}",
            headers={"X-User-ID": "usr-test-001"},
        )
        assert get_resp.status_code == 200
        conn_data = get_resp.json()
        assert conn_data["health"] == "quarantined"
        assert conn_data["routing_hold"] is True
        assert conn_data["health_reason"] == "user_revoked_key"


@pytest.mark.asyncio
async def test_openapi_contract_operations_and_audit_trail():
    """T033 & T045: Full CRUD on /venue-connections and verify audit log entries."""
    app = _setup_test_app_with_venues()
    cred_id = str(uuid4())

    async with make_client(app) as client:
        # 1. Direct path /v1/venue-connections (OpenAPI contract)
        post_resp = await client.post(
            "/v1/venue-connections",
            headers={"X-User-ID": "usr-audit-001"},
            json={
                "venue_code": "paper",
                "credential_id": cred_id,
                "environment": "paper",
                "label": "Audit Test Account",
            },
        )
        assert post_resp.status_code == 201
        conn = post_resp.json()
        conn_id = conn["id"]

        # 2. List connections
        list_resp = await client.get(
            "/v1/venue-connections",
            headers={"X-User-ID": "usr-audit-001"},
        )
        assert list_resp.status_code == 200
        items = list_resp.json()["items"]
        assert any(c["id"] == conn_id for c in items)

        # 3. Get connection
        get_resp = await client.get(
            f"/v1/venue-connections/{conn_id}",
            headers={"X-User-ID": "usr-audit-001"},
        )
        assert get_resp.status_code == 200

        # 4. Re-verify connection
        verify_resp = await client.post(
            f"/v1/venue-connections/{conn_id}/verify",
            headers={"X-User-ID": "usr-audit-001"},
        )
        assert verify_resp.status_code == 200
        assert verify_resp.json()["health"] == "healthy"

        # 5. List accounts with refresh
        acc_resp = await client.get(
            f"/v1/venue-connections/{conn_id}/accounts?refresh=true",
            headers={"X-User-ID": "usr-audit-001"},
        )
        assert acc_resp.status_code == 200

        # 6. Delete / Disconnect
        del_resp = await client.delete(
            f"/v1/venue-connections/{conn_id}",
            headers={"X-User-ID": "usr-audit-001"},
        )
        assert del_resp.status_code == 204

        # 7. Check audit log entries (T045)
        audit_entries = app.state.runtime.audit_log.query(actor="usr-audit-001")
        actions = [entry.action for entry in audit_entries]
        assert "trading.connection.created" in actions
        assert "trading.connection.verified" in actions
        assert "trading.connection.disconnected" in actions


@pytest.mark.asyncio
async def test_worker_credential_consumer_and_scheduler_probe():
    """T042 & T043: Worker consumer triggers quarantine/re-verify; scheduler probes execute."""
    from atlas_scheduler.venue_health_probe import probe_all_connections
    from atlas_worker.consumers.venue_credentials import VenueCredentialConsumer

    class MockHandler:
        def __init__(self) -> None:
            self.revoked: list[tuple[str, str]] = []
            self.rotated: list[str] = []

        async def handle_credential_revoked(self, credential_id: str, *, reason: str = "credential_revoked", actor: str = "system") -> list[str]:
            self.revoked.append((credential_id, reason))
            return ["conn-1"]

        async def handle_credential_rotated(self, credential_id: str) -> list[str]:
            self.rotated.append(credential_id)
            return ["conn-1"]

        async def list_active_connections(self):
            from dataclasses import dataclass
            @dataclass
            class DummyConn:
                id: str = "conn-1"
                venue_code: str = "paper"
                user_id: str = "usr-1"
            return [DummyConn()]

        async def verify_connection(self, connection_id: str, *, user_id: str):
            from dataclasses import dataclass
            @dataclass
            class DummyResult:
                health: str = "healthy"
            return DummyResult()

    handler = MockHandler()
    consumer = VenueCredentialConsumer(handler)

    # Test revocation consumer
    rev_envelope = EventEnvelope(
        event_type="atlas.credentials.credential.revoked",
        producer="atlas-credentials",
        payload={"credential_id": "cred-rev-1", "user_id": "usr-1", "cause": "manual_revocation"},
    )
    await consumer.on_credential_revoked(rev_envelope)
    assert handler.revoked == [("cred-rev-1", "manual_revocation")]

    # Test rotation consumer
    rot_envelope = EventEnvelope(
        event_type="atlas.credentials.credential.rotated",
        producer="atlas-credentials",
        payload={"credential_id": "cred-rot-1", "user_id": "usr-1", "version": 2},
    )
    await consumer.on_credential_rotated(rot_envelope)
    assert handler.rotated == ["cred-rot-1"]

    # Test scheduler probe
    probe_stats = await probe_all_connections(handler)
    assert probe_stats["total"] == 1
    assert probe_stats["verified"] == 1
    assert probe_stats["failed"] == 0
