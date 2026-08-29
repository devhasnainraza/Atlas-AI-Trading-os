# Implementation Plan: Trading Integration (Venues, Market Data & Order Execution)

**Branch**: `003-trading-integration` | **Date**: 2026-08-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-trading-integration/spec.md`

## Summary

Deliver Atlas's execution layer as two new API modules (`marketdata`, `trading`) plus a shared
venue-adapter package on the Spec 00 foundation, consuming Spec 01's credential vault for every
venue credential. Users connect MetaTrader 5, OANDA, Binance, Bybit, or Interactive Brokers (or
the built-in paper venue), stream freshness-guaranteed market data, see venue-authoritative
accounts and positions, and place/amend/cancel orders through a two-phase
intent → confirm flow behind a synchronous, override-free pre-trade risk gate. Ambiguous
outcomes become an explicit `unresolved` state resolved only by reconciliation. Every venue —
including paper — implements one adapter protocol validated by a shared conformance suite.

## Technical Context

**Language/Version**: Python 3.12 (`marketdata` + `trading` modules in `apps/api`, adapters in `shared/atlas_venues`, sync/reconcile jobs in `services/worker` + `services/scheduler`), TypeScript 5.x (trading UI in `apps/web`)
**Primary Dependencies**: FastAPI + Pydantic v2, SQLAlchemy 2 async + Alembic, httpx (venue REST), websockets (venue private streams), Redis 7 (latest quotes, rate-limit buckets, pub/sub fan-out), aiokafka (`atlas.trading.*` / `atlas.marketdata.*`), `MetaTrader5` (Windows bridge sidecar only), `ib_insync`-family async client (IB Gateway sidecar), ccxt (crypto instrument metadata normalization only — never order submission), sse-starlette (quote fan-out)
**Storage**: PostgreSQL 16 (connections, accounts, instruments, bars, intents, orders, fills, positions, risk policies/verdicts, mandates, paper state, reconciliation runs), Redis (latest quote per venue+instrument with staleness TTL, per-connection token buckets, submission locks, pub/sub), Kafka (trading + market data event log), S3 (reconciliation reports, bar backfill archives)
**Testing**: pytest + testcontainers (real PG/Redis), one shared **venue conformance suite** run against every adapter incl. paper (SC-013), venue simulators/recorded-cassette adapters for Binance/Bybit/OANDA/MT5-bridge/IBKR, Schemathesis vs contracts/trading-api.openapi.yaml, property-based tests for Decimal precision and quantity stepping, chaos/fault-injection suite (timeout mid-submit, stream gap, revoked credential, rate-limit ban), Playwright E2E on paper venue, k6 load (quote fan-out + order storm)
**Target Platform**: Same as Spec 00 — containers on Compose (local) and Kubernetes (cloud), plus two capability-limited sidecars (MT5 bridge on Windows, IB Gateway)
**Project Type**: web — extends `apps/api` (2 modules) + `apps/web` (features) + `services/worker` + `services/scheduler` + `shared/` (1 package) + 2 sidecars
**Performance Goals**: quote observation → browser p95 < 1s (SC-002); confirmation → venue transmit p95 < 500 ms excluding venue RTT (SC-004); kill switch effective < 1s (SC-008); account/position sync freshness target 5s streaming / 30s polling; 1,000 concurrent traders with active subscriptions inside every venue rate limit (SC-012)
**Constraints**: at-most-once venue transmission per intent (SC-005); no risk-gate bypass path anywhere (FR-038/SC-006); no credential in any client response, log, export, or support surface (SC-011); venue is authoritative — local state is a correctable projection (FR-020); refuse rather than approximate on stale/missing inputs (SC-007); Decimal-only arithmetic in trading domain code
**Scale/Scope**: 2 new backend modules + 1 shared adapter package + 6 adapters (5 real + paper), ~55 API operations, ~24 entities, ~28 domain events, 7 user stories

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Compliance in this plan | Status |
|---|-----------|------------------------|--------|
| I | Human First | Two-phase intent → explicit confirm on every order (§6); confirmations expire and invalidate on drift; automation only via scoped, expiring, revocable mandates (§8); user + operator kill switch (§8). | ✅ |
| II | Security First | Venue credentials only via Spec 01 vault per operation, never cached, never client-visible (§13); sidecars hold no persistent secrets; revocation quarantines the connection. | ✅ |
| III | Transparency | Confirmation review states exact terms, risk verdict, estimated cost/margin; stale data and degraded connections are labelled, not hidden (§4, §12). | ✅ |
| IV | Multi-Agent Collab | Order origin is first-class (`manual｜agent｜strategy｜mandate`); future agents submit intents through the same gate — never adapters directly (§6, §8). | ✅ |
| V | Explainability | Every order carries its full chain: origin → risk verdict (rules + values) → confirmation → submission → venue responses → fills → final state (§10). | ✅ |
| VI | Risk Before Profit | One synchronous risk gate on the only path to `adapter.submit`; no `force`/`skip_risk` parameter exists anywhere, asserted by contract test (§7). | ✅ |
| VII | Continuous Learning | Fills, verdicts, and reconciliation outcomes are the substrate for future journal/analytics specs; no training on excluded or erased data. | ✅ |
| VIII | Privacy by Design | Trading records are user-scoped; erasure handler registered against Spec 01's erasure event with execution-record retention documented (§14). | ✅ |
| IX | Reliability | `unresolved` is a first-class order state, never auto-retried; degraded modes explicit; refusal is the default when data is stale or a venue is unreachable (§12). | ✅ |
| X | Modular Architecture | `marketdata` and `trading` are standard Spec 00 modules with `public.py` surfaces; adapters live behind one protocol in `shared/atlas_venues`; no module reaches another's tables. | ✅ |
| XI | Observability | Order-flow dashboards, per-venue latency/rejection/rate-limit metrics, reconciliation drift metrics, append-only audit for every transition (§10, §11). | ✅ |
| XII | Scalability | Stateless API; per-connection stream ownership with lease-based sharding; Redis-backed fan-out and platform-wide rate buckets; bars partitioned monthly (§15). | ✅ |

**Gate result (pre-Phase-0)**: PASS. **Post-Phase-1 re-check**: PASS — three complexity entries
(two venue sidecars, two-phase order flow, venue-authoritative projection) justified in
Complexity Tracking.

## 1. High-Level Architecture

```text
Browser ──HTTPS──► apps/api (authN/authZ from Spec 01)
   │  SSE quotes                    │
   │                    ┌───────────┴────────────┐
   │                    ▼                        ▼
   │           marketdata module          trading module
   │           subs · quotes · bars       connections · accounts · instruments
   │           freshness contract         intents · orders · fills · positions
   │                    │                 RiskGate (no bypass) · mandates · kill switch
   │                    │                 reconciliation
   │                    └───────────┬────────────┘
   │                                ▼
   │                    shared/atlas_venues — VenueAdapter protocol
   │            ┌──────────┬─────────┬────────┬────────┬─────────┐
   │            ▼          ▼         ▼        ▼        ▼         ▼
   │          paper      oanda    binance   bybit    mt5*     ibkr*
   │                                                  │         │
   │                                          MT5 bridge   IB Gateway
   │                                          (Windows)     (sidecar)
   ▼
Redis: latest quote (TTL = staleness) · rate buckets · submit locks · pub/sub
Postgres: everything durable (bars partitioned monthly)
Kafka: atlas.trading.* / atlas.marketdata.* → worker (sync, reconcile, alerts, analytics)
Spec 01 vault: use_credential(id, purpose) per operation — nothing cached
```

- **Connection flow**: user picks venue + stored credential → adapter capability matrix ∩
  venue-granted permissions → verify reachability → persist connection with environment stamp →
  health probes on schedule.
- **Data flow**: subscription → stream owner (worker lease) → normalized tick → Redis latest
  (TTL = freshness limit) + pub/sub → SSE fan-out; bar aggregation and gap-marked backfill to
  Postgres.
- **Order flow**: compose → `POST /orders/intents` (validates instrument constraints, prices the
  order, runs the risk gate, returns verdict + expiry) → user confirms → submission ledger row
  written in the same transaction → single adapter submit → venue ack/reject → stream/poll
  updates → fills → position projection.
- **Ambiguity flow**: submit timeout or unclassifiable error → order `unresolved` → immediate
  targeted reconciliation → venue state applied → order resolved and recorded. The request path
  never retries.
- **Trust boundaries**: (1) internet ↔ ingress; (2) API ↔ modules (Spec 01 authN/authZ +
  step-up for mandate/live-connection changes); (3) modules ↔ vault (typed handles, not keys);
  (4) platform ↔ sidecars (private network only, per-operation credentials, no disk);
  (5) Atlas ↔ venue (TLS, per-connection identity, rate-limit compliance).

## 2. Venue Abstraction

`shared/atlas_venues` defines the only way Atlas talks to a market:

| Protocol area | Operations |
|---|---|
| Discovery | `capabilities()`, `verify_permissions()`, `instruments()`, `instrument(symbol)` |
| Data | `quote(symbols)`, `bars(symbol, timeframe, range)`, `stream_quotes(symbols)` |
| Account | `account_snapshot()`, `positions()`, `open_orders()`, `stream_account()` |
| Execution | `submit(order)`, `amend(order, changes)`, `cancel(order)`, `close_position(...)` |
| Semantics | `server_time_offset()`, `rate_limit_model()`, `classify_error(exc)` |

- **Capability matrix** per adapter: order types, TIF values, amend support, protective-level
  support (attached vs separate orders), streaming support, environments, symbol conventions.
- **Error classification** is part of the protocol and returns one of `retryable_transient`,
  `rate_limited`, `terminal_rejection`, `permission_denied`, `ambiguous` — `ambiguous` is what
  drives `unresolved` (never a retry).
- **Conformance suite** (`tests/conformance/venues/`) runs the same behavioral contract against
  every adapter: symbol normalization, precision/stepping, order lifecycle, cancel-after-partial,
  idempotent client id handling, error classification, and stream reconnect. Paper runs in CI on
  every PR; real venues run against demo accounts in a nightly job.
- **Adding a venue** = adapter + capability matrix + conformance pass + config. No change to
  order, risk, or reconciliation code (SC-013).

## 3. Venue Connections & Account Sync

- **Connection** = (user, venue, credential reference, environment, granted capabilities, health,
  last contact). Creating or promoting a connection to `live` requires Spec 01 step-up MFA.
- **Health**: `healthy | degraded | expired | failed | quarantined`. Probes run per-venue on the
  scheduler; failures downgrade with a sanitized reason; credential revocation →
  `quarantined` (order routing stops, reconciliation triggered).
- **Account sync**: streaming where the venue supports a private account stream (Binance, Bybit,
  OANDA transactions, IBKR); polling fallback at a per-venue cadence for MT5. Snapshot
  reconciliation on every reconnect. `synced_at` is stored and surfaced; account view flips to
  `stale` past the freshness target and `unknown` when never reached (FR-019).
- **Position discovery**: positions and orders that Atlas did not create are imported and
  counted against risk limits (FR-017) — never ignored.

## 4. Market Data & Freshness Contract

- **Latest quote**: Redis key per (venue, instrument) holding bid/ask/last + `observed_at`, with
  TTL = the asset class freshness limit. **Key absence is staleness** — no timestamp comparison
  scattered through call sites.
- **Freshness limits** (config, per asset class): crypto 3 s, forex 3 s, other 10 s; every
  response carries `freshness: fresh|stale` and `observed_at`.
- **Bars**: per (venue, instrument, timeframe), monthly-partitioned, with explicit gap rows;
  backfill is a low-priority job that yields to order traffic in the rate limiter.
- **Attribution**: every quote and bar names its venue; no cross-venue blending (FR-015).
- **Sessions**: instrument session schedules stored per venue in venue-local terms, resolved to
  UTC; `session_state` (`open|closed|pre|halted|suspended`) is part of the instrument view and a
  risk-gate input.
- **Stream ownership**: one worker holds a Redis lease per (connection, symbol group); lease
  expiry re-shards subscriptions — no duplicate venue subscriptions, no gap on failover.

## 5. Instrument Normalization

Canonical Atlas symbol (e.g. `EURUSD`, `BTCUSDT`) mapped to each venue's native symbol, with
per-venue specification: asset class, quantity min/max/step, contract size, price precision and
tick size, quote/base/settlement currency, margin/leverage terms, session schedule, tradability.
Specs refresh on a schedule and on connection creation; a changed spec re-validates any working
order's constraints and fails safe rather than transmitting an invalid order (FR-033). Unknown
or unmapped symbols are rejected at compose time with a clear message.

## 6. Order Lifecycle & Two-Phase Confirmation

| Phase | What happens |
|---|---|
| Compose | Client builds terms; no server state required |
| Intent | `POST /orders/intents` → normalize symbol, validate instrument constraints and precision, require fresh quote, price the order (estimated cost, fees, margin impact), run the **risk gate**, persist `order_intent` with verdict + `expires_at` (default 30 s) |
| Review | Client shows exact terms, verdict, cost/margin, destination account and environment |
| Confirm | `POST /orders/intents/{id}/confirm` with the intent's `verdict_hash`; server re-checks freshness, account state, kill switch, mandate/limits, and hash match — any drift ⇒ `409` invalidated, re-review required (FR-025) |
| Submit | Submission-ledger row + order row committed **before** the adapter call; exactly one `adapter.submit` per intent, guarded by a Redis lock on `client_order_id` |
| Track | Venue ack → `working`; stream/poll updates → `partially_filled`/`filled`/`canceled`/`rejected`/`expired`; each fill stored individually; position projection updated |
| Ambiguity | timeout or `ambiguous` classification ⇒ `unresolved` + targeted reconciliation; never auto-resubmitted (FR-030) |

- **Order types**: market, limit, stop, stop-limit; TIF `GTC｜IOC｜FOK｜DAY｜GTD`; optional
  attached stop-loss/take-profit expressed uniformly and translated per venue capability.
- **Amend/cancel**: `amending`/`canceling` in-flight sub-states; Atlas reports the venue's actual
  answer and never claims a refused cancellation succeeded (FR-028).
- **Origin & accountability**: every order records origin (`manual｜agent｜strategy｜mandate`)
  and the accountable human user id (FR-034).
- **Close position / protect position** reuse the same intent → confirm → gate path.

## 7. Risk Gate (Unbypassable)

- **Single entry point**: `RiskGate.evaluate(intent, context) → RiskVerdict` is the only code
  path that can reach `adapter.submit`. Enforced structurally: the submit call lives in one
  service function that takes a `RiskVerdict` value object it cannot construct itself.
- **No override exists**: no `force`, `skip_risk`, `dry_run_bypass`, or admin equivalent in the
  OpenAPI surface, service signatures, or adapter protocol. A contract test greps the surface and
  fails the build if one appears — the analogue of Spec 01's "no endpoint returns plaintext".
- **Rules** (all evaluated, all reported): max order size; max position size per instrument; max
  total exposure (per venue and aggregate); max daily loss (rolling user-defined window with
  stated reset time); max open positions; leverage ceiling; instrument allowlist; session guard;
  duplicate-order heuristic; kill-switch state; mandate scope when origin is `mandate`.
- **Fail-closed inputs**: stale quote, unknown balance, unreachable venue, unresolved
  reconciliation, or unknown instrument spec ⇒ `blocked` with `recommend_wait` (FR-039).
- **Risk-reducing exception**: when a daily-loss or exposure block is active, orders that
  strictly reduce exposure (close/partial-close in the offsetting direction) remain permitted;
  this is a rule in the gate, not a bypass of it (FR-043, US5 §5).
- **Verdict record**: rules evaluated, limit values, actual values, decision
  (`allowed｜blocked｜allowed_with_warnings`), breached rule list, correlation id, `verdict_hash`
  — persisted and retrievable for any order forever (FR-040).

## 8. Automation Mandates & Kill Switch

- **Mandate**: user-granted, requires step-up MFA, must declare instrument scope, max order
  size, max total commitment (notional), optional max orders per period, and a mandatory expiry
  (max 30 days). Orders under a mandate skip *per-order confirmation only* — never the risk gate.
  Consumption is metered against the mandate's caps; exhaustion or expiry ⇒ mandate inactive.
- **Revocation**: immediate, single click, no confirmation friction; in-flight orders are
  reported honestly, not rewritten.
- **Kill switch**: user-level (all their accounts) and operator-level (global or per venue),
  stored with actor + reason, checked in the gate and at confirm; effective < 1 s via Redis flag
  with Postgres as the durable record. Cancels and position closes remain available (FR-043).

## 9. Paper Trading

Paper is a `VenueAdapter` (research §16), not a branch in the order code. Simulated account with
configurable starting balance and currency; fills computed from live quotes with disclosed
spread widening, slippage, and latency model (`fill_model_version` stored on each simulated
fill); simulated margin and leverage mirror a chosen venue profile. Environment `paper` is
stamped on the connection, every account/order/position/fill row, every API response, and every
confirmation payload; the UI marks it persistently. Reset restores starting state and records the
reset. Paper figures are excluded from any surface labelled real performance (FR-050).

## 10. Audit, Explainability & Traceability

Extends Spec 00's append-only `audit_log_entry` with a trading taxonomy:
`trading.connection.created/verified/degraded/quarantined/disconnected`,
`trading.intent.created/expired/invalidated`, `trading.risk.evaluated/blocked`,
`trading.order.confirmed/submitted/acked/amended/canceled/filled/rejected/unresolved/resolved`,
`trading.position.opened/modified/closed`, `trading.mandate.granted/revoked/exhausted`,
`trading.killswitch.engaged/released`, `trading.reconciliation.completed/discrepancy/escalated`,
`trading.paper.reset`. Every entry carries actor, correlation id, connection, order, and
sanitized venue reference — never credentials or raw venue auth payloads. The **order chain**
view joins intent → verdict → confirmation → submission ledger → venue responses → fills →
transitions into one retrievable narrative (FR-055, SC-009), retained per execution-record
retention policy.

## 11. Reconciliation

Triggers: scheduled per connection (default 60 s for live, 5 min for demo/paper), post-
`unresolved` (immediate, targeted), stream reconnect after a gap, credential revocation, and on
demand. Compares open orders, positions, and balances; classifies each difference
(`missing_locally｜missing_at_venue｜quantity_mismatch｜price_mismatch｜state_mismatch｜
unknown_order`); applies venue state; records divergence + correction. Unresolvable
discrepancies escalate to the user and support and **hold order routing for that account** until
settled (FR-053). Drift rate is a first-class metric and alert (SC-003).

## 12. Degraded Modes & Failure Handling

| Failure | Behavior |
|---|---|
| Venue REST unreachable | Connection `degraded`; account view `stale` with age; new orders refused with recommend-wait |
| Stream gap / disconnect | Reconnect with backoff; on resume, snapshot reconcile; quotes go `stale` via TTL expiry meanwhile |
| Submit timeout / ambiguous error | Order `unresolved` + targeted reconciliation; **no retry**, no optimistic state |
| Rate limit hit | Shed backfill/instrument refresh first; orders and cancels keep priority; sustained ⇒ `degraded` with reason |
| Credential revoked/rotated | Connection `quarantined`; routing stops; in-flight orders reconciled |
| Redis unavailable | Quotes treated as stale (fail-safe), rate buckets fall back to conservative per-process limits, order submission refused (submit lock unavailable) |
| Kafka unavailable | Outbox retains events; order path continues (transactional outbox), consumers catch up |
| Sidecar (MT5/IBKR) down | Only that venue's connections degrade; other venues unaffected |
| Reconciliation unresolved | Order routing held for that account; user + support notified |

## 13. Security

Venue credentials retrieved per operation from the Spec 01 vault with purpose `trade` or
`read_only`, zeroized after use, never cached, never logged, never serialized to a client
(FR-008, SC-011) — enforced by a redaction guard plus a contract test asserting no response
schema in the trading surface can carry secret material. Live-connection creation and mandate
grants require step-up MFA. Sidecars sit on a private network with no public ingress, hold no
persistent secrets, and receive credentials per operation. Venue webhooks (where offered) are
signature-verified with replay windows. Outbound egress is allowlisted per venue host. Order
endpoints carry strict rate-limit classes independent of venue limits. Support surfaces show
health, permissions, and sanitized errors only (FR-056). Raw venue payloads are stored only after
redaction and only for the reconciliation window.

## 14. Privacy & Retention

Trading records are user-scoped and included in Spec 01's privacy export as metadata (no
credentials). An erasure handler is registered against
`atlas.privacy.user_erasure.requested` and emits its ack: subscriptions, intents, quotes cache,
paper accounts, and mandates are deleted; orders, fills, and risk verdicts are **pseudonymized,
not deleted**, under the execution-record retention assumption (7 years, configurable), with
that carve-out documented in the export bundle. Bars and instrument specs are non-personal and
retained independently. Retention: reconciliation reports 1 year, raw redacted venue payloads
30 days, quote cache seconds, audit ≥ 1 year (Spec 01 policy).

## 15. Scalability & Capacity

API and worker processes are stateless; stream ownership is lease-based per (connection, symbol
group) so subscriptions shard horizontally and fail over without duplicate venue subscriptions.
Rate-limit buckets and submit locks live in Redis so limits hold platform-wide. Quote fan-out is
Redis pub/sub → SSE, with per-connection subscription caps. Bars partitioned monthly; orders,
fills, and verdicts indexed by (user, created_at) with a partition plan documented for growth.
Capacity assumption for launch: 1,000 concurrent traders, ≤ 50 subscribed instruments each,
≤ 20 connections per user, order rate ≤ 5/s per user with burst shaping (SC-012).

## 16. Observability

Metrics: per-venue request latency/error/rate-limit-utilization; quote lag (venue observation →
client) with SC-002 SLO; order latency (confirm → transmit → ack) with SC-004 SLO; rejection
rate by reason; `unresolved` order count and age (**page-worthy**); reconciliation drift rate and
unresolved discrepancies (page-worthy); risk-block counts by rule; kill-switch engagements;
mandate usage; stream reconnect rate; sidecar health. Dashboards: Order Flow, Venue Health,
Market Data Freshness, Risk & Blocks, Reconciliation. Every alert gets a runbook in
`docs/runbooks/trading/`.

## 17. Error Handling

Spec 00 envelope extended: `ATLAS-TRD-001` connection unavailable, `-002` capability not
permitted, `-003` instrument not tradable / session closed, `-004` invalid quantity or precision,
`-005` stale market data, `-006` intent expired or invalidated, `-007` duplicate submission
blocked, `-008` order not amendable/cancelable in current state, `-009` venue rejected (carries
sanitized venue reason), `-010` outcome unresolved, `-011` reconciliation hold active,
`-012` rate limited by venue; `ATLAS-RISK-001` limit breached (carries breached rules),
`-002` kill switch engaged, `-003` mandate scope exceeded or expired, `-004` risk inputs
unavailable — recommend wait. Rules: venue reasons surfaced sanitized (FR-032/057); never expose
raw venue payloads, credentials, internal hosts, or stack traces; every error carries a
correlation id that joins the order chain.

## 18. Testing Strategy

Unit: risk-rule algebra, Decimal precision/stepping, order state machine, freshness logic,
fill-model math, mandate metering — all with fakes and an injected clock. **Conformance**: one
suite, every adapter (paper in CI, real venues nightly against demo). Integration
(testcontainers): intent → confirm → submit → fills → position with the paper adapter and with
cassette-backed venue simulators; reconciliation correcting each discrepancy class. Contract:
Schemathesis vs the trading OpenAPI; event-schema compatibility; **no-bypass test** (surface
contains no override parameter); **no-secret test** (no response schema can carry secrets).
Chaos/fault injection: timeout mid-submit ⇒ `unresolved` (never duplicate, never filled),
duplicate confirm ⇒ one venue order, stream gap ⇒ reconcile, revoked credential ⇒ quarantine,
rate-limit ban ⇒ degrade. E2E (Playwright) on paper: US4, US5, US6 journeys. Load (k6): 1,000
subscribers quote fan-out (SC-002), order storm (SC-004), kill-switch latency (SC-008).
Security: `/security-review` on the full diff, gitleaks/Bandit/pip-audit, egress-allowlist test.

## 19. Deployment Strategy

Rides Spec 00 infrastructure; adds two sidecar deployments (MT5 bridge on a Windows node pool,
IB Gateway) reachable only on the private network, each with its own health probes and
independent failure domain. New secrets via ESO: none for venue credentials (user vault), only
sidecar internal RPC keys and market-data config. Feature flags per venue (`venue.mt5.enabled`,
…) plus a global `trading.live_orders.enabled` flag that defaults **off** — paper and demo work
without it, so the module ships before live routing is switched on. Rollout: paper → demo
connections → live behind flag per venue. Migrations expand→migrate→contract. Rollback: disable
the venue flag (connections degrade cleanly, no data loss); order history is append-only and
never rewritten. Pre-live gates: conformance green on that venue, chaos suite green, drift
metric < threshold for 7 days on demo, security review complete, runbooks published.

## 20. Risks

| Risk | Type | Impact | Mitigation |
|------|------|--------|-----------|
| Duplicate order transmission | Financial | Direct capital loss, trust destroyed | Submission ledger + Redis lock + client order id, `unresolved` instead of retry, chaos test asserting exactly-one, SC-005 in CI |
| Risk-gate bypass introduced later | Financial/Compliance | Unbounded loss | Structural gate (verdict value object), no override param, contract test greps surface, PR review rule on trading module |
| Venue API/behavior change | Operational | Silent breakage or bad orders | Nightly conformance against demo accounts, capability matrix versioned, per-venue flags for fast disable |
| MT5 bridge fragility (Windows sidecar) | Operational | One venue down | Isolated failure domain, connection degrades with reason, polling fallback, MT5 marked capability-limited |
| Stale data acted upon | Financial | Wrong-price execution | TTL-as-staleness in Redis, fresh-quote requirement in gate, confirmation invalidation on drift, SC-007 tests |
| Local/venue divergence | Financial/Trust | Wrong position view, wrong risk math | Venue-authoritative projection, multi-trigger reconciliation, routing hold on unresolved, drift alerting |
| Venue rate-limit ban | Operational | User locked out of their own account | Platform-wide token buckets, priority shedding (orders > backfill), degrade with reason |
| Credential exposure via venue payload logs | Security | Catastrophic | Redaction guard + no-secret contract test, per-operation vault retrieval, payloads stored redacted only |
| Precision/rounding error | Financial | Wrong size sent | Decimal-only lint rule, property-based stepping tests, pre-submit constraint validation |
| Clock skew | Operational | Auth window and daily-window bugs | Per-venue server-time offset, injected UTC clock, skew metric + alert |
| Scope creep into agents/strategies | Delivery | Delay, unreviewed automation | Origin + mandate model defined now, agent/strategy behavior explicitly out of scope |
| Regulatory exposure from live routing | Compliance | Legal risk | `trading.live_orders.enabled` off by default, no custody, no advice, per-jurisdiction review before enabling |

## Complexity Tracking

| Choice | Why Needed | Simpler Alternative Rejected Because |
|--------|------------|--------------------------------------|
| Two venue sidecars (MT5 bridge, IB Gateway) | MT5's official API is Windows-terminal-bound and IBKR requires Gateway for order routing; both are where the target users already trade | Dropping MT5/IBKR removes the majority of retail forex and all multi-asset reach; Wine/community reimplementations are unsupported and unacceptable for money movement; MQL-side logic would move trading rules outside the risk gate |
| Two-phase intent → confirm instead of single-call order placement | Constitution I requires explicit confirmation of exactly what will be sent, including the risk verdict and cost; a single call cannot show a reviewable, invalidatable artifact | One-shot placement with a client-side confirm dialog puts the guarantee in the client, where it can be skipped by any non-browser caller |
| Venue-authoritative projection + reconciliation machinery | Positions and orders change outside Atlas, and ambiguous submits are unavoidable; without reconciliation the risk gate computes on fiction | Treating local state as truth guarantees silent divergence, and "reconcile on user request" surfaces the problem only after a loss |

---

**Phase 0 output**: [research.md](./research.md) · **Phase 1 outputs**:
[data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)
