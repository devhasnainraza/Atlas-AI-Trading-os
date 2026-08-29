# Tasks: Trading Integration (Venues, Market Data & Order Execution)

**Input**: Design documents from `/specs/003-trading-integration/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/](./contracts/)
**Depends on**: Spec 00 (platform foundation) — complete, and Spec 01 (auth, RBAC, credential
vault, privacy events) — **specified but not implemented**. See
[Implementation deviations](#implementation-deviations) for what that defers and how the seams
are held open.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: `US1`–`US7`, or blank for setup/foundational/polish
- File paths are explicit; `api` = `apps/api/src/atlas_api`, `venues` = `shared/atlas_venues/src/atlas_venues`

---

## Phase 1: Setup

- [x] T001 Create `shared/atlas_venues` package (pyproject, `py.typed`, `public.py`) and wire it into the uv workspace + `apps/api`/`services/worker` dependencies — public surface is a curated `__init__.py` `__all__`, matching the other four `shared/` packages; `public.py` is the *API module* convention, not the shared-package one
- [x] T002 [P] Scaffold `api/modules/marketdata/` per `docs/module-conventions.md` (`public.py`, `router.py`, `schemas.py`, `service.py`, `events.py`, `domain/`, `repository/`)
- [x] T003 [P] Scaffold `api/modules/trading/` with the same layout plus `domain/risk/`, `domain/orders/`, `domain/reconciliation/` — `domain/risk.py` landed with the gate; `orders`/`reconciliation` arrive with US4/US7 rather than as empty packages
- [x] T004 [P] Add `TradingSettings` and `MarketDataSettings` (fail-fast Pydantic Settings): freshness limits per asset class, intent TTL, reconcile cadences, subscription caps, `TRADING_LIVE_ORDERS_ENABLED` (default false)
- [x] T005 [P] Register flags in flagd config: `venue.paper.enabled` (default on), `venue.{mt5,oanda,binance,bybit,ibkr}.enabled` (default off), `trading.live_orders.enabled` (default off) — `infra/flags/flags.json` + README, loaded via `ATLAS_FEATURE_FLAGS_FILE` → `FileFlagProvider` (no flagd deployment exists yet); guarded by `tests/contract/trading/test_shipped_flags_are_safe.py`
- [x] T006 [P] Add `TRADING_*` / `MARKETDATA_*` sections to `infra/docker/.env.example` (no secrets — venue credentials live in the Spec 01 vault)
- [x] T007 [P] Add the float ban: Ruff/flake8 rule + CI check forbidding `float` literals and `float()` in `modules/trading`, `modules/marketdata`, and `atlas_venues` domain code — Ruff has no float-literal rule, so this is an AST guard test (`tests/contract/trading/test_no_float_money.py`) scoped by identifier meaning so durations stay legal
- [x] T008 [P] Create `tests/conformance/venues/`, `tests/contract/trading/`, `tests/chaos/trading/`, `tests/e2e/trading/` skeletons and register them in the test matrix

---

## Phase 2: Foundational (⚠️ CRITICAL — blocks every user story)

**These establish the adapter protocol, the schema, and the two guard tests. No story work starts until this phase is green.**

### Venue adapter protocol

- [x] T009 Define the `VenueAdapter` protocol in `venues/protocol.py`: discovery, data, account, execution, and semantics operations exactly as in plan §2
- [x] T010 Define value objects in `venues/models.py`: `Capabilities`, `InstrumentSpec`, `QuoteTick`, `Bar`, `AccountSnapshot`, `VenuePosition`, `VenueOrder`, `SubmitRequest`, `SubmitResult` — all `Decimal`, all frozen
- [x] T011 Define `venues/errors.py` with the classification enum (`retryable_transient｜rate_limited｜terminal_rejection｜permission_denied｜ambiguous`) and `classify_error` contract
- [x] T012 Implement `venues/registry.py` (adapter lookup by venue code, flag-gated) and `venues/public.py` exposing only the protocol, registry, and models — surface exported from `atlas_venues/__init__.py` (see T001)

### Schema

> **Deferred — no persistence layer exists yet.** Spec 00 shipped entirely in-memory: Protocol
> ports with `InMemory*` reference implementations, no SQLAlchemy models and no Alembic tree,
> even though both are declared in `apps/api/pyproject.toml`. Writing the first migration here
> would mean inventing the whole persistence foundation inside a trading spec. Instead T013–T018
> land as repository Protocol ports plus `InMemory*` implementations that match the table shapes
> in [data-model.md](./data-model.md) exactly — including the `order_submission` uniqueness
> constraint, which the in-memory store enforces itself. The migrations then become a
> port-swap, not a redesign.

- [ ] T013 Alembic migration: `venue`, `venue_connection`, `venue_account` (+ health/routing_hold indexes) per data-model.md
- [ ] T014 [P] Alembic migration: `instrument`, `market_data_subscription`, `candle` (monthly partitions + partition maintenance job)
- [ ] T015 Alembic migration: `order_intent`, `order`, `order_submission` (**unique on `intent_id`**), `order_event`, `fill`, `position`
- [ ] T016 [P] Alembic migration: `risk_policy`, `risk_verdict`, `automation_mandate`, `kill_switch`
- [ ] T017 [P] Alembic migration: `paper_account`, `reconciliation_run`, `reconciliation_discrepancy`, `venue_message`
- [ ] T018 [P] Seed script `modules/trading/seed.py`: venue catalog with capability matrices + rate-limit models, paper venue, default risk policy template

### Cross-cutting primitives

- [x] T019 `Decimal` money/quantity helpers in `venues/precision.py`: round-to-tick, step validation, min/max validation, with property-based tests
- [x] T020 Injected-clock + venue server-time offset service (`venues/timing.py`); skew metric emitted
- [x] T021 Redis token-bucket rate limiter honoring per-adapter weight models, shared across API and worker (`venues/ratelimit.py`), with priority classes (orders/cancels > snapshots > backfill)
- [x] T022 Credential access wrapper `venues/credentials.py` calling `credentials.public.use_credential(credential_id, purpose)` per operation, zeroizing after use, never caching — seam defined against the Spec 01 contract; the resolver is injected, so the vault drops in without touching adapters
- [x] T023 `venue_message` redaction guard: strip auth headers/secrets before persistence or logging, with unit tests over each adapter's payload shapes
- [x] T024 Register `atlas.trading.*` and `atlas.marketdata.*` event types in `shared/atlas_events/catalog.py` per contracts/trading-events.md
- [ ] T025 Wire RBAC permissions (`trading:connection:*`, `trading:order:*`, `trading:risk:*`, `marketdata:feed:read`) and step-up-MFA requirement for live connections + mandate grants — **blocked on Spec 01**; no `auth` module exists to hang scopes on
- [x] T026 Error taxonomy: `ATLAS-TRD-001..012` and `ATLAS-RISK-001..004` handlers mapping to the Spec 00 envelope

### Guard tests (must exist and pass before any story)

- [x] T027 `tests/contract/trading/test_no_risk_bypass.py` — asserts no `force`/`skip_risk`/`bypass`/`override`-style parameter exists in the OpenAPI surface, trading service signatures, or the adapter protocol (SC-006) — split by layer: `shared/tests/venues/test_no_risk_bypass.py` covers the protocol and service signatures, `tests/contract/trading/test_api_surface_guards.py` covers the published OpenAPI surface
- [x] T028 `tests/contract/trading/test_no_credential_exposure.py` — asserts no response schema, event payload, or log formatter in trading/marketdata can carry secret material (SC-011) — same split: `shared/tests/venues/test_no_credential_exposure.py` plus the OpenAPI half in `test_api_surface_guards.py`

**Checkpoint**: adapter protocol frozen, storage ports defined (migrations deferred — see above),
guard tests green — story work can begin.

---

## Phase 3: User Story 1 — Connect a broker or exchange (Priority: P1)

**Goal**: A user links a venue account with stored credentials and sees verified capabilities and health.
**Independent Test**: create a paper connection and a simulator-backed venue connection; both verify, list accounts, and report health; a read-only credential is rejected for trading capability with a clear message.

### Tests for User Story 1 ⚠️ write first, must fail

- [ ] T029 [P] [US1] Conformance test group `discovery`: `capabilities()`, `verify_permissions()`, `instruments()` behavior contract in `tests/conformance/venues/test_discovery.py`
- [ ] T030 [P] [US1] Integration test: create connection → verified capabilities stored as declared ∧ granted; read-only key ⇒ trading capability absent (FR-005)
- [ ] T031 [P] [US1] Integration test: bad/expired credential ⇒ `health: failed` with sanitized reason, no secret in response or log (FR-004, FR-008)
- [ ] T032 [P] [US1] Integration test: credential revoked event ⇒ connection `quarantined`, routing stops, reconciliation triggered
- [ ] T033 [P] [US1] Contract test: `/venue-connections` operations vs `contracts/trading-api.openapi.yaml`

### Implementation for User Story 1

- [ ] T034 [P] [US1] Paper adapter skeleton in `venues/adapters/paper/` implementing discovery + account operations (execution lands in US6)
- [ ] T035 [P] [US1] OANDA adapter discovery + account (`venues/adapters/oanda/`), v20 REST via httpx with timeout/retry classification
- [ ] T036 [P] [US1] Binance adapter discovery + account (`venues/adapters/binance/`) with weight-aware limits and server-time offset
- [ ] T037 [P] [US1] Bybit adapter discovery + account (`venues/adapters/bybit/`)
- [ ] T038 [US1] MT5 bridge sidecar (`services/mt5-bridge/`): narrow internal RPC, no persistent secrets, health endpoint; adapter `venues/adapters/mt5/` calling it
- [ ] T039 [US1] IBKR adapter (`venues/adapters/ibkr/`) + IB Gateway sidecar compose profile; marked capability-limited
- [ ] T040 [US1] `trading/repository/connections.py` + `domain/connections.py`: create, verify, capability intersection, health transitions
- [ ] T041 [US1] `trading/service.py` connection operations + `POST /venue-connections`, `GET`, `GET /{id}`, `DELETE`, `POST /{id}/verify` in `router.py`
- [ ] T042 [US1] Health probe scheduler job (`services/scheduler`) per venue cadence; emits `venue.degraded` / `venue.verified`
- [ ] T043 [US1] Consumer for `atlas.credentials.credential.revoked` / `.rotated` → quarantine / re-verify, idempotent via the event ledger
- [ ] T044 [P] [US1] Web: `/settings/venues` — connection list with health badges, add-connection flow (credential picker from Spec 01, environment choice, step-up MFA for live), sanitized error display
- [ ] T045 [P] [US1] Audit entries for `trading.connection.created/verified/degraded/quarantined/disconnected`

**Checkpoint**: users can connect venues, see verified capabilities and honest health; nothing trades yet.

---

## Phase 4: User Story 2 — See live market data (Priority: P1)

**Goal**: Subscribed instruments stream fresh, venue-attributed prices, and staleness is always visible.
**Independent Test**: subscribe on a simulator connection, observe SSE ticks in the browser inside the latency budget, cut the feed, and watch the UI flip to stale with an age — never a frozen price shown as current.

### Tests for User Story 2 ⚠️ write first, must fail

- [ ] T046 [P] [US2] Conformance test group `data`: `quote()`, `bars()`, `stream_quotes()` including reconnect and gap reporting
- [ ] T047 [P] [US2] Unit test: TTL-as-staleness — expired key ⇒ `freshness: stale`, `age_seconds` reported, Redis down ⇒ stale (fail-safe)
- [ ] T048 [P] [US2] Integration test: bar backfill marks gaps (`is_gap`) and never interpolates (FR-014)
- [ ] T049 [P] [US2] Integration test: quotes from two venues for one symbol stay separately attributed (FR-015)
- [ ] T050 [P] [US2] Load test (k6): 1,000 subscribers, observation → client p95 < 1s (SC-002)

### Implementation for User Story 2

- [ ] T051 [US2] Instrument normalization service: canonical ↔ venue symbol mapping, spec refresh job, `spec_version` bump + `instrument.spec_changed` event (`marketdata/domain/instruments.py`)
- [ ] T052 [US2] Redis quote store with freshness-limit TTL and `observed_at` (`marketdata/repository/quotes.py`)
- [ ] T053 [US2] Stream owner worker with Redis lease per (connection, symbol group), reconnect backoff, gap detection → `feed.degraded` / `feed.recovered`
- [ ] T054 [US2] Bar aggregation + gap-marked backfill job (low priority in the rate limiter), monthly partition writes
- [ ] T055 [US2] `marketdata/service.py` + `router.py`: `/market-data/quotes`, `/candles`, `/subscriptions` (CRUD, per-user cap), `/stream` (SSE via Redis pub/sub)
- [ ] T056 [US2] `marketdata/public.py` exposing `get_quote`, `get_quotes`, `is_fresh` for the trading module (no cross-module table access)
- [ ] T057 [P] [US2] Web: watchlist + chart on `/trading`, SSE hook with reconnect, explicit stale badge and age, session-state indicator
- [ ] T058 [P] [US2] Metrics + dashboard: quote lag histogram, stale-quote counter, stream reconnect rate, feed-degraded gauge

**Checkpoint**: US1 + US2 deliver a trustworthy read-only market view.

---

## Phase 5: User Story 3 — Account and position sync (Priority: P2)

**Goal**: Balances, positions, and open orders match the venue, with visible freshness and no silent divergence.
**Independent Test**: open a position directly at the simulator; Atlas discovers it, flags `opened_externally`, and counts it toward exposure; pause the feed and the view degrades to `stale` with an age.

### Tests for User Story 3 ⚠️ write first, must fail

- [ ] T059 [P] [US3] Conformance test group `account`: `account_snapshot()`, `positions()`, `open_orders()`, `stream_account()`
- [ ] T060 [P] [US3] Integration test: externally opened position imported with `opened_externally: true` and included in exposure math (FR-017)
- [ ] T061 [P] [US3] Integration test: sync failure ⇒ `view_state: stale` with age; never-synced ⇒ `unknown` (FR-019)
- [ ] T062 [P] [US3] Integration test: out-of-order account updates never overwrite newer state

### Implementation for User Story 3

- [ ] T063 [US3] Account snapshot service + `view_state` derivation (`trading/domain/accounts.py`)
- [ ] T064 [US3] Position projection from venue state (`trading/domain/positions.py`), netting vs hedging keying
- [ ] T065 [US3] Streaming account consumer per adapter (Binance/Bybit user data, OANDA transactions, IBKR) with polling fallback for MT5
- [ ] T066 [US3] Scheduled sync job + snapshot reconcile on reconnect; emits `account.synced`, `position.opened/updated/closed`
- [ ] T067 [US3] Endpoints: `GET /venue-connections/{id}/accounts` (with `refresh`), `GET /positions`
- [ ] T068 [P] [US3] Web: `/trading/positions` with freshness badge, external-origin marker, per-connection grouping
- [ ] T069 [P] [US3] Metrics: sync age per connection, stale-view gauge, external-position discovery counter

**Checkpoint**: account state is venue-truthful and honestly labelled — the precondition for risk math.

---

## Phase 6: User Story 4 — Order lifecycle with explicit confirmation (Priority: P2)

**Goal**: Nothing reaches a venue without an explicit human confirmation of exact terms, and transmission is at-most-once.
**Independent Test**: on the paper/simulator venue, place → amend → cancel; confirm twice and get exactly one venue order; drop the venue response mid-submit and get `unresolved` with no retry and no phantom fill.

### Tests for User Story 4 ⚠️ write first, must fail

- [ ] T070 [P] [US4] Conformance test group `execution`: submit/amend/cancel, cancel-after-partial, client-order-id handling, error classification
- [ ] T071 [P] [US4] Integration test: intent → confirm → order; the venue is called exactly once (assert on `venue_message`)
- [ ] T072 [P] [US4] Integration test: duplicate confirm ⇒ `200` with the same order id, `order_submission` unique constraint hit, zero extra venue calls (FR-026, SC-005)
- [ ] T073 [P] [US4] Chaos test: submit timeout ⇒ order `unresolved`, no retry, no optimistic fill (FR-030)
- [ ] T074 [P] [US4] Integration test: price drift beyond threshold between intent and confirm ⇒ `409` invalidated, re-review required (FR-025)
- [ ] T075 [P] [US4] Integration test: partial fill then cancel ⇒ filled quantity preserved, only remainder canceled (FR-027, edge case)
- [ ] T076 [P] [US4] Integration test: venue refuses amend/cancel ⇒ Atlas reports the refusal, state unchanged (FR-028)
- [ ] T077 [P] [US4] Integration test: instrument `spec_version` bump ⇒ working order re-validated, invalid order fails safe (FR-033)
- [ ] T078 [P] [US4] Contract test: order endpoints vs OpenAPI + Schemathesis fuzz on write bodies (`extra="forbid"`)
- [ ] T079 [P] [US4] Load test (k6): confirm → transmit p95 < 500 ms excluding venue RTT (SC-004)

### Implementation for User Story 4

- [ ] T080 [US4] Order state machine in `trading/domain/orders/state.py` with `unresolved` as a first-class state and append-only transitions
- [ ] T081 [US4] Intent service: normalization, precision/step validation, fresh-quote requirement, pricing (cost/fees/margin), verdict attachment, `verdict_hash`, TTL (`trading/domain/orders/intent.py`)
- [ ] T082 [US4] Confirmation service: hash match, freshness/account/kill-switch/mandate re-check, invalidation rules
- [ ] T083 [US4] Submission path: `order_submission` ledger row + order row in one transaction **before** the adapter call, Redis lock on `client_order_id`, exactly one `adapter.submit` (`trading/domain/orders/submit.py`)
- [ ] T084 [US4] Ambiguity handling: timeout/`ambiguous` ⇒ `unresolved` + emit `order.unresolved` + enqueue targeted reconciliation; never retry
- [ ] T085 [US4] Fill ingestion with `venue_fill_ref` dedupe, per-fill rows, derived average price, position update
- [ ] T086 [US4] Amend/cancel services with `amending`/`canceling` sub-states and venue-confirmed-only transitions
- [ ] T087 [US4] Execution implementations for paper, OANDA, Binance, Bybit adapters (submit/amend/cancel/close)
- [ ] T088 [US4] Execution implementations for MT5 (via bridge) and IBKR (via Gateway), capability-limited
- [ ] T089 [US4] Endpoints: `POST /orders/intents`, `GET /orders/intents/{id}`, `POST /orders/intents/{id}/confirm`, `GET /orders`, `GET /orders/{id}`, `POST /{id}/amend`, `POST /{id}/cancel`
- [ ] T090 [US4] Position action endpoints: `POST /positions/{id}/close-intent`, `POST /positions/{id}/protect-intent` (same gate path)
- [ ] T091 [P] [US4] Web: order ticket with mandatory confirmation panel (exact terms, verdict, cost, destination, environment), countdown to intent expiry, invalidation re-review
- [ ] T092 [P] [US4] Web: `/trading/orders` list with state badges, `unresolved` treatment, amend/cancel actions honoring venue answers
- [ ] T093 [P] [US4] Metrics + alerts: order latency histogram, rejection rate by reason, `unresolved` count and age (page-worthy)

**Checkpoint**: full manual trading works end to end with no duplicate-order path.

---

## Phase 7: User Story 5 — Pre-trade risk gate (Priority: P3)

**Goal**: Every order passes one unbypassable risk evaluation with a stored, explainable verdict.
**Independent Test**: set limits, attempt breaching orders of each rule type, and confirm each is blocked with named rules and values; verify no code path or parameter can reach submit without a verdict; verify stale inputs block rather than pass.

### Tests for User Story 5 ⚠️ write first, must fail

- [ ] T094 [P] [US5] Unit tests per rule: order size, position size, total exposure, daily loss window, open-position count, leverage, allowlist, session guard, duplicate heuristic
- [ ] T095 [P] [US5] Unit test: missing/stale inputs ⇒ `blocked` + `recommend_wait`, never `allowed` (FR-039, SC-007)
- [ ] T096 [P] [US5] Unit test: risk-reducing order permitted while a daily-loss block is active (FR-043 exception is a rule, not a bypass)
- [ ] T097 [P] [US5] Integration test: `submit` is unreachable without a `RiskVerdict` — attempted direct call fails type/architecture test
- [ ] T098 [P] [US5] Integration test: policy change applies to future orders only; working orders untouched (FR-044)
- [ ] T099 [P] [US5] Integration test: kill switch engaged ⇒ new orders refused < 1s, cancel/close still allowed (SC-008)

### Implementation for User Story 5

- [ ] T100 [US5] `RiskVerdict` value object constructible only by the gate; `submit` requires it (`trading/domain/risk/verdict.py`)
- [ ] T101 [US5] `RiskGate.evaluate(intent, context)` with all rules evaluated and reported, fail-closed inputs (`trading/domain/risk/gate.py`)
- [ ] T102 [US5] Exposure and daily-loss calculators using venue-authoritative positions and the configured window/timezone
- [ ] T103 [US5] Risk policy CRUD with versioning + `risk.policy_changed` event; `GET/PUT /risk/policy`, `POST /risk/preview`
- [ ] T104 [US5] Kill switch: Redis flag + durable rows, checks in gate and confirm, `GET/POST /risk/kill-switch`, operator scope via admin surface
- [ ] T105 [US5] Verdict persistence + retrieval; `GET /orders/{id}/chain` assembling origin → verdict → confirmation → submission → venue responses → fills → transitions (FR-055)
- [ ] T106 [P] [US5] Web: `/settings/risk` (policy editor with plain-language limits), block explanations in the ticket naming rule/limit/actual, kill-switch control
- [ ] T107 [P] [US5] Metrics + dashboard: blocks by rule, kill-switch engagements, verdict latency

**Checkpoint**: the constitution's Risk Before Profit principle is structurally enforced, not advisory.

---

## Phase 8: User Story 6 — Paper trading mode (Priority: P3)

**Goal**: A complete rehearsal environment using the same order, risk, and reconciliation path, unmistakably labelled.
**Independent Test**: run the full US4 and US5 journeys against a paper account; verify simulated fills carry a model version, the environment badge is present on every surface and payload, and reset restores starting state.

### Tests for User Story 6 ⚠️ write first, must fail

- [ ] T108 [P] [US6] Conformance suite runs green against the paper adapter (all groups) — the CI gate for SC-013
- [ ] T109 [P] [US6] Unit test: fill model applies disclosed spread/slippage/latency deterministically and stamps `fill_model_version`
- [ ] T110 [P] [US6] Integration test: `environment: paper` present on connection, account, order, position, fill, and confirmation payloads (FR-048)
- [ ] T111 [P] [US6] Integration test: reset restores starting balance, increments `reset_count`, records the reset (FR-049)
- [ ] T112 [P] [US6] Integration test: repository rejects any aggregate mixing environments (FR-050)
- [ ] T113 [P] [US6] E2E (Playwright): place, amend, cancel, and hit a risk block entirely in paper mode

### Implementation for User Story 6

- [ ] T114 [US6] Paper execution engine in `venues/adapters/paper/engine.py`: fills against live quotes with the disclosed model, simulated margin/leverage per chosen venue profile
- [ ] T115 [US6] Paper account service + endpoints: `GET/POST /paper/accounts`, `POST /paper/accounts/{id}/reset`, `paper.reset` event
- [ ] T116 [US6] Environment stamping enforcement at the repository layer + response serializers
- [ ] T117 [P] [US6] Web: persistent paper badge on all trading surfaces, paper account creation/reset UI, exclusion of simulated results from any real-performance view

**Checkpoint**: the whole feature is demonstrable and testable without a funded account.

---

## Phase 9: User Story 7 — Reconciliation and audit trail (Priority: P4)

**Goal**: Local state converges on venue truth, every divergence is recorded, and every order is fully explainable.
**Independent Test**: inject each discrepancy class at the simulator, run reconciliation, and verify correct classification, correction, and audit; verify an unresolvable discrepancy holds routing and notifies.

### Tests for User Story 7 ⚠️ write first, must fail

- [ ] T118 [P] [US7] Integration test per discrepancy class: `missing_locally`, `missing_at_venue`, `quantity_mismatch`, `price_mismatch`, `state_mismatch`, `unknown_order`
- [ ] T119 [P] [US7] Integration test: `unresolved` order resolved by targeted reconciliation to the venue's actual state, recorded as `corrected` (FR-030, FR-052)
- [ ] T120 [P] [US7] Integration test: unresolvable discrepancy ⇒ `routing_hold: true`, user + support notified, orders refused with `ATLAS-TRD-011` (FR-053)
- [ ] T121 [P] [US7] Integration test: order chain retrievable for a completed order and for a rejected one (SC-009)
- [ ] T122 [P] [US7] Integration test: erasure event ⇒ subscriptions/intents/mandates/paper/venue-messages deleted, execution records pseudonymized, ack emitted (plan §14)
- [ ] T123 [P] [US7] Chaos test: stream gap ⇒ snapshot reconcile restores agreement without duplicate orders

### Implementation for User Story 7

- [ ] T124 [US7] Reconciliation engine: diff orders/positions/balances, classify, apply venue state, record divergence + correction (`trading/domain/reconciliation/engine.py`)
- [ ] T125 [US7] Trigger wiring: scheduled per connection, on `order.unresolved`, on `feed.recovered` gap, on credential revocation, on demand
- [ ] T126 [US7] Escalation path: routing hold, `reconciliation.escalated` event, support-visible sanitized view (FR-056)
- [ ] T127 [US7] Endpoints: `GET/POST /reconciliation/runs`, `GET /reconciliation/runs/{id}`; report archived to S3
- [ ] T128 [US7] Trading audit taxonomy emission for every transition listed in plan §10, sanitized
- [ ] T129 [US7] Erasure handler + ack for `atlas.privacy.user_erasure.requested`, with the pseudonymization carve-out documented in the export bundle
- [ ] T130 [P] [US7] Web: `/trading/reconciliation` (runs, discrepancies, corrections) and the order-chain view on order detail
- [ ] T131 [P] [US7] Metrics + alerts: drift rate (SC-003), unresolved discrepancy age (page-worthy), reconciliation duration

**Checkpoint**: all seven stories complete; state is provably convergent and auditable.

---

## Phase 10: Polish & Cross-Cutting

- [ ] T132 [P] Runbooks in `docs/runbooks/trading/`: unresolved order, reconciliation escalation, venue outage, rate-limit ban, sidecar restart, kill-switch usage
- [ ] T133 [P] Dashboards: Order Flow, Venue Health, Market Data Freshness, Risk & Blocks, Reconciliation
- [ ] T134 [P] Nightly conformance job against demo accounts for OANDA, Binance testnet, Bybit testnet, IBKR paper, MT5 demo
- [ ] T135 [P] `./scripts/trading-smoke` implementing every row of [quickstart.md](./quickstart.md) §2
- [ ] T136 [P] Egress allowlist test per venue host; secret scanning (gitleaks) and Bandit/pip-audit on the new packages
- [ ] T137 [P] `packages/api-client` regeneration from the trading OpenAPI + TanStack Query hooks
- [ ] T138 [P] Performance validation of SC-002, SC-004, SC-008, SC-012 with results recorded in the spec's success-criteria table
- [ ] T139 `/security-review` on the complete diff, with findings triaged before enabling any live venue flag
- [ ] T140 Pre-live gate checklist execution (plan §19): conformance green, chaos green, 7-day demo drift under threshold, runbooks published, security review closed

---

## Dependencies & Execution Order

```text
Phase 1 Setup
   └─> Phase 2 Foundational (BLOCKING — protocol, schema, guard tests)
          ├─> Phase 3 US1 Connections (P1)
          │        └─> Phase 4 US2 Market data (P1)   [needs a verified connection]
          │                 └─> Phase 5 US3 Account/position sync (P2)
          │                          └─> Phase 6 US4 Order lifecycle (P2)
          │                                   ├─> Phase 7 US5 Risk gate (P3)*
          │                                   ├─> Phase 8 US6 Paper mode (P3)
          │                                   └─> Phase 9 US7 Reconciliation (P4)
          └─> Phase 10 Polish (after the stories it validates)
```

\* **US5 is sequenced after US4 only for delivery order, not for enforcement.** The gate call site
and the `RiskVerdict` requirement are built in T083/T100 together; US4 ships with a minimal gate
(size + kill switch) already on the submit path, and US5 fills in the full rule set. There is no
interim build in which submit is reachable without a verdict.

Within a phase: tests before implementation; migrations before repositories; adapters before the
services that call them; `public.py` surfaces before cross-module consumers.

## Parallel Example

```bash
# Phase 2, after T009–T012 land — migrations and primitives in parallel:
#   T014 instruments/candles migration
#   T016 risk migrations
#   T017 paper/reconciliation migrations
#   T018 seed script
#   T019 precision helpers
#   T023 redaction guard

# Phase 3, after T009–T012:
#   T034 paper adapter        T035 OANDA adapter
#   T036 Binance adapter      T037 Bybit adapter
# (MT5 T038 and IBKR T039 are serial — each owns a sidecar)

# Phase 6, tests first, all independent:
#   T070 conformance execution   T072 duplicate confirm
#   T073 timeout → unresolved    T074 price drift invalidation
#   T075 partial then cancel     T076 amend/cancel refusal
```

## Implementation Strategy

**MVP (P1)**: Phases 1–4 — connect venues and see trustworthy market data. Delivers value with
zero execution risk and proves the adapter protocol against four venues.

**Trading MVP (P1+P2)**: add Phases 5–6 — venue-truthful account state plus confirmed order
placement with at-most-once transmission. This is the first release that can touch money, and it
ships behind `trading.live_orders.enabled=false` (paper and demo only) until Phase 10's gate.

**Complete (P1–P4)**: add Phases 7–9 — full risk enforcement, paper rehearsal, and convergent
reconciliation with a complete audit chain.

### Implementation deviations

Five places where the code deliberately differs from what these tasks assume. Each is a
consequence of what exists upstream, not a change of intent.

| # | Deviation | Why | Seam held open by |
|---|---|---|---|
| 1 | **No Alembic migrations.** T013–T018 land as repository Protocol ports with `InMemory*` implementations. | Spec 00 shipped in-memory only — no SQLAlchemy models, no Alembic tree. Writing the first migration inside a trading spec means designing the persistence foundation here. | Port signatures and in-memory invariants mirror [data-model.md](./data-model.md) table-for-table, including `order_submission`'s uniqueness on `intent_id`. |
| 2 | **No credential vault.** Spec 01 is specified but not implemented. | `use_credential(credential_id, purpose)` has no implementation to call. | `atlas_venues/credentials.py` defines the borrow-per-operation contract with an injected resolver. Adapters already never cache. |
| 3 | **No RBAC scopes or step-up MFA** (T025). | No `auth` module exists to attach permissions to. | Live transmission is gated by config **and** feature flag independently, so the missing third gate cannot be the only thing standing between an intent and the market. |
| 4 | **Five live venue adapters deferred** (MT5, OANDA, Binance, Bybit, IBKR). Only the paper adapter ships. | Request/response shapes, rate-limit weights, and error codes must come from verified vendor documentation and a credentialed sandbox. Guessing them violates "do not invent APIs, data, or contracts" — and a guessed order payload is a wrong order. | The conformance suite (`atlas_venues/conformance.py`) is venue-agnostic and already passes against paper; each adapter's acceptance test is "the existing suite goes green unchanged". |
| 5 | **The float ban is an AST guard test, not a linter rule** (T007). | Ruff has no float-literal rule, and a blanket ban would fire on every timeout and token-bucket rate — a rule people switch off. | `tests/contract/trading/test_no_float_money.py` scopes the ban by identifier meaning and includes a test that the scanner still catches each violation shape. |

### Traceability

| Story | Tasks | Requirements | Success criteria |
|---|---|---|---|
| US1 Connections | T029–T045 | FR-001..008 | SC-001, SC-011 |
| US2 Market data | T046–T058 | FR-009..015 | SC-002, SC-007 |
| US3 Account sync | T059–T069 | FR-016..022 | SC-003, SC-010 |
| US4 Order lifecycle | T070–T093 | FR-023..035 | SC-004, SC-005, SC-006 |
| US5 Risk gate | T094–T107 | FR-036..044 | SC-006, SC-007, SC-008 |
| US6 Paper mode | T108–T117 | FR-045..050 | SC-013 |
| US7 Reconciliation | T118–T131 | FR-051..058 | SC-003, SC-009 |
| Cross-cutting | T001–T028, T132–T140 | FR-008, FR-038 | SC-011, SC-012, SC-013 |

## Summary

- **Total tasks**: 140 (28 setup + foundational, 103 across seven stories, 9 polish)
- **Done so far**: T001–T012, T019–T024, T026–T028 (Phase 1 complete; Phase 2 complete except the
  deferred schema T013–T018 and the Spec 01-blocked T025)
- **Parallelizable**: 62 marked `[P]`
- **Guard tasks that must never regress**: T027 (no risk bypass), T028 (no credential exposure),
  T072 (single transmission per intent), T073 (timeout ⇒ `unresolved`, never a retry)
- **MVP scope**: T001–T058 (P1) — venues connected, market data trustworthy, nothing tradable yet
- **Independent test criteria**: each phase's checkpoint is demonstrable on the paper venue or a
  venue simulator with no funded account
