# Phase 0 Research: Trading Integration Decisions

**Feature**: 003-trading-integration (branch `003-trading-integration`) | **Date**: 2026-08-25
All Technical Context unknowns resolved below. Format: Decision / Rationale / Alternatives.

## 1. Venue abstraction — one adapter protocol, venue-specific adapters

- **Decision**: Define a single `VenueAdapter` protocol in `shared/atlas_venues/` covering
  capability discovery, account snapshot, instrument specs, quote/bar retrieval, streaming
  subscription, order submit/amend/cancel, order & position listing, and normalized error
  classification. Every venue — including the simulated paper venue — implements exactly that
  protocol, and one shared conformance suite runs against all of them (SC-013).
- **Rationale**: Order, risk, and reconciliation logic must be written once; if venue quirks
  leak upward, the risk gate becomes venue-conditional, which is exactly how bypass paths get
  born. A conformance suite is also the only honest way to claim "adding a venue is an adapter".
- **Alternatives**: ccxt as the universal abstraction (excellent for crypto REST, but no
  coverage for MT5/OANDA/IBKR and it leaks exchange-specific params — kept as an option *inside*
  crypto adapters, not as the platform abstraction); per-venue bespoke services (duplicated
  risk logic — rejected outright); FIX protocol as the common layer (right answer for
  institutional venues, wrong cost/coverage for retail forex + crypto today; the adapter
  protocol leaves room for a FIX adapter later).
- **Tradeoffs**: The protocol is a lowest-common-denominator surface. Venue-specific extras
  (Binance's OCO, IBKR's algos) are deliberately excluded from v1 rather than modeled as
  passthrough — passthrough would defeat pre-trade validation.

## 2. Capability negotiation — declared, verified, and enforced

- **Decision**: Each adapter declares a static capability matrix (supported order types, TIF
  values, amend semantics, streaming support, protective-level support, environments) and, at
  connection time, Atlas verifies the *actual* granted permissions from the venue (e.g. an
  exchange key with read-only scope). The narrower of declared-and-granted is stored on the
  connection and enforced before any request.
- **Rationale**: FR-005. A read-only exchange key must fail at compose time with a clear
  message, not at submission with a venue error. Users are encouraged (Spec 01 §9) to store
  read-only keys, so this case is the norm, not the exception.
- **Alternatives**: Trust the user's declared intent (produces confusing venue rejections);
  probe by placing a test order (unacceptable — that is real money).

## 3. MetaTrader 5 connectivity — Windows sidecar bridge

- **Decision**: MT5 is reached through a dedicated bridge process (the official `MetaTrader5`
  Python package plus terminal, running on Windows) exposing a narrow internal RPC that the
  MT5 adapter calls. The bridge is stateless per request apart from the terminal session, is
  never exposed publicly, and receives credentials only per-operation from the vault.
- **Rationale**: The official MT5 API binds to the Windows terminal — there is no supported
  Linux server-side library. A sidecar keeps that constraint isolated behind the adapter
  protocol instead of forcing the whole platform onto Windows.
- **Alternatives**: Broker-specific REST bridges (varies per broker, not portable);
  community Linux/Wine reimplementations (unsupported, unacceptable for order routing);
  MQL5 Expert Advisor + socket bridge (viable and sometimes lower-latency, but ships trading
  logic into MQL where it cannot be tested or risk-gated — rejected on Principle VI);
  dropping MT5 (it is where most retail forex users actually are).
- **Tradeoffs**: An extra operational component with a Windows footprint and its own failure
  mode. Mitigated by: MT5 marked as a capability-limited venue, bridge health surfaced as
  connection health, and the bridge holding no persistent secrets.

## 4. OANDA — v20 REST + streaming endpoints, direct HTTP

- **Decision**: Implement the OANDA adapter directly against the v20 REST API with its
  separate pricing/transaction streaming host; no vendor SDK.
- **Rationale**: The API is small, stable, well documented, and the official Python wrapper is
  thin and lightly maintained; direct HTTP gives us control over timeouts, idempotency headers,
  and retry classification, which are the parts that matter for order safety.
- **Alternatives**: `oandapyV20` (adds little over `httpx`, adds a dependency to audit).

## 5. Crypto venues — native REST/WebSocket per exchange, ccxt only as an internal helper

- **Decision**: Binance and Bybit adapters use each venue's own REST endpoints plus its user
  data / private WebSocket stream for order and position updates, with server-time offset
  tracking and weight-aware rate limiting. ccxt may be used inside a crypto adapter for
  instrument metadata normalization, never for order submission.
- **Rationale**: Order submission needs exact control over the client order id, timestamp
  window, recv-window semantics, and error-code classification (retryable vs terminal). Private
  streams are what make near-real-time fill updates possible instead of polling.
- **Alternatives**: ccxt for everything (its unified error model erases the retryable/terminal
  distinction we depend on for FR-030); polling only (slow, rate-limit hostile).

## 6. Interactive Brokers — IB Gateway sidecar + async client

- **Decision**: IBKR is reached via IB Gateway running as a sidecar with an async
  `ib_insync`-family client in the adapter; IBKR is marked capability-limited for v1 (single
  account per connection, no algo orders).
- **Rationale**: IBKR has no credentialed REST for order routing without Gateway/TWS; this is
  the standard deployment shape. Isolating it as a sidecar mirrors the MT5 decision.
- **Alternatives**: IBKR Client Portal Web API (OAuth-ish, but session-keepalive fragility and
  narrower coverage); deferring IBKR entirely (it is the multi-asset reach the roadmap wants).

## 7. Order idempotency — client order id + submission ledger, never blind retry

- **Decision**: Every order gets an Atlas-generated `client_order_id` (deterministic per
  confirmed intent) that is sent to the venue as its client identifier where supported. A
  submission ledger row is written **before** the outbound call in the same transaction as the
  order row; the ledger enforces at-most-once transmission per intent. On timeout or ambiguous
  error the order moves to `unresolved` and only reconciliation (§11) — never the request path —
  decides its fate.
- **Rationale**: FR-026, FR-030, SC-005. Duplicate order submission is the single most
  expensive bug class in this feature. "Retry on timeout" is the standard way to place the same
  trade twice.
- **Alternatives**: Idempotency-key middleware only (protects the HTTP layer, not the venue
  call); automatic retry with venue-side dedupe (venue support is inconsistent — MT5 has no
  client id semantics comparable to exchanges); optimistic retry with post-hoc cancel (races).
- **Tradeoffs**: An unresolved order needs human-visible latency until reconciliation resolves
  it. Accepted: honest uncertainty beats a confident lie.

## 8. Order state machine — explicit states, venue is authoritative

- **Decision**: `intent → pending_confirmation → risk_checked → submitting → working →
  partially_filled → filled | canceled | rejected | expired`, plus the terminal-adjacent
  `unresolved` state, and `amending`/`canceling` as in-flight sub-states. Transitions are
  append-only events; local state is a projection that reconciliation may correct (FR-020).
- **Rationale**: Making "we do not know" a first-class state is what allows FR-030 and the
  edge cases to be implemented rather than hand-waved. Append-only transitions give FR-055's
  chain for free.
- **Alternatives**: Mirroring one venue's status enum (leaks venue semantics upward); a
  boolean `is_open` with a status string (unrepresentable ambiguity).

## 9. Market data storage — Redis for latest, Postgres for bars, no time-series engine yet

- **Decision**: Latest quote per (venue, instrument) in Redis with an explicit
  `observed_at` and a TTL slightly beyond the freshness limit, so expiry *is* staleness.
  Aggregated bars in Postgres, partitioned by month, with gap markers. No TimescaleDB/ClickHouse
  in this spec.
- **Rationale**: The freshness contract (FR-011/012) is easier to guarantee when absence of a
  key means stale rather than requiring a timestamp comparison everywhere. Bar volume at launch
  (subscribed instruments × timeframes) is comfortably within plain Postgres.
- **Alternatives**: TimescaleDB now (real answer at tick-archive scale — deferred until bar
  retention or tick storage demands it; the repository interface hides the choice);
  in-process caching (breaks horizontal scale, Principle XII); storing every tick (no product
  requirement in this spec, large cost).

## 10. Client streaming — Server-Sent Events for quotes, existing realtime channel for state

- **Decision**: Quote fan-out to browsers over SSE from a dedicated read path fed by Redis
  pub/sub; order, position, and connection state changes ride the platform's existing realtime
  fan-out driven by domain events.
- **Rationale**: Quotes are unidirectional, high-frequency, and reconnect-friendly — SSE is
  simpler than WebSocket and survives proxies well. Order state changes are already events, so
  reusing the existing channel avoids a second push mechanism.
- **Alternatives**: WebSocket for both (needed only if the client must send high-frequency
  upstream messages, which it does not — orders are ordinary requests); long polling (latency
  budget in SC-002 fails).

## 11. Reconciliation — scheduled, event-triggered, and venue-wins

- **Decision**: Reconciliation runs (a) on a schedule per connection, (b) immediately after any
  `unresolved` order, (c) on reconnect after a stream gap, and (d) on demand. It diffs orders,
  positions, and balances, classifies each discrepancy (`missing_locally`, `missing_at_venue`,
  `quantity_mismatch`, `price_mismatch`, `state_mismatch`, `unknown_order`), applies the venue's
  state, and records both divergence and correction. Unresolvable discrepancies hold order
  routing for that account until settled.
- **Rationale**: FR-051/052/053. Positions opened outside Atlas and the `unresolved` state both
  require this to exist for the feature to be safe at all.
- **Alternatives**: Trust local state (guarantees eventual divergence); reconcile only on user
  request (the divergence is discovered at the worst possible moment).

## 12. Risk gate placement — synchronous, in-process, single entry point, no override parameter

- **Decision**: One `RiskGate.evaluate(order_intent, context) → RiskVerdict` call sits on the
  only code path that can reach an adapter's submit method. There is no `skip_risk`, `force`, or
  admin bypass parameter anywhere in the API surface, service layer, or adapter protocol — the
  absence is asserted by a contract test, mirroring Spec 01's "no endpoint returns plaintext".
  Missing or stale inputs produce `blocked`, never `allowed`.
- **Rationale**: Constitution VI is absolute and FR-038 demands no override path. An override
  flag that exists "for emergencies" is a bypass that will be used.
- **Alternatives**: Risk as middleware (bypassable by internal callers); risk as an async
  pre-check (race between check and submit); advisory risk with a confirm-anyway button
  (directly contradicts the constitution).
- **Tradeoffs**: Legitimate edge cases (a user certain a limit is wrong) require changing the
  policy first, which applies only to future orders (FR-044). That friction is the point.

## 13. Money and quantity arithmetic — Decimal end to end, venue precision at the boundary

- **Decision**: All prices, quantities, and money use `Decimal` with venue-declared precision
  applied at the adapter boundary; floats are banned in trading domain code (lint rule).
  Quantity is validated against the instrument's min/max/step before transmission.
- **Rationale**: Float rounding changes the order actually sent (FR-033, edge case on
  precision). This is cheap to enforce now and expensive to retrofit.
- **Alternatives**: Integer minor units (correct but awkward across FX pips, crypto 8+ decimals,
  and per-venue steps); floats with rounding helpers (rejected).

## 14. Time — reconciled venue offset, injected clock

- **Decision**: Each adapter tracks a venue server-time offset (refreshed periodically) used for
  timestamp-windowed venue requests. All Atlas-side time rules (session guards, daily loss
  windows, intent and mandate expiry) use the platform's injected clock in UTC, with session
  schedules stored per instrument in venue-local terms and resolved to UTC.
- **Rationale**: Clock skew silently breaks exchange auth windows and daily-window rules; the
  injected clock keeps the domain deterministically testable (Spec 00 standard).
- **Alternatives**: Local system time everywhere (skew and DST bugs); venue time as the system
  of record (multiple venues disagree).

## 15. Venue rate limiting — per-connection token buckets, weight-aware, degrade not drop

- **Decision**: Per-connection token buckets in Redis, configured from each adapter's declared
  limit model (including request-weight models), shared across API and worker processes. On
  exhaustion, non-urgent traffic (bar backfill, instrument refresh) is shed first; order and
  cancel requests hold priority; sustained exhaustion degrades the connection with a
  user-visible reason.
- **Rationale**: FR-035. A venue ban takes out the whole user, so limits must be respected
  platform-wide, not per-process. Cancellation must never queue behind backfill.
- **Alternatives**: In-process limiters (wrong under horizontal scale); reactive backoff only
  (bans arrive before backoff learns).

## 16. Paper trading — a venue adapter, not a special case

- **Decision**: The paper engine implements `VenueAdapter` like any other venue, filling
  against live quotes with a disclosed model (configurable spread widening, slippage, and
  latency), maintaining simulated balance/positions in Postgres. Environment is stamped on the
  connection, every account/order/position record, and every confirmation payload; simulated
  data is excluded from any real-performance figure.
- **Rationale**: Reuses the entire order, risk, and reconciliation path — which is precisely
  what makes paper mode a valid rehearsal (US6) and a safe test bed for future agents. It also
  gives the conformance suite (§1) a venue that always runs in CI.
- **Alternatives**: A separate simulated code path (tests a different system than the one users
  trade with — rejected); venue demo accounts only (unavailable for some venues, requires
  credentials, and cannot be reset on demand — demo remains supported *in addition*).

## 17. Credential handling — per-operation retrieval through the vault, never cached

- **Decision**: Adapters receive credentials only via Spec 01's
  `credentials.public.use_credential(credential_id, purpose)` with purpose `trade` or
  `read_only`, per operation, zeroized after use; no adapter, connection object, or sidecar
  persists secret material. Credential revocation events immediately quarantine the connection
  and trigger reconciliation of in-flight orders.
- **Rationale**: Constitution II and Spec 01's consumer obligation on
  `atlas.credentials.credential.revoked`. Long-lived authenticated venue sessions (MT5 terminal,
  IB Gateway) are the awkward case and are handled as: session established per connection,
  torn down on revocation, credentials never written to disk.
- **Alternatives**: Cache decrypted credentials per connection for performance (defeats
  revocation and widens blast radius — rejected); pass credentials to the client for direct
  venue calls (catastrophic, and forbidden by FR-008).

## 18. Degraded modes — explicit, user-visible, and refusal-biased

- **Decision**: A connection is `healthy | degraded | expired | failed | quarantined`; an
  account view is `live | stale | unknown`; an instrument's data is `fresh | stale`. Order
  submission requires healthy connection + fresh data + resolved reconciliation state. Anything
  else refuses with a reason and a recommendation to wait.
- **Rationale**: Constitution IX — the safe default is inaction, stated plainly. Encoding the
  degraded states explicitly is what stops "temporarily fell back to stale data" from happening
  silently.
- **Alternatives**: Best-effort execution with warnings (the failure mode this product exists
  to prevent).
