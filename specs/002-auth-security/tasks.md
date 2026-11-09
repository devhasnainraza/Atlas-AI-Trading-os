# Tasks: Authentication, Security & User Management Platform

**Input**: Design documents from `/specs/002-auth-security/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (all present)

**Tests**: INCLUDED — the constitution mandates test-first for new behavior and plan §23
defines the strategy; every story ships its contract/integration/abuse tests before or with
implementation.

**Organization**: Phases 3–7 map 1:1 to spec user stories US1–US5 (P1–P5). Paths follow the
Spec 00 monorepo: backend modules in `apps/api/src/atlas_api/modules/`, shared Python in
`shared/`, web features in `apps/web/src/features/`, workers in `services/worker/`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizable (different files, no dependency on an incomplete task)
- **[Story]**: US1–US5 for user-story phases only

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Scaffolds, dependencies, and config surface for the two new modules

- [X] T001 Scaffold `auth` module skeleton (public.py, router.py, schemas.py, service/, domain/, repository/, events.py, deps.py, README.md) in apps/api/src/atlas_api/modules/auth/
- [X] T002 [P] Scaffold `credentials` module skeleton (same layout) in apps/api/src/atlas_api/modules/credentials/
- [X] T003 [P] Add auth dependencies (authlib, argon2-cffi, PyJWT[crypto], pyotp, cryptography, zxcvbn, user-agents, geoip2) to apps/api/pyproject.toml and uv.lock via `uv add`
- [X] T004 [P] Add AUTH_* / VAULT_* / OAUTH_* settings sections (fail-fast Pydantic Settings, no defaults for security fields; VAULT_KEK_LOCAL rejected when ENV=production) in shared/atlas_core/config.py and infra/docker/.env.example
- [X] T005 [P] Add Mailpit service + GeoLite2 volume to infra/docker/compose.yaml and wire SMTP env for local email catching
- [X] T006 [P] Extend scripts/bootstrap to generate local ES256 JWT keypair + cookie-signing keys and write scripts/auth-smoke skeleton in scripts/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Crypto, token, middleware, event, and error primitives every story needs

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 Initialize Alembic migration branches `auth` and `credentials` (empty baseline revisions) in apps/api/src/atlas_api/modules/auth/migrations/ and apps/api/src/atlas_api/modules/credentials/migrations/
- [X] T008 [P] Implement TokenService (ES256 mint/verify, 15-min TTL, claims sub/sid/roles_ver/mfa, kid rotation support) + `/.well-known/jwks.json` route in apps/api/src/atlas_api/modules/auth/service/tokens.py
- [X] T009 [P] Implement PasswordHasher (Argon2id 64MiB/t3/p4, versioned params, rehash-on-verify) in apps/api/src/atlas_api/modules/auth/service/hashing.py
- [X] T010 [P] Implement vault EnvelopeCrypto (AES-256-GCM per-credential DEK, KekProvider interface with LocalEnvKek + KmsKek stub, AAD binding, crypto-shred) in apps/api/src/atlas_api/modules/credentials/service/crypto.py
- [X] T011 [P] Implement one-time token machinery (issue/consume SHA-256-hashed single-use rows, purpose policies 24h/30m/15m) in apps/api/src/atlas_api/modules/auth/service/one_time_tokens.py
- [X] T012 Replace DevIdentityProvider seam with real AuthMiddleware (bearer + `__Host-` cookie parsing, JWT verify, sid denylist check for sensitive route class) in apps/api/src/atlas_api/middleware/authn.py
- [X] T013 Implement CSRF double-submit middleware for cookie-authenticated mutations in apps/api/src/atlas_api/middleware/csrf.py
- [X] T014 [P] Register auth error codes (ATLAS-AUTH-001..008, ATLAS-CRED-001..004) with uniform enumeration-safe messages in shared/atlas_core/errors.py
- [X] T015 [P] Register auth rate-limit classes (auth-strict, sensitive, default) and per-account backoff counter helpers (Redis) in shared/atlas_core/ratelimit.py
- [X] T016 [P] Define event schemas for atlas.auth.* / atlas.credentials.* / atlas.privacy.* per contracts/auth-events.md in shared/atlas_events/catalog/auth.py
- [X] T017 [P] Implement auth email dispatch worker consumer (verification/reset/magic/security-alert templates via Notifier interface, queued with retries) in services/worker/src/consumers/auth_emails.py
- [X] T018 [P] Extend audit writer with auth action taxonomy + secret-redaction guard tests in shared/atlas_observability/audit.py

**Checkpoint**: Crypto/token/middleware primitives ready — user stories can start

---

## Phase 3: User Story 1 - Secure Account Creation and Sign-In (Priority: P1) 🎯 MVP

**Goal**: Register with email verification + consents; sign in via email/password, Google,
GitHub, Apple, magic link; sessions issued with rotating refresh tokens.

**Independent Test**: Fresh account → verify email (Mailpit) → login → refresh rotates →
invalid credentials rejected uniformly (spec US1 acceptance scenarios).

### Tests for User Story 1 ⚠️ write first, must fail

- [ ] T019 [P] [US1] Contract tests for register/verify/login/refresh/logout/magic-link/oauth endpoints (Schemathesis + explicit cases) in tests/contract/auth/test_us1_auth_endpoints.py
- [ ] T020 [P] [US1] Integration test register→verify→consents→login→refresh-rotation→reuse-revokes-family in apps/api/src/atlas_api/modules/auth/tests/integration/test_registration_login.py
- [ ] T021 [P] [US1] Integration test OAuth callback (mocked providers) incl. account-linking confirmation rule in apps/api/src/atlas_api/modules/auth/tests/integration/test_oauth_flows.py

### Implementation for User Story 1

- [X] T022 [US1] Migration 001: user, user_profile, consent_record, oauth_account, verification_token, session, device tables per data-model.md in apps/api/src/atlas_api/modules/auth/migrations/versions/001_identity_core.py
- [X] T023 [P] [US1] Domain entities + status state machine (user, session family, device) in apps/api/src/atlas_api/modules/auth/domain/models.py
- [X] T024 [P] [US1] Repositories (UserRepo, SessionRepo, DeviceRepo, OAuthAccountRepo, ConsentRepo) in apps/api/src/atlas_api/modules/auth/repository/
- [X] T025 [US1] RegistrationService (create pending user, consent recording, verification issue/consume, resend cooldown, enumeration-safe semantics) in apps/api/src/atlas_api/modules/auth/service/registration.py
- [ ] T026 [US1] SessionService (login, refresh rotation + family revocation, logout/logout-all, device upsert, cookie/bearer response shaping) in apps/api/src/atlas_api/modules/auth/service/sessions.py
- [ ] T027 [US1] OAuthService (Authlib Google/GitHub/Apple, PKCE+state+nonce, link-confirmation challenge, last-method-unlink guard) in apps/api/src/atlas_api/modules/auth/service/oauth.py
- [ ] T028 [US1] MagicLinkService (request/consume, 15-min single-use) in apps/api/src/atlas_api/modules/auth/service/magic_link.py
- [ ] T029 [US1] Auth routers: /auth/register, /auth/verify-email(+resend), /auth/login, /auth/refresh, /auth/logout(-all), /auth/magic-link(+consume), /auth/oauth/{provider}/start+callback per contracts/auth-api.openapi.yaml in apps/api/src/atlas_api/modules/auth/router.py
- [ ] T030 [US1] Publish + consume US1 events (user.registered, email_verified, login_succeeded/failed, session.revoked) wiring outbox in apps/api/src/atlas_api/modules/auth/events.py
- [ ] T031 [P] [US1] Web: register/login/verify pages + auth API hooks + cookie session handling in apps/web/src/features/auth/
- [ ] T032 [US1] Playwright E2E: US1 journey (register→verify→login→logout) in tests/e2e/auth/us1_registration_login.spec.ts

**Checkpoint**: MVP — a user can securely create an account and sign in with all methods

---

## Phase 4: User Story 2 - Protect and Recover Access (Priority: P2)

**Goal**: Password reset/change with history + breach checks, TOTP MFA + recovery codes,
lockout/backoff, session & device management UI.

**Independent Test**: Reset password without secret exposure; enable MFA → new-device login
requires second factor; revoke one/all sessions takes effect immediately (spec US2).

### Tests for User Story 2 ⚠️ write first, must fail

- [ ] T033 [P] [US2] Contract tests password forgot/reset/change, mfa totp enroll/activate/disable, recovery-codes, step-up, sessions/devices endpoints in tests/contract/auth/test_us2_protection_endpoints.py
- [ ] T034 [P] [US2] Integration tests reset-flow (sessions revoked), MFA enroll→login-challenge→recovery-code path, trusted-device skip in apps/api/src/atlas_api/modules/auth/tests/integration/test_mfa_recovery.py
- [ ] T035 [P] [US2] Abuse suite: brute-force→backoff→lockout, enumeration timing, replay of used tokens, CSRF negative cases in tests/security/auth_abuse/test_lockout_enumeration_replay.py

### Implementation for User Story 2

- [ ] T036 [US2] Migration 002: mfa_totp_factor, recovery_code, password_history tables + user lockout columns in apps/api/src/atlas_api/modules/auth/migrations/versions/002_protection.py
- [ ] T037 [P] [US2] PasswordPolicyService (zxcvbn ≥3, HIBP k-anonymity with fail-open flag, history-5 check) in apps/api/src/atlas_api/modules/auth/service/password_policy.py
- [ ] T038 [US2] PasswordService (forgot/reset/change, session revocation on change, notifications) in apps/api/src/atlas_api/modules/auth/service/passwords.py
- [ ] T039 [US2] MfaService (TOTP enroll/activate/disable, step replay guard, recovery-code batches, step-up freshness, login MFA challenge continuation token) in apps/api/src/atlas_api/modules/auth/service/mfa.py
- [ ] T040 [US2] LockoutService (per-account exponential backoff, IP throttles, lockout events + emails, CAPTCHA flag hook) in apps/api/src/atlas_api/modules/auth/service/lockout.py
- [ ] T041 [US2] Routers: /auth/password/*, /mfa/*, /sessions, /sessions/{id}, /devices, /devices/{id}/trust per contract in apps/api/src/atlas_api/modules/auth/router.py
- [ ] T042 [P] [US2] Web: password reset/change flows, MFA enrollment wizard (QR + codes shown once), sessions & devices management under apps/web/src/features/auth/settings/
- [ ] T043 [US2] Playwright E2E: reset + MFA + revoke-all journeys in tests/e2e/auth/us2_protect_recover.spec.ts

**Checkpoint**: Accounts are protected and recoverable; US1 unaffected

---

## Phase 5: User Story 3 - Connected Credentials & External Accounts (Priority: P3)

**Goal**: Envelope-encrypted vault for broker/exchange/AI/webhook secrets — store, rotate,
revoke, delete with zero plaintext after save; connected accounts with status/health.

**Independent Test**: Add credential → only masked ref visible anywhere; rotate → old value
dead; revoke → retrieval denied + audited; account detail shows status/permissions/last sync
(spec US3).

### Tests for User Story 3 ⚠️ write first, must fail

- [ ] T044 [P] [US3] Contract tests /credentials* and /connected-accounts* incl. assertion that NO response schema can carry secret material in tests/contract/auth/test_us3_vault_endpoints.py
- [ ] T045 [P] [US3] Integration tests encrypt→store→rotate→revoke→crypto-shred with real Postgres; use_credential purpose gating + audit rows in apps/api/src/atlas_api/modules/credentials/tests/integration/test_vault_lifecycle.py

### Implementation for User Story 3

- [ ] T046 [US3] Migration 001 (credentials branch): credential, credential_version, connected_account tables in apps/api/src/atlas_api/modules/credentials/migrations/versions/001_vault.py
- [ ] T047 [P] [US3] Domain models + lifecycle state machines (credential status, version status, account health) in apps/api/src/atlas_api/modules/credentials/domain/models.py
- [ ] T048 [US3] VaultService (create/rotate/revoke/delete with step-up enforcement, masked serialization, validation probes per provider kind) in apps/api/src/atlas_api/modules/credentials/service/vault.py
- [ ] T049 [US3] `use_credential(credential_id, purpose)` server-side public API with purpose matching, single-request handle, audit + retrieved event in apps/api/src/atlas_api/modules/credentials/public.py
- [ ] T050 [US3] ConnectedAccountService (link to credential/oauth_account, status transitions, reconnect/disconnect) + scheduled health-probe job in apps/api/src/atlas_api/modules/credentials/service/connected_accounts.py and services/scheduler/src/jobs/account_health.py
- [ ] T051 [US3] Routers: /credentials (list/create), /credentials/{id}/(rotate|revoke|validate), DELETE /credentials/{id}, /connected-accounts* per contract in apps/api/src/atlas_api/modules/credentials/router.py
- [ ] T052 [P] [US3] Web: credentials manager (add w/ write-once UX, masked list, rotate/revoke dialogs) + connected accounts page in apps/web/src/features/credentials/
- [ ] T053 [US3] Playwright E2E: store→mask→rotate→revoke→disconnect journey in tests/e2e/auth/us3_credentials.spec.ts

**Checkpoint**: External secrets are safe; future broker/AI specs consume public.py only

---

## Phase 6: User Story 4 - Roles and Enterprise-Ready Access (Priority: P4)

**Goal**: Deny-by-default RBAC with seeded system roles, instant permission refresh, admin
role management — org/team-scope-ready without building orgs.

**Independent Test**: Assign role → allowed actions change immediately; out-of-permission
action denied consistently for every role (spec US4 matrix).

### Tests for User Story 4 ⚠️ write first, must fail

- [ ] T054 [P] [US4] Table-driven RBAC matrix test (every seeded role × representative endpoint set → allow/deny) in apps/api/src/atlas_api/modules/auth/tests/integration/test_rbac_matrix.py
- [ ] T055 [P] [US4] Contract tests /admin/users*, roles PUT, lock PUT incl. audit-entry assertions in tests/contract/auth/test_us4_admin_endpoints.py

### Implementation for User Story 4

- [ ] T056 [US4] Migration 003: role, permission, role_permission, user_role (scope columns), user.roles_ver in apps/api/src/atlas_api/modules/auth/migrations/versions/003_rbac.py
- [ ] T057 [US4] Seed system roles/permissions (guest/user/premium/support/admin + reserved org roles; premium ⊇ user seeding) in apps/api/src/atlas_api/modules/auth/seed.py
- [ ] T058 [US4] PermissionResolver (cached role→permission sets, roles_ver staleness re-resolution, deny-by-default enforcement in authz dependency) in apps/api/src/atlas_api/modules/auth/service/authorization.py
- [ ] T059 [US4] Declare required_permissions on every existing auth/credentials/platform route + CI check that unknown/undeclared permission keys fail the build in apps/api/src/atlas_api/modules/*/router.py and scripts/check-permissions
- [ ] T060 [US4] Admin service + routers (user search masked, set roles with step-up + roles_ver bump, lock/unlock) in apps/api/src/atlas_api/modules/auth/service/admin.py and router.py
- [ ] T061 [P] [US4] Web: minimal admin users page (search, roles editor, lock toggle) gated by admin permissions in apps/web/src/features/admin/users/

**Checkpoint**: Server-side authorization is real everywhere; org model unblocked for later

---

## Phase 7: User Story 5 - Observe Security and Control Privacy (Priority: P5)

**Goal**: Security center (score, sessions, devices, alerts, recommendations), security
event pipeline (new device / impossible travel / token reuse), API keys, audit visibility,
privacy export + deletion with erasure contract.

**Independent Test**: Security center shows required panels; sensitive actions produce
reviewable audit records; export delivers bundle; deletion removes linked artifacts after
grace (spec US5).

### Tests for User Story 5 ⚠️ write first, must fail

- [ ] T062 [P] [US5] Contract tests /security/*, /api-keys*, /privacy/* in tests/contract/auth/test_us5_security_privacy_endpoints.py
- [ ] T063 [P] [US5] Integration tests: impossible-travel + new-device event raising, export bundle content (no secrets), deletion grace→hard-delete with crypto-shred + pseudonymized audit in apps/api/src/atlas_api/modules/auth/tests/integration/test_security_privacy.py
- [ ] T064 [P] [US5] Erasure-coverage contract test: walk module registry, fail if any module with user-linked tables lacks an erasure subscription in tests/contract/auth/test_erasure_coverage.py

### Implementation for User Story 5

- [ ] T065 [US5] Migration 004: security_event, privacy_request, api_key tables in apps/api/src/atlas_api/modules/auth/migrations/versions/004_security_privacy.py
- [ ] T066 [US5] SecurityAnalyzer worker consumer (login events → GeoIP enrichment, new-device, impossible-travel >900km/h, token-reuse escalation → security_event + alert event) in services/worker/src/consumers/security_analyzer.py
- [ ] T067 [US5] SecurityCenterService (versioned score formula, overview aggregation, recommendations rules, events list/ack) + routers /security/* in apps/api/src/atlas_api/modules/auth/service/security_center.py
- [ ] T068 [US5] ApiKeyService (atlas_ prefix generation, show-once, SHA-256 storage, scope ⊆ owner, bearer path support in AuthMiddleware) + /api-keys routers in apps/api/src/atlas_api/modules/auth/service/api_keys.py
- [ ] T069 [US5] PrivacyService + worker jobs: export bundle→S3 presigned (7d), deletion request with 14-day grace/cancel, hard-delete orchestration publishing atlas.privacy.user_erasure.requested and awaiting acks in apps/api/src/atlas_api/modules/auth/service/privacy.py and services/worker/src/jobs/privacy_jobs.py
- [ ] T070 [P] [US5] Web: Security Center page (score, logins, sessions, devices, keys, alerts, recommendations) + privacy page (export/download, delete w/ grace state) in apps/web/src/features/security/
- [ ] T071 [US5] Playwright E2E: security center review + export + deletion-cancel journey in tests/e2e/auth/us5_security_privacy.spec.ts

**Checkpoint**: All five stories independently functional

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T072 [P] Auth dashboards (Auth overview, Abuse, Vault) + alert rules (stuffing spike, token-reuse, DLQ growth for auth topics, KEK age) as code in infra/k8s/observability/auth/
- [ ] T073 [P] Runbooks: lockout storms, token-reuse incident, KEK rotation/rewrap, vault restore decrypt canary in docs/runbooks/auth/
- [ ] T074 [P] k6 load scenarios: login storm 1k VU p95<2s (SC-002), refresh throughput, vault ops in tests/load/auth_login_storm.js
- [ ] T075 [P] ZAP baseline profile for auth routes + nightly CI job in .github/workflows/security-nightly.yml
- [ ] T076 Terraform: KMS key + alias for vault KEK, GeoLite2 refresh job, OAuth secret entries via ESO in infra/terraform/modules/auth/
- [ ] T077 Fix SpecKit script/dir mismatch: make check-prerequisites.sh, setup-plan.sh, update-agent-context.sh, create-phr.sh resolve specs dir from branch OR rename specs dirs to match branches (pick one convention) in .specify/scripts/bash/common.sh
- [ ] T078 Validate quickstart end-to-end on fresh clone (all §2 smoke flows green) and update specs/002-auth-security/quickstart.md discrepancies
- [ ] T079 Pre-production security review: run /security-review on the full auth diff, triage findings, and record external pentest scope doc in docs/security/pentest-scope.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)** → nothing; T001 before T002-only-if-same-files (they are separate — all [P] eligible after T001 creates no shared files; run T001+T002 in parallel)
- **Phase 2 (Foundational)** ← Phase 1. T007 first (migration branches); T008–T018 parallelizable except T012/T013 (middleware chain order, same area)
- **US1 (Phase 3)** ← Phase 2 — no story dependencies
- **US2 (Phase 4)** ← Phase 2 (+ uses US1's session tables from T022; testable independently via its own fixtures)
- **US3 (Phase 5)** ← Phase 2 only (credentials module is self-contained; step-up check no-ops gracefully if MFA not enrolled)
- **US4 (Phase 6)** ← Phase 2 (+ T059 touches routers from US1–US3, schedule after their routers exist or accept merge conflicts)
- **US5 (Phase 7)** ← Phase 2; analyzer (T066) consumes US1 login events; export/delete touch US3 vault via public.py
- **Phase 8 (Polish)** ← all desired stories

### Story completion order (single developer)

US1 → US2 → US3 → US4 → US5 (matches P1–P5). Parallel team: after Phase 2, US1+US3 can run
concurrently (different modules); US2 follows US1; US4/US5 last (they touch shared routers/
events from earlier stories).

### Parallel Example: User Story 1

```bash
# After T022 (migration) lands, run in parallel:
Task: "T023 Domain entities in apps/api/src/atlas_api/modules/auth/domain/models.py"
Task: "T024 Repositories in apps/api/src/atlas_api/modules/auth/repository/"
Task: "T031 Web register/login/verify pages in apps/web/src/features/auth/"
# Tests T019–T021 were already written (and failing) before implementation began
```

---

## Implementation Strategy

- **MVP first**: Phases 1–3 only → deployable secure sign-in (US1) → validate → demo.
- **Incremental**: each story phase ends at a checkpoint that is independently testable and
  deployable behind the auth feature flags (per-method flags from plan §24).
- **Traceability**: T019–T032→US1/SC-001/002; T033–T043→US2/SC-003/006; T044–T053→US3/
  SC-005; T054–T061→US4/SC-010; T062–T071→US5/SC-004/007/009; T074→SC-002; T064→SC-007
  privacy contract.
- Commit after each task or logical group; stop at any checkpoint to validate.

## Summary

- **Total**: 79 tasks | Setup 6 | Foundational 12 | US1 14 | US2 11 | US3 10 | US4 8 | US5 10 | Polish 8
- **Parallel opportunities**: 31 tasks marked [P]; US1 ∥ US3 after Phase 2 for two-developer flow
- **MVP scope**: Phases 1–3 (T001–T032)
