---
id: 0001
title: Document execution safety architecture decision
stage: plan
date: 2026-08-29
surface: agent
model: claude-opus-5
feature: 003-trading-integration
branch: 003-trading-integration
user: user
command: /sp.adr trading-execution-safety-architecture
labels: ["adr", "trading", "execution", "risk-gate", "idempotency", "safety"]
links:
  spec: specs/003-trading-integration/spec.md
  ticket: null
  adr: history/adr/0001-trading-execution-safety-architecture.md
  pr: null
files:
 - history/adr/0001-trading-execution-safety-architecture.md (created)
 - history/prompts/003-trading-integration/0001-document-execution-safety-architecture-decision.plan.prompt.md (this record)
tests:
 - none run for the ADR itself (documentation artifact)
 - standing evidence for its claims: tests/contract/trading/test_api_surface_guards.py, shared/tests/venues/test_no_risk_bypass.py, shared/tests/venues/test_no_credential_exposure.py, tests/contract/trading/test_shipped_flags_are_safe.py
---

## Prompt

# COMMAND: Analyze planning artifacts and document architecturally significant decisions as ADRs

**User's additional input:** `trading-execution-safety-architecture`

Act as a senior software architect. Execute a 6-step workflow: (1) load planning context via
`check-prerequisites.sh --json`, aborting if plan.md is missing; (2) extract architecturally
significant decisions from plan.md as **decision clusters**, not atomic choices — group
technologies that work together and would change together, separate only what could diverge
independently; (3) scan `history/adr/` for existing coverage or conflicts; (4) apply the
significance test — does it impact how engineers write/structure software, are there notable
tradeoffs or alternatives, will it be questioned or revisited later — proceeding only if ALL
three pass; (5) create qualifying ADRs via `create-adr.sh "<title>"` and fill every
`{{PLACEHOLDER}}`; (6) report completion in the prescribed format.

At Steps 2 and 4, apply lightweight Analyze→Measure checks. Analyze for two named failure modes:
**over-granular ADRs** (documenting trivial, low-impact, or single-file decisions such as naming
conventions) and **missing alternatives** (no alternative approach listed). Measure with a
checklist grader that PASSes only if all hold: the ADR documents a decision that clusters related
changes or impacts multiple components; it explicitly lists at least one alternative with
rationale; it includes clear pros and cons for the chosen approach and alternatives; it is concise
but sufficiently detailed for future reference.

Error handling: if plan.md is missing, display an error and exit without creating ADRs; if
`create-adr.sh` fails, display the exact error, skip that ADR, continue with others, and report
partial completion. Tone: thorough, analytical, decision-focused — emphasize the "why" behind each
decision and its long-term implications.

As the main request completes, create and complete a PHR: determine the stage, generate a 3–7 word
title, route by stage (`plan` → `history/prompts/<feature-name>/`), run
`create-phr.sh --title <title> --stage <stage> --feature <name> --json`, fill all placeholders
including verbatim prompt text and a concise response, and validate that no placeholders remain.
If the script fails, fall back to writing the file agent-natively. Warn but do not block on
failure.

## Response snapshot

Ran the 6-step workflow. `check-prerequisites.sh` resolved FEATURE_DIR to
`specs/003-trading-integration` with research/data-model/contracts/quickstart available; plan.md
present (31 KB), so no abort. `history/adr/` did not exist — **zero existing ADRs, therefore zero
conflicts and zero references**.

**Step 2 — clusters extracted from plan.md** (5 candidates, deliberately clustered):

1. *Trading Execution Safety* — two-phase intent→confirm, at-most-once via pre-call submission
   ledger, `unresolved`-never-retry, structurally unbypassable risk gate (§6, §7, §8, §12,
   Complexity 2–3, Risks 1–2).
2. *Venue Abstraction Layer* — single `VenueAdapter` protocol, capability matrix, `classify_error`
   in-protocol, shared conformance suite, paper-as-adapter, symbol normalization, two sidecars
   (§2, §5, §9, Complexity 1).
3. *Venue-Authoritative State & Reconciliation* — venue is truth, local is a correctable
   projection, multi-trigger reconciliation, routing hold (§3, §11, Complexity 3, Risk 6).
4. *Market Data Freshness Contract* — Redis TTL-as-staleness (key absence **is** staleness),
   per-asset-class limits, refuse-rather-than-approximate, lease-based stream ownership (§4).
5. *Deferred Persistence via Repository Ports* — from implementation, not plan; in-memory ports
   holding the `intent_id` uniqueness invariant until Alembic exists.

Rejected as over-granular and folded into their clusters rather than given their own ADRs: the
Decimal-only float ban (part of the adapter boundary contract), individual venue choices, and the
per-venue feature-flag naming.

**Step 4 — significance test:** all five PASS all three criteria. **Step 5 —** created only
cluster 1, the decision the user named, per the project rule that ADRs are never auto-created
without consent; the other four are reported as candidates awaiting a decision.

**ADR-0001** documents four mechanisms as one cluster on the grounds that each closes a hole the
others leave open. Notable content beyond the mechanics: the enforcement of "unbypassable" is
structural (the submit function takes a `RiskVerdict` value object it cannot construct itself), the
two apparent exceptions are named explicitly as *rules inside the gate* rather than bypasses
(risk-reducing closes; mandates skipping per-order confirmation only), and an **Implementation
status** section records that the intent/confirm endpoints, submission ledger, and reconciliation
are not yet shipped — with the explicit caveat that *the at-most-once guarantee is only as durable
as its store*, so the mechanism is incomplete until the Postgres constraint exists. Six
alternatives were documented with rejection rationale, including alternative C (retry-with-dedup)
identified as "the design that produces the incident" and alternative F (local-as-truth) noted as
belonging to a separate cluster rather than folded in.

## Outcome

- ✅ Impact: First ADR in the repository; the four load-bearing safety invariants of the order path
  now have a permanent, reviewable rationale ahead of Phase 4 implementation, including honest
  scope about what is built versus decided.
- 🧪 Tests: None run for the ADR (documentation). Four existing guard suites cited as standing
  evidence for its central claims; T072/T073 will supply the at-most-once and ambiguity evidence
  when the order path lands.
- 📁 Files: `history/adr/0001-trading-execution-safety-architecture.md`; this PHR.
- 🔁 Next prompts: `/sp.adr` for the four remaining candidate clusters if the user consents;
  then Phase 2 remainder (T013–T018 as in-memory repository ports) and Phase 3 (US1 connections).
- 🧠 Reflection: The ADR's most valuable section turned out to be the one the template does not ask
  for — implementation status. Without it, a future reader would take "submission ledger committed
  before the adapter call" as a description of running code, when the durable constraint that makes
  the guarantee real does not exist yet. Worth adding to the template.

## Evaluation notes (flywheel)

- Failure modes observed: `create-phr.sh` aborts with "PHR template not found at .specify/templates/
  or templates/" — `phr-template.prompt.md` is absent from the repo, so the documented fallback path
  is now the only path. This also explains why Specs 00–03's own spec/plan/tasks runs left PHRs for
  001 and 002 but none for 003: the script has been broken since at least that point. Wrote this
  record agent-natively, matching the format of
  `history/prompts/002-auth-security/0002-plan-auth-security-blueprint.plan.prompt.md`.
- Graders run and results (PASS/FAIL): **PASS on all four checklist items.** Clustered (four
  mechanisms across trading module, adapter protocol, API surface, and contract tests — not a
  single-file change) ✅; alternatives with rationale (six, each with a rejection reason) ✅; pros
  and cons for chosen approach and alternatives (6 positive, 6 negative consequences, all stated
  as tradeoffs rather than wins) ✅; concise but sufficient ✅. Over-granularity check: 5 candidate
  clusters extracted from ~20 plan sections, 3 sub-decisions explicitly folded in rather than split
  out. Missing-alternatives check: none. Placeholder validation: zero `{{` remaining; all 10
  referenced paths verified to exist.
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): add `.specify/templates/phr-template.prompt.md` (derive
  it from the 002 PHRs, which are self-consistent) and add an **Implementation status** section to
  `adr-template.md` so ADRs written mid-implementation cannot be misread as descriptions of shipped
  behaviour.
