# Tasks: Memory, Journal & Learning

**Input**: Design documents from `/specs/spec-07-memory-learning/`
**Prerequisites**: [spec.md](./spec.md), Spec 00, Spec 02 (fills), Spec 03 (memory agent)
**Tests**: INCLUDED — user vector partition isolation, revenge trading detector precision, and chart snapshot capture tests.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: `US1`–`US3`, or blank for setup/foundational/polish

---

## Phase 1: Setup

- [x] T001 [P] Scaffold memory and journal module skeletons in `apps/api/src/atlas_api/modules/journal/` and `modules/memory/`
- [x] T002 [P] Configure `JournalSettings` (S3 chart storage bucket, screenshot service endpoint) in `shared/atlas_core/config.py`
- [x] T003 [P] Register journal events in `shared/atlas_events/catalog.py`: `journal.entry.created`, `learning.bias.detected`, `learning.coaching.published`

---

## Phase 2: Foundational (⚠️ CRITICAL — blocks every user story)

- [x] T004 Create Alembic migration for `journal_entries` and `memory_user_embeddings` in `apps/api/src/atlas_api/modules/journal/migrations/`
- [x] T005 [P] Implement user-scoped vector retrieval repository enforcing `WHERE user_id = :current_user` in `apps/api/src/atlas_api/modules/memory/repository/`
- [x] T006 [P] Implement S3 presigned image upload and WebP optimization pipeline in `shared/atlas_core/storage.py`

---

## Phase 3: User Story 1 — Automated Multimedia Trade Journaling (Priority: P1) 🎯 MVP

**Goal**: Every trade closing triggers automatic capture of chart screenshots, entry/exit ticks, R-multiples, and AI post-mortem debrief.

### Tests for User Story 1 ⚠️ write first, must fail

- [x] T007 [P] [US1] Unit test: R-multiple calculation accurately evaluates PnL relative to initial stop-loss risk
- [x] T008 [P] [US1] Integration test: Position closed event in Kafka automatically generates journal entry with chart snapshot within 3 seconds
- [x] T009 [P] [US1] Contract test: `GET /api/v1/journal/entries` against OpenAPI schema

### Implementation for User Story 1

- [x] T010 [US1] Implement Trade Close Consumer in `services/worker/src/consumers/journal_consumer.py`
- [x] T011 [US1] Implement Headless Chart Capture service generating WebP images with plotted trade levels
- [x] T012 [US1] Implement `JournalService` generating AI post-mortem comparing planned vs. actual outcome in `apps/api/src/atlas_api/modules/journal/service.py`
- [x] T013 [US1] Implement `POST /api/v1/journal/entries/{id}/annotate` for user emotion tagging and notes
- [ ] T014 [P] [US1] Web: Interactive Multimedia Journal view with chart previews and emotion badges in `apps/web/src/features/journal/`

---

## Phase 4: User Story 2 — Behavioral Anomaly & Revenge Trading Detection (Priority: P1)

**Goal**: Learning Agent identifies negative psychological loops (revenge trading, overtrading) and alerts the trader with cooldown suggestions.

### Tests for User Story 2 ⚠️ write first, must fail

- [x] T015 [P] [US2] Unit test: Opening oversized position < 5 minutes after a loss triggers Revenge Trading alert
- [x] T016 [P] [US2] Unit test: Daily trade frequency exceeding 2 standard deviations triggers Overtrading warning

### Implementation for User Story 2

- [x] T017 [US2] Implement Behavioral Pattern Analyzer in `apps/api/src/atlas_api/modules/journal/domain/behavior.py`
- [x] T018 [US2] Implement Cognitive Bias Profile scoring engine (FOMO, revenge trading, loss aversion)
- [x] T019 [US2] Wire coaching warning modal into order submission pipelines when bias is triggered

---

## Phase 5: User Story 3 — Weekly AI Coaching Diagnostics (Priority: P2)

**Goal**: Sunday evening AI coach report highlights weekly profit factor, disciplined decisions, and optimal market hours.

### Tests for User Story 3 ⚠️ write first, must fail

- [x] T020 [P] [US3] Unit test: Weekly coach accurately computes win rate by market session (London vs. New York)
- [x] T021 [P] [US3] Integration test: Scheduled Celery Beat job compiles and saves coaching report for all active users

### Implementation for User Story 3

- [x] T022 [US3] Implement Coaching Synthesis Engine in `apps/api/src/atlas_api/modules/journal/service/coaching.py`
- [x] T023 [US3] Implement Celery Beat cron job scheduled for Sundays at 21:00 UTC
- [ ] T024 [P] [US3] Web: Weekly AI Coach Dossier view in `apps/web/src/features/journal/coaching/`

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T025 [P] Implement `atlas.privacy.user_deleted` subscriber deleting journal records and vector partitions
- [ ] T026 [P] Image storage lifecycle policy configuration in MinIO / AWS S3
