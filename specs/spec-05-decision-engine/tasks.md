# Tasks: Decision Engine & Risk Management

**Input**: Design documents from `/specs/spec-05-decision-engine/`
**Prerequisites**: [spec.md](./spec.md), Spec 00, Spec 02 (pre-trade risk), Spec 03 (agent core)
**Tests**: INCLUDED — constitutional risk overrides, debate consistency fuzzing, and Bayesian calibration tests.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: `US1`–`US3`, or blank for setup/foundational/polish

---

## Phase 1: Setup

- [x] T001 [P] Scaffold decision engine module in `apps/api/src/atlas_api/modules/decision/`
- [x] T002 [P] Configure `DecisionSettings` (confidence threshold default 65.0%, debate rounds, risk max weights) in `shared/atlas_core/config.py`
- [x] T003 [P] Register decision events in `shared/atlas_events/catalog.py`: `decision.proposal.created`, `decision.risk.vetoed`, `decision.proposal.approved`

---

## Phase 2: Foundational (⚠️ CRITICAL — blocks every user story)

- [x] T004 Create Alembic migration for `decision_proposals` table in `apps/api/src/atlas_api/modules/decision/migrations/`
- [x] T005 [P] Implement Bayesian Confidence Scoring algorithm in `apps/api/src/atlas_api/modules/decision/domain/confidence.py`
- [x] T006 [P] Implement Constitutional Risk Policy Validator (Principle VI) guaranteeing risk rules override profit signals

---

## Phase 3: User Story 1 — Dialectic AI Debate Pipeline (Priority: P1) 🎯 MVP

**Goal**: Adversarial debate between Bull and Bear agents challenges every trade setup before synthesis.

### Tests for User Story 1 ⚠️ write first, must fail

- [x] T007 [P] [US1] Unit test: Bear advocate surfaces hidden resistance and invalidates weak technical breakouts
- [x] T008 [P] [US1] Integration test: Complete 8-stage debate pipeline executes in < 6 seconds with streaming fixtures
- [x] T009 [P] [US1] Contract test: `/api/v1/decision/evaluate` returns structured debate transcript

### Implementation for User Story 1

- [x] T010 [US1] Implement `BullAdvocateNode` formulating maximum upside thesis in `apps/api/src/atlas_api/modules/decision/domain/debate.py`
- [x] T011 [US1] Implement `BearAdvocateNode` challenging thesis and seeking falsification conditions
- [x] T012 [US1] Implement `SynthesisArbitratorNode` reconciling conflicting arguments and checking for logical fallacies
- [x] T013 [US1] Construct the LangGraph Debate Graph in `apps/api/src/atlas_api/modules/decision/service.py`
- [ ] T014 [P] [US1] Web: Dialectic Debate split-screen view in `apps/web/src/features/decision/`

---

## Phase 4: User Story 2 — Constitutional Risk Hard Override (Priority: P1)

**Goal**: Pre-trade risk gate strictly halts and vetoes high-confidence trades if drawdown or exposure caps are breached.

### Tests for User Story 2 ⚠️ write first, must fail

- [x] T015 [P] [US2] Unit test: 95% confidence trade is unconditionally blocked when daily loss limit is reached
- [x] T016 [P] [US2] Integration test: Risk veto generates structured rejection event and logs explainable audit entry

### Implementation for User Story 2

- [x] T017 [US2] Implement Pre-Trade Risk Evaluation Node invoking Spec 02 risk gate
- [x] T018 [US2] Implement Fail-Safe "WAIT / NO_TRADE" fallback routing when confidence < 65%
- [x] T019 [US2] Wire risk rejection notifications to user dashboard

---

## Phase 5: User Story 3 — Transparent 4-Part Proposal Delivery (Priority: P1)

**Goal**: Deliver actionable, transparent proposals containing Confidence %, Evidence, Risks, and Alternative Scenarios.

### Tests for User Story 3 ⚠️ write first, must fail

- [x] T020 [P] [US3] Unit test: Proposal serializer raises validation error if any of the 4 required elements is missing
- [x] T021 [P] [US3] Integration test: Human cryptographic approval triggers order execution hand-off

### Implementation for User Story 3

- [x] T022 [US3] Implement Proposal Generator formulating Entry, Stop Loss, and Take Profit targets (minimum 1:1.5 R:R)
- [x] T023 [US3] Implement `POST /api/v1/decision/proposals/{id}/approve` and `/reject` endpoints
- [ ] T024 [P] [US3] Web: Interactive Proposal Card with mini-chart and countdown timer

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T025 [P] Run 10,000 synthetic setup evaluations to verify Bayesian confidence calibration
- [ ] T026 [P] Proposal TTL auto-expiry background worker in `services/worker/src/jobs/proposal_expiry.py`
