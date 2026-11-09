# Tasks: Trading Automation

**Input**: Design documents from `/specs/spec-06-trading-automation/`
**Prerequisites**: [spec.md](./spec.md), Spec 00, Spec 02 (execution), Spec 05 (proposals)
**Tests**: INCLUDED — circuit breaker trip invariants, news embargo time tests, and trailing stop precision benchmarks.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: `US1`–`US3`, or blank for setup/foundational/polish

---

## Phase 1: Setup

- [x] T001 [P] Scaffold automation module in `apps/api/src/atlas_api/modules/automation/`
- [x] T002 [P] Configure `AutomationSettings` (news embargo window minutes, max default daily loss limit) in `shared/atlas_core/config.py`
- [x] T003 [P] Register automation events in `shared/atlas_events/catalog.py`: `automation.mandate.activated`, `automation.circuit_breaker.tripped`, `automation.position.breakeven_moved`

---

## Phase 2: Foundational (⚠️ CRITICAL — blocks every user story)

- [x] T004 Create Alembic migration for `automation_mandates` and `automation_circuit_breaker_events` in `apps/api/src/atlas_api/modules/automation/migrations/`
- [x] T005 [P] Implement `AutomationSupervisorDaemon` in `services/worker/src/automation/supervisor.py` maintaining in-memory position state
- [x] T006 [P] Implement Circuit Breaker Evaluator enforcing daily loss limits and consecutive loss cooldowns

---

## Phase 3: User Story 1 — Smart SL/TP & Dynamic Trailing Stop (Priority: P1) 🎯 MVP

**Goal**: Positions automatically adjust Stop Loss to Breakeven upon TP1 fill and trail profits with dynamic volatility stops.

### Tests for User Story 1 ⚠️ write first, must fail

- [x] T007 [P] [US1] Unit test: TP1 fill event triggers automated Stop Loss modification to entry price + spread
- [x] T008 [P] [US1] Unit test: Trailing stop accurately updates watermark and advances stop price as price expands
- [x] T009 [P] [US1] Integration test: Multi-target scaling closes 50% at TP1, 25% at TP2, and trails remaining runner

### Implementation for User Story 1

- [x] T010 [US1] Implement Smart Stop Loss calculator (ATR multiples, structural swing points) in `apps/api/src/atlas_api/modules/automation/domain/smart_stops.py`
- [x] T011 [US1] Implement Multi-Target Take Profit execution engine in `apps/api/src/atlas_api/modules/automation/domain/take_profit.py`
- [x] T012 [US1] Implement Trailing Stop Daemon listening to live market ticks in `services/worker/src/automation/trailing.py`
- [ ] T013 [P] [US1] Web: Active Position Protection card with live trailing stop and Breakeven visual indicator

---

## Phase 4: User Story 2 — News Protection & Trading Session Embargoes (Priority: P1)

**Goal**: Automated strategies pause entries before high-impact news releases and operate strictly within defined market sessions.

### Tests for User Story 2 ⚠️ write first, must fail

- [x] T014 [P] [US2] Unit test: Orders submitted 10 minutes prior to CPI announcement are rejected with news lockout error
- [x] T015 [P] [US2] Unit test: Trading outside authorized session hours (e.g. Asian session for London mandate) is blocked

### Implementation for User Story 2

- [x] T016 [US2] Implement News Embargo Guard querying Spec 04 economic calendar in `apps/api/src/atlas_api/modules/automation/domain/news_guard.py`
- [x] T017 [US2] Implement Session Hours Filter (London, New York, Tokyo) with UTC alignment
- [x] T018 [US2] Wire news protection status badge into trade entry pipelines

---

## Phase 5: User Story 3 — Daily Drawdown Circuit Breakers & Emergency Stop (Priority: P1)

**Goal**: Automatic cessation of trading upon hitting loss thresholds, backed by a global emergency stop button.

### Tests for User Story 3 ⚠️ write first, must fail

- [x] T019 [P] [US3] Unit test: Exceeding daily drawdown threshold disarms mandates and rejects subsequent order intents
- [x] T020 [P] [US3] Integration test: Emergency Stop cancels all open venue orders within 500ms

### Implementation for User Story 3

- [x] T021 [US3] Implement Daily Loss Accumulator tracking realized + unrealized equity fluctuations
- [x] T022 [US3] Implement `POST /api/v1/automation/emergency-stop` endpoint executing batch cancellations and position flatten options
- [x] T023 [US3] Implement `POST /api/v1/automation/circuit-breakers/reset` with mandatory admin authorization
- [ ] T024 [P] [US3] Web: Global Emergency Kill Switch button in top navigation bar with slide-to-confirm modal

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T025 [P] Trailing stop execution latency benchmarks under high-frequency tick bursts
- [ ] T026 [P] SRE Runbook: Recovering from automated circuit breaker halts and reviewing loss attribution
