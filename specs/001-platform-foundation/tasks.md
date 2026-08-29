# Tasks: Platform Foundation & Core System Architecture

**Input**: Design documents from `/specs/001-platform-foundation/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/
**Tests**: Included because the spec requires automated tests and contract validation.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the monorepo shell, root tooling, and repo hygiene needed before any feature work.

- [x] T001 Create the monorepo root manifests and workspace wiring in `package.json`, `pnpm-workspace.yaml`, `pyproject.toml`, and `turbo.json`
- [x] T002 Add repository hygiene and developer entrypoint files in `.gitignore`, `.editorconfig`, `.nvmrc`, `.python-version`, and `README.md`
- [x] T003 [P] Add baseline command placeholders for bootstrap, lint, db, client generation, and smoke checks in `scripts/bootstrap`, `scripts/lint-all`, `scripts/db`, `scripts/generate-client`, `scripts/dev-reset`, and `scripts/smoke-events`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the shared platform scaffolds that every user story depends on.

- [x] T004 [P] Create the Python shared package skeletons in `shared/atlas_core/`, `shared/atlas_events/`, `shared/atlas_observability/`, and `shared/atlas_ai/`
- [x] T005 [P] Create the frontend and shared TypeScript package skeletons in `apps/web/`, `packages/ui/`, `packages/api-client/`, and `packages/config/`
- [x] T006 Implement the shared configuration, error taxonomy, correlation ID, and settings helpers in `shared/atlas_core/config.py`, `shared/atlas_core/errors.py`, `shared/atlas_core/correlation.py`, and `shared/atlas_observability/bootstrap.py`
- [x] T007 Implement the API app factory, middleware stack, and base health routes in `apps/api/src/atlas_api/main.py` and `apps/api/src/atlas_api/middleware/`
- [x] T008 Add the local container, deploy, and CI scaffolds in `infra/docker/`, `infra/k8s/`, `infra/terraform/`, and `.github/workflows/`

**Checkpoint**: Foundation ready — user story work can now proceed.

---

## Phase 3: User Story 1 - Module Developer Adds a New Capability (Priority: P1) 🎯 MVP

**Goal**: A developer can scaffold a new module, expose one API operation, and use shared platform services without touching existing modules.

**Independent Test**: Scaffold the sample module, expose one endpoint, and verify module boundaries prevent internal cross-module imports.

- [x] T009 [P] [US1] Define the module registration contract and scaffold template in `apps/api/src/atlas_api/modules/_template/` and `apps/api/src/atlas_api/modules/public.py`
- [x] T010 [P] [US1] Implement the sample module public interface, domain, service, router, and events in `apps/api/src/atlas_api/modules/sample/`
- [x] T011 [US1] Register the sample module in the app factory and unified API router in `apps/api/src/atlas_api/main.py` and `apps/api/src/atlas_api/modules/platform/`
- [x] T012 [P] [US1] Enforce module boundary rules in `pyproject.toml`, `packages/config/dependency-cruiser.cjs`, and `apps/api/pyproject.toml`
- [x] T013 [US1] Add module scaffold and isolation tests in `apps/api/tests/modules/sample/test_module_registration.py` and `tests/contract/test_module_boundaries.py`

---

## Phase 4: User Story 2 - Modules Communicate Through Events (Priority: P2)

**Goal**: A module can publish events, other modules can subscribe independently, and failures retry into DLQ/replay flows.

**Independent Test**: Publish a sample event, verify a second consumer receives it, force a failure into DLQ, and replay historical events.

- [x] T014 [P] [US2] Define the event envelope, catalog, and foundation event schemas in `shared/atlas_events/envelope.py`, `shared/atlas_events/catalog.py`, and `specs/001-platform-foundation/contracts/platform-events.md`
- [x] T015 [P] [US2] Implement the transactional outbox, publisher, subscriber, processed-event ledger, and dead-letter adapters in `shared/atlas_events/`
- [x] T016 [P] [US2] Implement worker relay, retry, and replay flows in `services/worker/src/atlas_worker/events.py` and `apps/api/src/atlas_api/modules/platform/events.py`
- [x] T017 [US2] Publish the sample proof event from `apps/api/src/atlas_api/modules/sample/events.py` and wire replay-capable consumption
- [x] T018 [US2] Add event contract and DLQ/replay tests in `tests/contract/test_platform_events.py` and `services/worker/tests/test_event_reliability.py`

---

## Phase 5: User Story 3 - Operator Observes and Operates the Platform (Priority: P3)

**Goal**: An operator can inspect health, correlate requests, view dashboards, and audit critical actions.

**Independent Test**: Exercise a request across services, trace it by correlation ID, and verify degraded dependencies surface in readiness and alerts.

- [x] T019 [P] [US3] Implement correlation-aware structured logging, metrics, and tracing bootstrap in `shared/atlas_observability/` and `apps/api/src/atlas_api/main.py`
- [x] T020 [P] [US3] Implement liveness, readiness, and dependency status reporting in `apps/api/src/atlas_api/modules/platform/router.py` and `shared/atlas_core/dependencies.py`
- [x] T021 [US3] Add the audit log entity, repository, and admin read endpoints in `apps/api/src/atlas_api/modules/platform/domain/audit_log_entry.py`, `apps/api/src/atlas_api/modules/platform/repository/audit_log.py`, and `apps/api/src/atlas_api/modules/platform/router.py`
- [x] T022 [P] [US3] Provision dashboards, alerts, and runbooks in `infra/observability/` and `docs/runbooks/`
- [x] T023 [US3] Add observability integration tests in `tests/integration/test_health_and_logging.py` and `tests/contract/test_audit_log_api.py`

---

## Phase 6: User Story 4 - Client Developer Consumes Versioned APIs (Priority: P4)

**Goal**: Clients get one unified API entry point with validation, rate limiting, stable errors, and versioned compatibility.

**Independent Test**: Send malformed and over-limit requests, confirm the error envelope and 429 behavior, and verify a v2 surface does not break v1 clients.

- [x] T024 [P] [US4] Implement request validation, error envelope mapping, security headers, and rate limiting middleware in `apps/api/src/atlas_api/middleware/`
- [x] T025 [P] [US4] Wire versioned `/v1` routing, browsable OpenAPI publishing, and compatibility routes in `apps/api/src/atlas_api/main.py` and `apps/api/src/atlas_api/modules/sample/router_v2.py`
- [x] T026 [P] [US4] Generate the typed API client and schema sync flow in `packages/api-client/` and `scripts/generate-client`
- [x] T027 [US4] Add API contract tests for malformed requests, rate limits, and version coexistence in `tests/contract/test_platform_api.py`

---

## Phase 7: User Story 5 - Platform Runs the Same Everywhere (Priority: P5)

**Goal**: The platform boots locally with one documented procedure and deploys from the same artifacts across environments.

**Independent Test**: From a fresh clone, start the local stack, run smoke checks, and confirm the same artifacts can be templated for deployment.

- [x] T028 [P] [US5] Create the local Compose stack and multi-stage Dockerfiles in `infra/docker/compose.yaml`, `infra/docker/compose.dev.yaml`, `infra/docker/Dockerfile.api`, `infra/docker/Dockerfile.web`, `infra/docker/Dockerfile.worker`, and `infra/docker/Dockerfile.scheduler`
- [x] T029 [P] [US5] Add environment files and daily-use scripts in `infra/docker/.env.example`, `scripts/bootstrap`, `scripts/db`, `scripts/lint-all`, `scripts/dev-reset`, and `scripts/smoke-events`
- [x] T030 [P] [US5] Scaffold Helm charts and Terraform modules for the deployable units in `infra/k8s/` and `infra/terraform/`
- [x] T031 [US5] Publish the quickstart, onboarding, and platform runbook docs in `specs/001-platform-foundation/quickstart.md`, `docs/onboarding/local-development.md`, and `docs/runbooks/platform-foundation.md`
- [x] T032 [US5] Add end-to-end local-stack smoke validation in `tests/e2e/test_local_stack.py` and `.github/workflows/ci.yaml`

---

## Phase 8: User Story 6 - Operator Toggles Features Without Deploying (Priority: P6)

**Goal**: Feature flags can change behavior quickly, safely, and with a defined default when evaluation fails.

**Independent Test**: Toggle a guarded capability and verify the change propagates without restart; simulate provider failure and verify fallback behavior.

- [x] T033 [P] [US6] Implement shared feature-flag interfaces and client wrappers in `shared/atlas_core/feature_flags.py` and `packages/config/src/feature-flags.ts`
- [x] T034 [P] [US6] Implement flag evaluation, GitOps webhook ingestion, and audit recording in `apps/api/src/atlas_api/modules/platform/router.py` and `services/worker/src/atlas_worker/flags.py`
- [x] T035 [P] [US6] Add a sample guarded capability and frontend fallback behavior in `apps/api/src/atlas_api/modules/sample/router.py` and `apps/web/src/lib/flags.ts`
- [x] T036 [US6] Add feature-flag contract and propagation tests in `tests/contract/test_feature_flags.py` and `tests/integration/test_flag_propagation.py`

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Finish shared quality gates, docs, and validation artifacts that cut across stories.

- [x] T037 [P] Add CI pipelines for lint, typecheck, unit/integration/contract, security, build, and Helm validation in `.github/workflows/ci.yaml` and `.github/workflows/security.yaml`
- [x] T038 [P] Add repository documentation and architecture index in `README.md`, `docs/architecture.md`, and `docs/module-conventions.md`
- [x] T039 [P] Add security scan and secret-detection configs in `gitleaks.toml`, `.bandit.yml`, and `trivy.yaml`
- [x] T040 [P] Refresh the quickstart validation evidence and final smoke notes in `specs/001-platform-foundation/quickstart.md` and `docs/runbooks/platform-foundation.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies; start immediately.
- **Foundational (Phase 2)**: depends on Phase 1; blocks all user stories.
- **User Stories (Phases 3+)**: depend on Phase 2.
- **Polish (Phase 9)**: depends on the desired user stories being complete.

### User Story Dependencies

- **US1 (P1)**: first MVP slice; no dependency on later stories.
- **US2 (P2)**: can begin after Phase 2; sample event proof is easiest once US1's sample module scaffold exists.
- **US3 (P3)**: can begin after Phase 2 and benefits from the sample module work, but stays independently testable.
- **US4 (P4)**: can begin after Phase 2; versioning proof uses the API shell and sample module.
- **US5 (P5)**: can begin after Phase 2; full local-stack smoke becomes strongest once US1–US4 exist.
- **US6 (P6)**: can begin after Phase 2; frontend fallback proof benefits from the API and web shells.

### Within Each User Story

- Tests should be written before implementation where practical.
- Shared scaffolds come before concrete module/service code.
- Story-specific tests should confirm the story is independently usable.
- Keep cross-story coupling to public interfaces and events only.

### Parallel Opportunities

- Setup tasks T003 can run alongside T001/T002.
- Foundational tasks T004/T005 can run in parallel.
- User stories can proceed in parallel after Phase 2, with T009/T010, T014/T015/T016, T019/T020/T022, T024/T025/T026, T028/T029/T030, and T033/T034/T035 all parallelizable inside their story boundaries.

---

## Parallel Example: User Story 1

```bash
Task: "Define the module registration contract and scaffold template in apps/api/src/atlas_api/modules/_template/ and apps/api/src/atlas_api/modules/public.py"
Task: "Implement the sample module public interface, domain, service, router, and events in apps/api/src/atlas_api/modules/sample/"
Task: "Enforce module boundary rules in pyproject.toml, packages/config/dependency-cruiser.cjs, and apps/api/pyproject.toml"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational.
3. Complete Phase 3: User Story 1.
4. Validate the module scaffold and boundary rules.
5. Stop if US1 does not stand alone.

### Incremental Delivery

1. Foundation first.
2. Add US1 to prove modular extension.
3. Add US2 to prove event-driven communication.
4. Add US3 to prove operability.
5. Add US4 to prove API consistency.
6. Add US5 to prove environment parity.
7. Add US6 to prove safe runtime toggles.

