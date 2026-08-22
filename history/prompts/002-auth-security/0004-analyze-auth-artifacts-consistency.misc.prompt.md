---
id: 0004
title: Analyze auth artifacts consistency
stage: misc
date: 2026-08-04
surface: agent
model: claude-fable-5
feature: 002-auth-security
branch: 002-auth-security
user: user
command: /sp.analyze
labels: ["analysis", "consistency", "coverage", "read-only"]
links:
  spec: specs/01-auth-security/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - none (read-only analysis; report emitted to conversation)
tests:
 - none (static cross-artifact analysis)
---

## Prompt

/sp.analyze (no user input) — non-destructive cross-artifact consistency and quality
analysis across spec.md, plan.md, and tasks.md for the current feature after /sp.tasks;
constitution treated as non-negotiable authority; produce findings table, coverage summary,
metrics, next actions; offer (not apply) remediation.

## Response snapshot

Analyzed specs/01-auth-security/{spec,plan,tasks}.md + data-model + contracts against
constitution v1.0.0. **No CRITICAL constitution violations.** 12 findings: 2 HIGH —
(C1) FR-010 profile management has zero implementation tasks (migration creates
user_profile but no service/router/UI task covers /users/me, preferences, consents
endpoints that exist in the OpenAPI contract), and (I1) branch `002-auth-security` vs
specs dir `01-auth-security` divergence breaks all four SpecKit scripts and will block
/sp.implement (fix exists as T077 but is sequenced in Polish — too late). Mediums:
retention/purge janitor jobs designed in data-model but untasked; audit hash-chain
checkpoint (plan §15) untasked; consent re-prompt on version bump untasked; US2's story
independence relies on US1 migration T022 (documented but fragile); role-set drift
(plan/data-model add org_admin missing from spec FR-016); platform API keys (T068) have no
backing FR. Lows: FR-011/FR-012 near-duplicate encryption clauses; "suspicious IPs"
unmeasured; security_alert vs security_event naming drift; spec FR-020 mentions webhook
endpoints that don't exist this spec. Coverage: 23/24 FRs (96%) have ≥1 task; 79 tasks;
all 10 SCs traceable except SC-001's 3-minute timing (no explicit assertion). Recommended:
resolve both HIGH items (add profile tasks; do T077 immediately before implement), then
proceed.

## Outcome

- ✅ Impact: Pre-implementation defect list; two HIGH blockers surfaced before /sp.implement could hit them.
- 🧪 Tests: n/a (static analysis).
- 📁 Files: none modified (read-only command).
- 🔁 Next prompts: Apply remediation edits on approval; then /sp.implement; /sp.adr still pending consent.
- 🧠 Reflection: The only true coverage hole (FR-010) came from the contract having endpoints the task generator's router tasks didn't enumerate — future /sp.tasks runs should diff contract operationIds against task router lists.

## Evaluation notes (flywheel)

- Failure modes observed: check-prerequisites.sh still blocked by naming divergence (4th occurrence) — elevated from Polish task to pre-implement action in report.
- Graders run and results (PASS/FAIL): Constitution alignment PASS (0 violations); coverage 96%; determinism — stable finding IDs by category.
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): Add contract-operationId↔task cross-check step to the /sp.tasks workflow.
