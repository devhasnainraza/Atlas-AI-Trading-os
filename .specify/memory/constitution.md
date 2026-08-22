<!--
Sync Impact Report
==================
Version change: (template, unversioned) → 1.0.0
Rationale: Initial ratification — template placeholders replaced with the 12
project principles supplied by the architext, plus Mission, Development
Workflow, and Governance sections.

Modified principles: n/a (initial adoption; all 12 principles newly defined)
Added sections:
- Mission
- Core Principles (I–XII)
- Development Workflow & Quality Gates
- Governance
Removed sections:
- All template placeholder comments and example slots

Templates status:
- ✅ .specify/templates/plan-template.md — "Constitution Check" gate is generic
  ("Gates determined based on constitution file") and now resolves against the
  12 principles below; no file edit required.
- ✅ .specify/templates/spec-template.md — no constitution references; aligned.
- ✅ .specify/templates/tasks-template.md — no constitution references; task
  categories (tests, observability, security) remain compatible.
- ⚠ .specify/templates/commands/*.md — directory does not exist in this repo;
  nothing to update.

Deferred TODOs: none.
-->

# Atlas AI Trading OS Constitution

## Mission

Build the world's most trustworthy AI-powered Trading Operating System that assists traders
through transparent research, continuous monitoring, intelligent automation, and
human-centered decision making.

## Core Principles

### I. Human First

The AI assists users but does not replace human judgment by default. Trade execution and
other consequential actions MUST require explicit human confirmation unless the user has
deliberately opted into a clearly scoped automation. The system MUST always allow the user
to override or halt automated behavior.

Rationale: Trust is the product. Users remain accountable for their capital, so the system
must keep them in command.

### II. Security First

All sensitive information MUST be encrypted in transit and at rest. Broker credentials
MUST never be exposed to the client; they are held and used exclusively by trusted
server-side components. Secrets MUST never be hardcoded in source or logs — configuration
comes from environment/secret stores.

Rationale: A trading platform is a high-value attack target; a single credential leak is
catastrophic and unrecoverable trust damage.

### III. Transparency

Every recommendation MUST include: confidence, evidence, risks, and alternative scenarios.
A recommendation missing any of these four elements is incomplete and MUST NOT be
presented to the user as actionable.

Rationale: Traders can only calibrate reliance on the system when they can see how sure it
is, why, and what could go wrong.

### IV. Multi-Agent Collaboration

Specialized agents collaborate through a Manager Agent. No single agent has absolute
authority: cross-cutting decisions MUST flow through the Manager Agent, and agent outputs
are advisory inputs to that coordination — never unilateral commands to other agents.

Rationale: Separation of duties limits blast radius of any one agent's error and keeps
responsibilities auditable.

### V. Explainability

Every recommendation MUST be explainable: the system MUST be able to produce a
human-readable account of the inputs, reasoning steps, and tools that led to it. Features
that cannot produce such an account MUST NOT ship.

Rationale: "Trust me" is not an acceptable answer in financial decision support.

### VI. Risk Before Profit

Risk management always overrides profit opportunities. When a risk rule (position limits,
exposure caps, drawdown guards) conflicts with a profit signal, the risk rule wins —
without exception and without runtime override by any agent.

Rationale: Survival of capital precedes growth of capital; asymmetric downside makes this
ordering non-negotiable.

### VII. Continuous Learning

The platform continuously improves using journals, historical analysis, and user feedback,
while respecting user privacy. Learning pipelines MUST honor Principle VIII constraints
and MUST NOT train on or share data a user has excluded or deleted.

Rationale: Compounding insight from real usage is the moat, but only if it never comes at
the cost of user trust.

### VIII. Privacy by Design

User data belongs to the user. The system MUST minimize data collection to what a feature
demonstrably needs, MUST give users visibility and control over their stored information,
and MUST support deletion of user data on request.

Rationale: Financial behavior data is among the most sensitive personal data; stewardship
of it is a precondition for the mission.

### IX. Reliability (Fail Safe)

Critical failures MUST fail safely. If required data is unavailable or confidence is too
low, the system MUST recommend waiting rather than forcing a trade. Degraded modes MUST
be explicit to the user — the system never silently pretends to full capability.

Rationale: In trading, a wrong action is usually worse than no action; inaction is the
safe default state.

### X. Modular Architecture

Every capability is implemented as an independent agent or service with clear
responsibilities. Modules MUST communicate through defined contracts, MUST be
independently testable, and MUST NOT reach into another module's internals.

Rationale: Clear seams keep the system evolvable, testable, and safe to change one piece
at a time.

### XI. Observability

Every important AI decision, tool call, and execution path MUST be logged for debugging
and auditing. Logs MUST be structured, correlate an end-to-end request across agents, and
MUST NOT contain secrets or raw broker credentials (per Principle II).

Rationale: Explainability (V) and incident response are impossible without a faithful
record of what the system actually did.

### XII. Scalability

The platform MUST support thousands of concurrent users through distributed agent
execution. Designs MUST avoid single-instance bottlenecks and stateful coupling that
prevents horizontal scaling; capacity assumptions MUST be stated in each feature plan.

Rationale: Trust also means being up and responsive when markets move and everyone logs
in at once.

## Development Workflow & Quality Gates

- All work follows Spec-Driven Development: specification → plan → tasks → implementation,
  with artifacts under `specs/<feature>/`.
- Every plan MUST pass the Constitution Check gate against the principles above before
  Phase 0 research, and again after design; violations require an entry in Complexity
  Tracking with justification.
- Changes MUST be the smallest viable diff, covered by tests, and reference code
  precisely; test-first is the default for new behavior.
- Prompt History Records are created for every user prompt under `history/prompts/`;
  architecturally significant decisions are proposed as ADRs under `history/adr/` and
  require user consent before creation.

## Governance

This constitution supersedes all other development practices in this repository. All PRs
and reviews MUST verify compliance with the Core Principles; a change that conflicts with
a principle is rejected or the conflict is documented and resolved through amendment.

Amendment procedure: propose the change with rationale, review it with the architext, and
record significant reversals or additions as an ADR. Amendments take effect when merged to
the default branch with an updated version line.

Versioning policy (semantic): MAJOR for backward-incompatible removals or redefinitions of
principles or governance; MINOR for new principles/sections or materially expanded
guidance; PATCH for clarifications and wording fixes.

Compliance review: the Constitution Check in every feature plan is the recurring
enforcement point; deviations discovered later are logged as issues and either remediated
or ratified via amendment.

**Version**: 1.0.0 | **Ratified**: 2026-08-03 | **Last Amended**: 2026-08-03
