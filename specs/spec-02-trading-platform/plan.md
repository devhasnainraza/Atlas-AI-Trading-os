# Implementation Plan: Trading Integrations & Broker Layer (Trading Platform)

**Branch**: `02-trading-platform` | **Date**: 2026-08-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/spec-02-trading-platform/spec.md`

## Summary

Deliver Atlas's unified trading execution and market connectivity layer as a modular, high-integrity platform component. The system interfaces seamlessly with traditional forex venues (MT5, OANDA, Interactive Brokers) and crypto exchanges (Binance, Bybit) alongside a built-in deterministic paper execution engine. All broker credentials remain strictly sealed in the Spec 01 envelope-encrypted vault. Every order path is subject to non-bypassable pre-trade risk evaluation, explicit human confirmation for live discretionary execution, deterministic order state lifecycle transitions, continuous background position reconciliation, and normalized real-time WebSocket market data distribution.

## Technical Context

**Language/Version**: Python 3.12 (backend services & workers in `apps/api`), TypeScript 5.x / Next.js 15 (web execution & monitoring interfaces in `apps/web`)  
**Primary Dependencies**: FastAPI + Pydantic v2, SQLAlchemy 2 (async) + Alembic, Redis 7 (real-time tickers, order routing locks, rate limit buckets), aiokafka (execution events), MetaTrader5 (Windows/Wine bridge), ccxt.pro / native aiohttp/websockets (crypto venues), v20 (OANDA REST/streaming), ib_insync (IBKR TWS/Gateway)  
**Storage**: PostgreSQL 16 (venues, connections, accounts, order intents, orders, fills, positions, risk policies), Redis 7 (market data L1/L2 caches, rate limit tokens, reconciliation locks), Kafka (`atlas.trading.*` topics)  
**Testing**: pytest-asyncio + testcontainers (Postgres, Redis, Kafka), mock exchange WebSocket/REST harnesses, deterministic paper engine test suite, order state machine property testing (Hypothesis), Schemathesis (API contracts)  
**Target Platform**: Hybrid containerized deployment (Linux for Core API & Crypto adapters; dedicated Windows/Wine worker container for MT5 execution bridge)  
**Performance Goals**: p95 order routing latency < 15ms (internal processing excluding venue transit); pre-trade risk evaluation < 5ms; market data fan-out p95 < 50ms; 10,000+ orders/sec throughput  
**Constraints**: Absolute ban on floating-point arithmetic for price/volume/PnL (strict `Decimal` / `NUMERIC(24,8)` enforcement); credentials never exposed to client; non-bypassable pre-trade risk gate; fail-closed routing hold on state ambiguity  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Compliance in this plan | Status |
|---|-----------|------------------------|--------|
| I | Human First | Live trade routing requires explicit human intent or signed automated mandate; instant kill-switch and cancel-all available on all UI screens. | ✅ |
| II | Security First | Venue credentials referenced by `credential_id` from Spec 01 vault; decrypted strictly inside backend adapter memory; zero plaintext secrets in logs or API payloads. | ✅ |
| III | Transparency | Every order intent records the originating actor (human/agent), timestamp, risk verdict ID, and fee calculation breakdown. | ✅ |
| IV | Multi-Agent Collab | Standardized Tool interfaces allow future execution and monitoring agents to interact through typed contracts without raw venue bindings. | ✅ |
| V | Explainability | Order rejections emit standardized structured reason codes (e.g., `RISK_DAILY_LOSS_EXCEEDED`, `VENUE_POST_ONLY_RESTRICTION`); execution trace preserved. | ✅ |
| VI | Risk Before Profit | Mandatory pre-trade risk checks run synchronously prior to order dispatch; fail-closed on service failure or market data staleness. | ✅ |
| VII | Continuous Learning | Execution slippage, fill ratios, and latency metrics logged to Kafka for agent learning and model calibration. | ✅ |
| VIII | Privacy by Design | Account identifiers and order books isolated by tenant and user; no cross-user data leaks in cache keys or WebSocket channels. | ✅ |
| IX | Reliability | Automatic circuit breakers per venue; continuous background reconciliation catches phantom fills; state ambiguities trigger `routing_hold`. | ✅ |
| X | Modular Architecture | Ports-and-adapters architecture (`VenueAdapter` ABC) cleanly separates venue protocols from core order and risk engines. | ✅ |
| XI | Observability | Prometheus metrics for order latencies, venue error rates, WebSocket heartbeat drifts; OpenTelemetry distributed tracing across risk and dispatch hops. | ✅ |
| XII | Scalability | Stateless execution dispatchers horizontally scaled with Kafka partition consumers; Redis token buckets prevent venue rate limit penalties. | ✅ |

**Gate result**: PASS.

## 1. High-Level Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│ UI / Agent Callers (HTTP REST / WebSocket / Agent Tools)               │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ apps/api: Trading Module Gateway                                       │
│  - Session Auth & RBAC Check                                           │
│  - Order Intent Ingestion & Validation                                 │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Synchronous Pre-Trade Risk Gate (Risk Engine)                          │
│  - Leverage, Margin, Max Drawdown, Daily Loss, Fat-Finger Limits       │
│  - Fail-Closed: Blocks order if risk limits breached or data stale     │
└───────────────┬───────────────────────────────────────┬────────────────┘
                │ Approved                              │ Rejected
                ▼                                       ▼
┌───────────────────────────────┐       ┌────────────────────────────────┐
│ Order State Machine (DB: PENDING)│     │ Return HTTP 422 with Reason    │
└───────────────┬───────────────┘       └────────────────────────────────┘
                │
                ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Venue Adapter Layer (Ports & Adapters Architecture)                    │
│  - Retrieves sealed credentials via Spec 01 Vault                      │
│  - Translates Normalized Order -> Venue Wire Protocol                  │
│  - Leaky-Bucket Rate Limiter / Circuit Breaker                         │
├───────────────┬───────────────┬───────────────┬────────────────────────┤
│ Binance / CCXT│ MT5 Bridge    │ OANDA v20     │ Paper Engine (Internal)│
└───────┬───────┴───────┬───────┴───────┬───────┴────────┬───────────────┘
        │               │               │                │
        ▼               ▼               ▼                ▼
   [Exchanges]     [Forex Meta]    [OANDA FX]      [Local Orderbook Sim]
        │               │               │                │
        └───────────────┼───────────────┴────────────────┘
                        │ Execution Reports & Fills
                        ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Reconciliation Engine & Event Publisher                                │
│  - Updates Position & Order Tables (`NUMERIC` Decimal arithmetic)      │
│  - Emits `atlas.trading.order_filled` to Kafka                         │
│  - Fan-out to Redis Pub/Sub -> WebSocket to Frontend Clients           │
└────────────────────────────────────────────────────────────────────────┘
```

## 2. Directory Structure

```text
specs/spec-02-trading-platform/
├── spec.md              # Specification document
├── plan.md              # This architecture plan
├── data-model.md        # Data models (venue, order, position, risk)
└── tasks.md             # Test-first task breakdown
```

## 3. Core Technical Decisions & Rationale

### ADR-02-01: Ports-and-Adapters (Hexagonal) Architecture for Venue Integrations
- **Context**: Atlas must support diverse protocols: FIX/REST/WebSocket for crypto, COM/IPC for MT5, proprietary REST/streaming for OANDA and IBKR.
- **Decision**: Define a single abstract base class `VenueAdapter` with strict async methods (`connect`, `submit_order`, `cancel_order`, `get_positions`, `stream_market_data`). Core trading domain logic has zero dependency on exchange SDKs.
- **Consequences**: Adapters can be mocked effortlessly in unit tests. New venues can be added without modifying risk or execution engines.

### ADR-02-02: Synchronous Pre-Trade Risk Gate with In-Memory State & DB Persistence
- **Context**: Asynchronous risk evaluation introduces race conditions where concurrent orders could exceed maximum portfolio exposure.
- **Decision**: Evaluate risk synchronously within the order creation transaction utilizing Redis distributed locks on user account margins, verified against database snapshots.
- **Consequences**: Deterministic risk rejection (<5ms p95 latency overhead). Zero margin slippage under concurrent agent execution.

### ADR-02-03: Strict Decimal Enforcement & Float Ban
- **Context**: Python and JavaScript native floating-point representations cause catastrophic rounding errors in trading calculations (e.g. `0.1 + 0.2 != 0.3`).
- **Decision**: Enforce `decimal.Decimal` in Python across all models, services, and database columns (`NUMERIC(24,8)`). AST linters fail any build containing raw float operations in `apps/api/trading`.
- **Consequences**: 100% exact balance and PnL calculations down to the smallest satoshi or pip.

## 4. Operational Readiness & Reliability

- **Reconciliation Loop**: Periodic background worker executes every 60s per active connection, comparing local positions against venue snapshots. If a discrepancy is detected, a `routing_hold` is triggered automatically, alerting the user and pausing automated order submission until resolved.
- **Emergency Kill-Switch**: A single REST call (`POST /v1/trading/kill-switch`) immediately cancels all active orders across all venues, closes open positions if requested, and disables routing for the user account.
