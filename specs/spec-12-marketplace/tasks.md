# Tasks: AI Marketplace

**Input**: Design documents from `/specs/spec-12-marketplace/`
**Prerequisites**: [spec.md](./spec.md), Spec 00, Spec 03 (agents), Spec 06 (automation), Spec 10 (billing)
**Tests**: INCLUDED — sandbox escape penetration tests, backtest provenance verification, and Stripe Connect split payout accounting tests.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: `US1`–`US3`, or blank for setup/foundational/polish

---

## Phase 1: Setup

- [x] T001 [P] Scaffold marketplace module in `apps/api/src/atlas_api/modules/marketplace/`
- [x] T002 [P] Configure `MarketplaceSettings` (Stripe Connect client ID, sandbox resource limits: 512MB RAM, 1 CPU core) in `shared/atlas_core/config.py`
- [x] T003 [P] Register marketplace events in `shared/atlas_events/catalog.py`: `marketplace.plugin.submitted`, `marketplace.plugin.verified`, `marketplace.plugin.installed`

---

## Phase 2: Foundational (⚠️ CRITICAL — blocks every user story)

- [x] T004 Create Alembic migration for `marketplace_plugins` and `marketplace_installations` in `apps/api/src/atlas_api/modules/marketplace/migrations/`
- [x] T005 [P] Implement `AtlasPluginManifest` validator and cryptographic signature verifier in `apps/api/src/atlas_api/modules/marketplace/domain/manifest.py`
- [x] T006 [P] Implement Sandboxed Plugin Runtime Executor (gVisor container or WASM runner) with restricted system call profiles in `shared/atlas_ai/sandbox.py`

---

## Phase 3: User Story 1 — 1-Click Plugin Discovery & Installation (Priority: P1) 🎯 MVP

**Goal**: Users browse verified agents and strategies, installing them into their workspace with one click.

### Tests for User Story 1 ⚠️ write first, must fail

- [x] T007 [P] [US1] Unit test: Installing a plugin binds manifest capabilities without granting unauthorized broker access
- [x] T008 [P] [US1] Integration test: 1-click install provisions state and initializes sandboxed agent within 2 seconds
- [x] T009 [P] [US1] Contract test: `GET /api/v1/marketplace/plugins` against OpenAPI schema

### Implementation for User Story 1

- [x] T010 [US1] Implement Marketplace Catalog Search Service in `apps/api/src/atlas_api/modules/marketplace/service/catalog.py`
- [x] T011 [US1] Implement Plugin Installation & License Manager in `apps/api/src/atlas_api/modules/marketplace/service/installation.py`
- [x] T012 [US1] Implement `POST /api/v1/marketplace/plugins/{id}/install` endpoint
- [x] T013 [P] [US1] Web: Marketplace Discovery App Store grid and filter tabs in `apps/web/src/features/marketplace/`

---

## Phase 4: User Story 2 — Creator Portal & Automated Verification Pipeline (Priority: P1)

**Goal**: Quantitative creators upload strategy packages and undergo automated AST security and 3-year historical backtesting before publishing.

### Tests for User Story 2 ⚠️ write first, must fail

- [x] T014 [P] [US2] Security test: Plugin containing unauthorized filesystem or socket calls fails automated AST scan
- [x] T015 [P] [US2] Integration test: Automated backtest runner simulates 3 years of historical EUR/USD ticks and records verified metrics

### Implementation for User Story 2

- [x] T016 [US2] Implement AST Security Scanner checking prohibited import and execution calls in `apps/api/src/atlas_api/modules/marketplace/service/verifier.py`
- [x] T017 [US2] Implement Automated Backtest Verification Worker in `services/worker/src/jobs/backtest_runner.py`
- [x] T018 [US2] Implement `POST /api/v1/marketplace/creator/submit` endpoint
- [x] T019 [P] [US2] Web: Creator Portal package upload and backtest performance dashboard in `apps/web/src/features/marketplace/creator/`

---

## Phase 5: User Story 3 — Sandbox Isolation & Pre-Trade Risk Gate Protection (Priority: P1)

**Goal**: Third-party marketplace agents run strictly in sandboxes and cannot bypass the native Pre-Trade Risk Gate.

### Tests for User Story 3 ⚠️ write first, must fail

- [x] T020 [P] [US3] Unit test: Marketplace agent trade proposals are routed through the host Pre-Trade Risk Gate
- [x] T021 [P] [US3] Penetration test: Sandboxed agent attempting direct network call to external IP is intercepted and blocked

### Implementation for User Story 3

- [x] T022 [US3] Implement Subgraph Sandboxing Wrapper intercepting marketplace LangGraph nodes
- [x] T023 [US3] Implement Host Pre-Trade Risk Enforcer strictly validating third-party trade signals before venue dispatch

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T024 [P] Implement Stripe Connect 70/30 creator revenue split and payout accounting ledger
- [x] T025 [P] User review and 5-star rating system with verified purchase tags
