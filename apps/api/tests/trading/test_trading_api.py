"""Trading module API contract (US1/US5/US6 read surfaces).

These endpoints exist to make the platform's refusals legible before an order is placed: which
venues are permitted, which rules will judge it, and whether a real order can leave at all. The
tests below therefore assert the *safe* answers — paper on, real venues off, live transmission
off unless two independent switches agree.
"""

from __future__ import annotations

import pytest

from atlas_api.modules.trading.venues import VENUE_FLAG_DEFAULTS, VENUE_FLAG_KEYS
from atlas_api.testing import build_test_app, make_client
from atlas_venues.adapters.paper import PAPER_VENUE_CODE


async def test_venue_catalog_lists_paper_with_its_capabilities():
    app = build_test_app()
    async with make_client(app) as client:
        resp = await client.get("/v1/trading/venues")
    assert resp.status_code == 200
    venues = {v["venue_code"]: v for v in resp.json()["venues"]}
    assert PAPER_VENUE_CODE in venues
    paper = venues[PAPER_VENUE_CODE]
    assert paper["enabled"] is True, "paper cannot lose money and ships enabled"
    assert paper["requires_sidecar"] is False
    assert "paper" in paper["environments"]
    assert paper["supports_client_order_id"] is True


async def test_paper_venue_never_offers_a_live_environment():
    """A book that settles against itself must not claim it can reach the real market."""
    app = build_test_app()
    async with make_client(app) as client:
        resp = await client.get("/v1/trading/venues")
    paper = next(v for v in resp.json()["venues"] if v["venue_code"] == PAPER_VENUE_CODE)
    assert "live" not in paper["environments"]


def test_every_real_money_venue_ships_disabled():
    """Defence in depth, checked at the source of truth rather than through the API.

    Registering an adapter must never be the same act as permitting it. Anything that can lose
    real money starts off and is switched on deliberately.
    """
    real_money_venues = set(VENUE_FLAG_KEYS) - {PAPER_VENUE_CODE}
    assert real_money_venues, "the flag map should cover the real venues"
    enabled_by_default = {v for v in real_money_venues if VENUE_FLAG_DEFAULTS.get(v, False)}
    assert not enabled_by_default, f"real-money venues default to enabled: {enabled_by_default}"


async def test_risk_rules_are_published_with_a_description_each():
    app = build_test_app()
    async with make_client(app) as client:
        resp = await client.get("/v1/trading/risk/rules")
    assert resp.status_code == 200
    rules = resp.json()["rules"]
    assert len(rules) >= 20, "the published set should be the whole gate, not a summary"
    assert all(r["description"].strip() for r in rules), "a rule with no explanation is not usable"
    codes = [r["code"] for r in rules]
    assert len(codes) == len(set(codes))
    assert "kill_switch_engaged" in codes


async def test_live_trading_is_off_by_default_and_says_why():
    app = build_test_app()
    async with make_client(app) as client:
        resp = await client.get("/v1/trading/live-status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["live_orders_enabled"] is False
    assert body["require_step_up_for_live"] is True
    assert "disabled" in body["reason"].lower()


async def test_config_alone_cannot_turn_live_trading_on(monkeypatch: pytest.MonkeyPatch):
    """Config and flag are independent switches; one is not a majority.

    A redeploy takes minutes, a flag flip takes seconds. Requiring both means an operator can
    stop transmission immediately without waiting on a release.
    """
    monkeypatch.setenv("TRADING_LIVE_ORDERS_ENABLED", "true")
    app = build_test_app()
    async with make_client(app) as client:
        resp = await client.get("/v1/trading/live-status")
    body = resp.json()
    assert body["live_orders_enabled"] is False
    assert "feature flag" in body["reason"].lower()


async def test_paper_reset_returns_the_new_balance_and_increments_the_counter():
    app = build_test_app()
    async with make_client(app) as client:
        first = await client.post("/v1/trading/paper/acct-1/reset", json={})
        second = await client.post(
            "/v1/trading/paper/acct-1/reset", json={"starting_balance": "25000.50"}
        )
    assert first.status_code == 200
    assert first.json()["reset_count"] == 1
    assert second.status_code == 200
    body = second.json()
    assert body["venue_account_ref"] == "acct-1"
    assert body["starting_balance"] == "25000.50", "the exact decimal must survive the round trip"
    assert body["reset_count"] == 2, "reset history is not erasable by resetting again"


async def test_paper_reset_rejects_unknown_fields_and_non_positive_balances():
    app = build_test_app()
    async with make_client(app) as client:
        typo = await client.post("/v1/trading/paper/acct-1/reset", json={"startingBalance": "1000"})
        zero = await client.post("/v1/trading/paper/acct-1/reset", json={"starting_balance": "0"})
    # A misspelled field silently read as "not given" is how a wrong number reaches a book.
    assert typo.status_code == 422
    assert typo.json()["error"]["code"] == "ATLAS-VAL-001"
    assert zero.status_code == 422


async def test_two_apps_do_not_share_one_paper_book():
    """Module state belongs to an app, not to the process.

    Built as a global, the second app's book store would answer the first app's requests and the
    reset counter would continue from wherever the other app left off.
    """
    app_a = build_test_app()
    app_b = build_test_app()
    async with make_client(app_a) as client_a:
        await client_a.post("/v1/trading/paper/shared-ref/reset", json={})
        await client_a.post("/v1/trading/paper/shared-ref/reset", json={})
        a_third = await client_a.post("/v1/trading/paper/shared-ref/reset", json={})
    async with make_client(app_b) as client_b:
        b_first = await client_b.post("/v1/trading/paper/shared-ref/reset", json={})
    assert a_third.json()["reset_count"] == 3
    assert b_first.json()["reset_count"] == 1


async def test_trading_module_is_registered_with_the_platform():
    app = build_test_app()
    async with make_client(app) as client:
        resp = await client.get("/v1/platform/modules")
    names = {m["name"] for m in resp.json()}
    assert {"trading", "marketdata"} <= names
