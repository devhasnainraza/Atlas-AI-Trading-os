---
id: 0003
title: Generate auth security tasks
stage: tasks
date: 2026-08-04
surface: agent
model: claude-fable-5
feature: 002-auth-security
branch: 002-auth-security
user: user
command: /sp.tasks
labels: ["tasks", "authentication", "security", "vault", "rbac", "mfa", "privacy"]
links:
  spec: specs/01-auth-security/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - specs/01-auth-security/tasks.md
tests:
 - none run (task-generation artifact; test tasks embedded per story, write-first)
---

## Prompt

/sp.tasks (no user input)

Command outline executed: run check-prerequisites.sh and parse FEATURE_DIR + available
docs; load plan.md and spec.md (required) plus data-model.md, contracts/, research.md,
quickstart.md; generate a dependency-ordered tasks.md using .specify/templates/
tasks-template.md with strict checklist format `- [ ] T00X [P?] [USn?] Description with
file path`; organize phases as Setup → Foundational (blocking) → one phase per user story
in priority order (P1..P5) → Polish; include per-story goal, independent test criteria,
checkpoints, dependency graph, parallel execution examples, implementation strategy (MVP
first); report totals, per-story counts, parallel opportunities, MVP scope, and format
validation; then create a PHR.

## Response snapshot

Generated `specs/01-auth-security/tasks.md` with **79 tasks** mapped to the five spec user
stories. check-prerequisites.sh failed on the known branch(002-auth-security) vs specs-dir
(01-auth-security) naming mismatch, so docs were loaded directly from
specs/01-auth-security/ (all present: plan, spec, research, data-model, contracts,
quickstart). Structure: Phase 1 Setup (6 — module scaffolds, deps, settings, Mailpit/GeoIP,
bootstrap keys); Phase 2 Foundational (12 — Alembic branches, TokenService+JWKS, Argon2id
hasher, vault EnvelopeCrypto with KekProvider, one-time-token machinery, AuthMiddleware
replacing DevIdentityProvider, CSRF middleware, error codes, rate-limit classes, event
schemas, auth-email worker, audit taxonomy); Phase 3 US1 Secure Account Creation & Sign-In
(14, MVP — tests-first contract/integration/OAuth, identity-core migration, domain/repos,
Registration/Session/OAuth/MagicLink services, routers, events, web pages, E2E); Phase 4
US2 Protect & Recover (11 — password policy w/ zxcvbn+HIBP, reset/change, MFA TOTP +
recovery codes + step-up, lockout/backoff, sessions/devices UI, abuse suite); Phase 5 US3
Credentials Vault & Connected Accounts (10 — vault migration, lifecycle services,
use_credential public API, health probes, no-secret-in-schema contract test, E2E); Phase 6
US4 RBAC (8 — rbac migration, seeds, PermissionResolver w/ roles_ver, route permission
declarations + CI check, admin endpoints, matrix test); Phase 7 US5 Security Center &
Privacy (10 — security_event/privacy_request/api_key migration, SecurityAnalyzer worker
(impossible travel/new device/token reuse), score service, API keys, export/deletion jobs
with erasure-coverage contract test, web pages, E2E); Phase 8 Polish (8 — dashboards/
alerts, runbooks, k6 SC-002 scenario, ZAP nightly, Terraform KMS/GeoIP/ESO, SpecKit
script-dir mismatch fix, quickstart validation, /security-review + pentest scope).
31 tasks marked [P]; dependency graph documented (US1 ∥ US3 possible after Phase 2);
MVP = T001–T032. Format validated: every task has checkbox, sequential ID, [P] where
parallelizable, [USn] labels only in story phases, and an explicit file path.

## Outcome

- ✅ Impact: Auth feature is decomposed and immediately executable via /sp.implement; MVP boundary and traceability to SC-001..010 explicit.
- 🧪 Tests: Test tasks embedded per story (write-first, must fail before implementation); none executed at this stage.
- 📁 Files: specs/01-auth-security/tasks.md
- 🔁 Next prompts: /sp.analyze for cross-artifact consistency; /sp.implement to execute; /sp.adr custom-iam-and-credential-vault still pending user consent.
- 🧠 Reflection: T059 (route permission declarations) intentionally scheduled late because it touches routers created across US1–US3 — called out in dependencies to avoid merge-conflict surprises.

## Evaluation notes (flywheel)

- Failure modes observed: check-prerequisites.sh blocked by branch/specs-dir naming divergence (third script affected) — remediation captured as task T077 rather than left as tribal knowledge.
- Graders run and results (PASS/FAIL): Checklist-format validation PASS (79/79); story coverage PASS (5/5 stories, every FR mapped to ≥1 task); phase-structure PASS.
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): Run /sp.analyze before /sp.implement to catch spec↔plan↔tasks drift introduced by the repo reorg.
