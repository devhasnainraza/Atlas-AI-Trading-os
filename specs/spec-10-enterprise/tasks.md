# Tasks: Enterprise Features

**Input**: Design documents from `/specs/spec-10-enterprise/`
**Prerequisites**: [spec.md](./spec.md), Spec 00, Spec 01 (RBAC), Spec 02 (risk limits)
**Tests**: INCLUDED — multi-tenant row-level security isolation, dual-approval risk workflow, and Stripe webhook metering tests.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: `US1`–`US3`, or blank for setup/foundational/polish

---

## Phase 1: Setup

- [x] T001 [P] Scaffold enterprise module in `apps/api/src/atlas_api/modules/enterprise/`
- [x] T002 [P] Add Stripe SDK dependency (`stripe`) to `apps/api/pyproject.toml`
- [x] T003 [P] Configure `EnterpriseSettings` (Stripe API keys, webhook signing secrets, custom domain CNAME targets) in `shared/atlas_core/config.py`
- [x] T004 [P] Register enterprise events in `shared/atlas_events/catalog.py`: `enterprise.org.created`, `enterprise.member.invited`, `enterprise.webhook.dispatched`

---

## Phase 2: Foundational (⚠️ CRITICAL — blocks every user story)

- [x] T005 Create Alembic migration for `enterprise_organizations` and `enterprise_memberships` in `apps/api/src/atlas_api/modules/enterprise/migrations/`
- [x] T006 [P] Implement PostgreSQL Row-Level Security (RLS) policies enforcing `org_id` isolation across all enterprise queries
- [x] T007 [P] Implement Enterprise Webhook Dispatcher with HMAC-SHA256 signatures in `apps/api/src/atlas_api/modules/enterprise/service/webhooks.py`

---

## Phase 3: User Story 1 — Multi-Tenant Org & Hierarchical Risk Controls (Priority: P1) 🎯 MVP

**Goal**: Hedge funds and prop desks enforce organization-wide daily loss limits and dual-approval gates for junior traders.

### Tests for User Story 1 ⚠️ write first, must fail

- [x] T008 [P] [US1] Unit test: Junior trader order exceeding 2 lots requires Senior Trader approval token
- [x] T009 [P] [US1] Integration test: Desk-wide 4.0% loss limit trips circuit breaker for all team members

### Implementation for User Story 1

- [x] T010 [US1] Implement Organization & Workspace Management Service in `apps/api/src/atlas_api/modules/enterprise/service/organization.py`
- [x] T011 [US1] Implement Hierarchical Risk Policy Evaluator in `apps/api/src/atlas_api/modules/enterprise/domain/risk_hierarchy.py`
- [x] T012 [US1] Implement `POST /api/v1/enterprise/members/invite` and `/organizations/{id}/policies`
- [ ] T013 [P] [US1] Web: Enterprise Admin & Desk Risk Control Console in `apps/web/src/features/enterprise/`

---

## Phase 4: User Story 2 — White-Label Portal & Custom Branding (Priority: P1)

**Goal**: Partner brokerages deploy the platform with custom domains, brand logos, and customized theme tokens.

### Tests for User Story 2 ⚠️ write first, must fail

- [x] T014 [P] [US2] Unit test: Multi-tenant host header router resolves tenant organization by CNAME domain
- [x] T015 [P] [US2] Integration test: Custom theme variables dynamically inject into Next.js layout

### Implementation for User Story 2

- [x] T016 [US2] Implement Tenant Domain Resolution Middleware in `apps/api/src/atlas_api/middleware/tenant.py`
- [x] T017 [US2] Implement White-Label Configuration Service in `apps/api/src/atlas_api/modules/enterprise/service/branding.py`
- [ ] T018 [P] [US2] Web: Dynamic Theme Provider loading custom logos and CSS variables based on tenant

---

## Phase 5: User Story 3 — Enterprise Webhook Ingestion & Metered Billing (Priority: P2)

**Goal**: Algorithmic funds receive real-time execution webhooks, and organizations are billed via Stripe based on active seats and agent token usage.

### Tests for User Story 3 ⚠️ write first, must fail

- [x] T019 [P] [US3] Unit test: Webhook payload carries valid `X-Atlas-Signature` HMAC-SHA256 header
- [x] T020 [P] [US3] Integration test: Stripe usage record creation accurately syncs monthly LLM token consumption

### Implementation for User Story 3

- [x] T021 [US3] Implement Stripe Billing Manager (Subscription tiers, seat count management) in `apps/api/src/atlas_api/modules/enterprise/service/billing.py`
- [x] T022 [US3] Implement Token Usage Metering worker tracking LLM consumption per tenant
- [x] T023 [US3] Implement `POST /api/v1/enterprise/webhooks` subscription endpoint

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T024 [P] Compliance Audit Export Service generating cryptographically signed CSV/JSON packages
- [ ] T025 [P] Enterprise API documentation and interactive Swagger developer portal
