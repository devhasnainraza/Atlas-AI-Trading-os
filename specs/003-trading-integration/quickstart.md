# Quickstart: Trading Integration (Local Development)

**Feature**: 003-trading-integration | Builds on the Spec 00 local stack
(`specs/001-platform-foundation/quickstart.md`) and Spec 01 auth/vault
(`specs/002-auth-security/quickstart.md`) — complete both first.

Everything below works **without any real venue account**: the paper venue and the recorded
venue simulators cover US1–US7 end to end.

## Extra prerequisites

- **Nothing** for paper mode. `venue.paper.enabled=true` by default in local flagd.
- Optional demo credentials (stored through the Spec 01 vault UI, never in `.env`): OANDA practice
  token, Binance/Bybit testnet API keys, IBKR paper account.
- Optional sidecars, only if you want the real thing locally:
  - MT5 bridge — requires a Windows host with the MT5 terminal; `compose.mt5.yaml` profile.
  - IB Gateway — `compose.ibkr.yaml` profile, paper login.
- `TRADING_LIVE_ORDERS_ENABLED` stays **false** locally; live routing is a deliberate,
  reviewed switch (plan §19).

## 1. Configure

```bash
cp infra/docker/.env.example .env       # includes TRADING_* and MARKETDATA_* sections
./scripts/db migrate                    # applies marketdata + trading migration branches
uv run python -m atlas_api.modules.trading.seed   # seeds venue catalog + paper venue + default risk policy
```

Startup fails fast if a required trading variable is missing — the error names the field.
Freshness limits (`MARKETDATA_FRESHNESS_*`) and reconciliation cadences
(`TRADING_RECONCILE_INTERVAL_*`) are config, not code.

## 2. Smoke the flows (scripts wrap curl; all against http://localhost:8000/v1)

| Flow | Command | Expect |
|---|---|---|
| Paper connection | `./scripts/trading-smoke connect-paper` | 201 connection, `environment: paper`, `health: healthy`, capabilities listed |
| Market data | `./scripts/trading-smoke quotes` | subscribe → SSE ticks; kill the simulator → quotes flip to `freshness: stale` within the limit |
| Account sync | `./scripts/trading-smoke accounts` | balance/equity with `view_state: live`; pause the feed → `stale` with age |
| Order lifecycle | `./scripts/trading-smoke order` | intent (verdict + cost) → confirm → `working` → fill → position appears |
| Duplicate confirm | `./scripts/trading-smoke duplicate` | second confirm returns `200` with the **same** order id; exactly one venue submit in `venue_message` |
| Risk block | `./scripts/trading-smoke risk-block` | oversized order → intent `rejected_by_risk` with breached rules; no venue call recorded |
| Stale-data refusal | `./scripts/trading-smoke stale` | freeze the feed → intent creation returns `ATLAS-TRD-005`, recommend wait |
| Unresolved order | `./scripts/trading-smoke unresolved` | simulator drops the response → order `unresolved`, **no retry**, reconciliation resolves it |
| Kill switch | `./scripts/trading-smoke kill-switch` | engage → new orders refused < 1s; cancel and close still succeed |
| Reconciliation | `./scripts/trading-smoke reconcile` | inject an external position at the simulator → run → imported, counted against limits |
| Paper reset | `./scripts/trading-smoke paper-reset` | balance restored, `reset_count` incremented, reset audited |

## 3. Web UI

`apps/web` routes: `/trading` (watchlist + chart + order ticket), `/trading/orders`,
`/trading/positions`, `/settings/venues` (connections + health), `/settings/risk` (policy,
kill switch, mandates), `/trading/reconciliation`. Paper mode shows a persistent environment
badge on every trading surface; the order ticket cannot submit without passing through the
confirmation panel that displays the exact terms and the risk verdict.

## 4. Tests

```bash
uv run pytest apps/api/src/atlas_api/modules/trading apps/api/src/atlas_api/modules/marketdata -m "not slow"
uv run pytest tests/conformance/venues -k paper        # venue conformance suite (all adapters in CI)
uv run pytest tests/contract/trading                   # Schemathesis + event compat + no-bypass + no-secret
uv run pytest tests/chaos/trading                      # timeout mid-submit, stream gap, revoked credential, rate-limit ban
pnpm exec playwright test tests/e2e/trading            # US4–US6 journeys on paper
```

The two guard tests are the ones to run before any trading PR:
`tests/contract/trading/test_no_risk_bypass.py` (no `force`/`skip_risk`-style parameter exists in
the API surface, service signatures, or adapter protocol) and
`tests/contract/trading/test_no_credential_exposure.py` (no response schema or log path can carry
secret material).

## Troubleshooting

- **All quotes `stale` immediately**: Redis not reachable — staleness is the fail-safe default, so
  check the container before suspecting the feed.
- **Intent creation returns `ATLAS-TRD-005`**: no fresh quote for that instrument. Subscribe
  first; the gate refuses rather than pricing off an old tick.
- **Confirm returns `409` repeatedly**: the price moved past the drift threshold between review and
  confirm. Re-create the intent — this is the invalidation rule working.
- **Order stuck `unresolved`**: check the worker is running; reconciliation is what resolves it,
  and nothing in the request path will retry.
- **`routing_hold: true` on a connection**: an unresolved discrepancy exists. Open the
  reconciliation run, settle it, then routing resumes.
- **MT5 profile fails on Linux/macOS**: expected — the bridge requires a Windows host. Use the
  paper venue or the MT5 simulator adapter instead.
- **Clock-dependent test failures**: the suite uses the injected clock; never `datetime.now()` in
  trading domain code (Spec 00 standard).
