# Implementation Plan: Trading Automation

**Branch**: `06-trading-automation` | **Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/spec-06-trading-automation/spec.md`

## Summary

Deliver Atlas's high-precision trading automation engine: supporting three distinct operational modes (Manual, Semi-Automatic with human sign-off, and Fully Autonomous Mandates strictly bounded by user-defined risk budgets). Features dynamic multi-stage exit management (ATR-based stop losses, partial TP scaling with automatic Breakeven ratcheting, dynamic trailing stops), continuous AI-driven trade exit surveillance, real-time macroeconomic news blackouts, session time windows, and multi-tier capital protection circuit breakers (daily loss caps, consecutive loss cooldowns, and one-click emergency flatten panic buttons).

## Technical Context

**Language/Version**: Python 3.12 (automation daemon & position guard workers in `apps/api`), TypeScript 5.x / Next.js 15 (automation command cockpit & circuit breaker gauges in `apps/web`)  
**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2 (async) + Alembic, Redis 7 (in-memory position guard states, tick subscriptions, rate limiters), aiokafka, APScheduler / Celery Beat (session and news embargo schedules), numpy / pandas-ta (ATR and Chandelier exit calculations)  
**Storage**: PostgreSQL 16 (automation mandates, circuit breaker audit logs, position guard configurations), Redis 7 (sub-millisecond active position monitors, trailing stop triggers, daily loss counters), Kafka (`atlas.automation.*` topics)  
**Testing**: pytest-asyncio, time-travel tick replay harnesses (Freezegun), synthetic market tick generators simulating flash crashes and slippage, Hypothesis property tests for invariant circuit breaker halts  
**Target Platform**: Low-latency containerized daemon service (`services/worker/src/automation/`) running with persistent hot in-memory Redis synchronization  
**Performance Goals**: Signal-to-venue dispatch latency < 35ms p95 in fully automatic mode; trailing stop recalculation < 100ms per price tick; emergency flatten dispatch < 200ms glass-to-venue; circuit breaker evaluation < 2ms  
**Constraints**: Ban on floating-point arithmetic (`Decimal` / `NUMERIC(28,10)` throughout); fully autonomous mandates require cryptographic signing and strict capital bounds; circuit breakers fail-closed on service disconnect; news protection embargoes non-bypassable  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Compliance in this plan | Status |
|---|-----------|------------------------|--------|
| I | Human First | Default mode is Semi-Automatic; Fully Autonomous mode requires explicit signed mandate; emergency stop available on all UI screens. | ✅ |
| II | Security First | Mandate activation requires secondary authentication; automation daemon cannot modify user risk ceilings beyond server caps. | ✅ |
| III | Transparency | Every automated trade execution records the authorizing mandate ID, circuit breaker status snapshot, and slippage metric. | ✅ |
| IV | Multi-Agent Collab | Execution, Risk, and Market agents coordinate via typed Kafka events to monitor trade invalidations. | ✅ |
| V | Explainability | Exit actions, breakeven moves, and circuit breaker halts emit explicit reason codes (e.g. `ATLAS-AUTO-NEWS-LOCK`, `ATLAS-AUTO-BREAKEVEN-TRIGGER`). | ✅ |
| VI | Risk Before Profit | Mandatory Stop Loss attached to 100% of entries; daily loss circuit breaker is non-bypassable and overrides all active strategies. | ✅ |
| VII | Continuous Learning | Execution slippage, trailing stop efficiency, and exit timing telemetry fed to Learning Agent for parameter tuning. | ✅ |
| VIII | Privacy by Design | Automation mandates and positions are strictly scoped to `user_id` and `account_id`. | ✅ |
| IX | Reliability | Automation daemon maintains heartbeat; if worker stalls or loses venue connection, mandates immediately transition to `SUSPENDED`. | ✅ |
| X | Modular Architecture | Automation engine interacts with Spec 02 Venue Adapters purely through abstract interfaces and standardized order intents. | ✅ |
| XI | Observability | Latency histograms, circuit breaker trip counters, and position guard tick frequencies exported to Prometheus and Grafana. | ✅ |
| XII | Scalability | Redis pub/sub shards position guard tick processing across multiple stateless worker threads by symbol. | ✅ |

**Gate result**: PASS.

## 1. High-Level Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│ UI / Trader Cockpit (Mode Selection, Mandate Setup, Emergency Stop)    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Automation Supervisor Daemon (services/worker/src/automation)          │
│                                                                        │
│   ┌───────────────────────────┐     ┌───────────────────────────┐      │
│   │    Automation Mandates    │     │    Circuit Breaker Hub    │      │
│   │  - Symbol whitelist       │     │  - Daily loss tracker     │      │
│   │  - Max risk % per trade   │     │  - News blackout detector │      │
│   │  - Concurrent pos caps    │     │  - Session hours schedule │      │
│   └─────────────┬─────────────┘     └─────────────┬─────────────┘      │
│                 │                                 │                    │
│                 └────────────────┬────────────────┘                    │
│                                  ▼                                     │
│   ┌─────────────────────────────────────────────────────────────┐      │
│   │                   Signal Validation & Gate                  │      │
│   │    (Mode = Full Auto -> Verify Mandate; Semi-Auto -> Modal) │      │
│   └──────────────────────────────┬──────────────────────────────┘      │
└──────────────────────────────────┼─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Position Guard & Exit Management Engine (Hot Redis State)               │
│                                                                        │
│   ┌───────────────────────────┐     ┌───────────────────────────┐      │
│   │    Smart SL / TP Engine   │     │    Trailing Stop Engine   │      │
│   │  - ATR-based dynamic SL   │     │  - Chandelier / High-Water│      │
│   │  - Auto-Breakeven at TP1  │     │  - Step-based trailing    │      │
│   └─────────────┬─────────────┘     └─────────────┬─────────────┘      │
│                 │                                 │                    │
│                 └────────────────┬────────────────┘                    │
│                                  ▼                                     │
│   ┌─────────────────────────────────────────────────────────────┐      │
│   │                   AI Trade Exit Monitor                     │      │
│   │     (Continuous order flow & thesis invalidation check)     │      │
│   └──────────────────────────────┬──────────────────────────────┘      │
└──────────────────────────────────┼─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Venue Execution Layer (Spec 02 Adapters: Binance, MT5, OANDA, etc.)    │
└────────────────────────────────────────────────────────────────────────┘
```

## 2. Directory Structure

```text
specs/spec-06-trading-automation/
├── spec.md              # Specification document
├── plan.md              # This architecture plan
├── data-model.md        # Data models (mandates, circuit breakers, guards)
└── tasks.md             # Test-first task breakdown
```

## 3. Core Technical Decisions & Rationale

### ADR-06-01: Redis In-Memory Position Guard State with Postgres Write-Through
- **Context**: Evaluating trailing stops and breakeven adjustments across hundreds of market ticks per second requires sub-millisecond read/write latency.
- **Decision**: Maintain active position guard states (`current_stop_loss`, `tp1_filled`, `highest_price_seen`) in Redis hashes, asynchronously writing updates to PostgreSQL on state transitions.
- **Consequences**: Enables sub-100ms reaction time to tick events while preserving durable audit history in PostgreSQL.

### ADR-06-02: Strict Separation of Automation Modes
- **Context**: Ambiguity between manual trader actions and automated agent interventions causes execution conflict and accountability failures.
- **Decision**: Tag every order intent with its exact authorization mode: `MANUAL`, `SEMI_AUTOMATIC`, or `FULLY_AUTOMATIC` (with linked `mandate_id`).
- **Consequences**: Absolute transparency in trade logs and post-mortem attribution.

### ADR-06-03: Hard Automated News Blackout Window
- **Context**: Economic news spikes (e.g. CPI, NFP) exhibit extreme slippage and spread widening that invalidate algorithmic strategies.
- **Decision**: Non-bypassable scheduler embargoes trade entries 15 minutes before and after scheduled High-Impact events unless user explicitly opts into high-risk mode.
- **Consequences**: Prevents catastrophic slippage during liquidity gaps.
