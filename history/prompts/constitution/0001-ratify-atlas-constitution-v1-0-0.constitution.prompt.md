---
id: 0001
title: Ratify Atlas constitution v1.0.0
stage: constitution
date: 2026-08-03
surface: agent
model: claude-fable-5
feature: none
branch: master
user: user
command: /sp.constitution
labels: ["constitution", "governance", "principles"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - .specify/memory/constitution.md
tests:
 - none (documentation-only change)
---

## Prompt

# Atlas AI Trading OS Constitution

## Mission

Build the world's most trustworthy AI-powered Trading Operating System that assists traders through transparent research, continuous monitoring, intelligent automation, and human-centered decision making.

## Core Principles

### 1. Human First

The AI assists users but does not replace human judgment by default.

### 2. Security First

All sensitive information must be encrypted in transit and at rest.

Broker credentials must never be exposed to the client.

### 3. Transparency

Every recommendation must include:

- Confidence
- Evidence
- Risks
- Alternative scenarios

### 4. Multi-Agent Collaboration

Specialized agents collaborate through a Manager Agent.

No single agent has absolute authority.

### 5. Explainability

Every recommendation must be explainable.

### 6. Risk Before Profit

Risk management always overrides profit opportunities.

### 7. Continuous Learning

The platform continuously improves using journals, historical analysis, and user feedback while respecting user privacy.

### 8. Privacy by Design

User data belongs to the user.

The system minimizes data collection and gives users control over their stored information.

### 9. Reliability

Critical failures must fail safely.

If required data is unavailable or confidence is too low, the system should recommend waiting rather than forcing a trade.

### 10. Modular Architecture

Every capability is implemented as an independent agent or service with clear responsibilities.

### 11. Observability

Every important AI decision, tool call, and execution path should be logged for debugging and auditing.

### 12. Scalability

The platform must support thousands of concurrent users through distributed agent execution.

## Response snapshot

Ratified the initial Atlas AI Trading OS Constitution v1.0.0 at
`.specify/memory/constitution.md`. All template placeholders were replaced with the
architext's 12 principles (Human First, Security First, Transparency, Multi-Agent
Collaboration, Explainability, Risk Before Profit, Continuous Learning, Privacy by
Design, Reliability/Fail Safe, Modular Architecture, Observability, Scalability), each
tightened into declarative MUST/MUST NOT rules with rationale. Added Mission,
Development Workflow & Quality Gates, and Governance sections (amendment procedure,
semantic versioning policy, compliance review via the plan-stage Constitution Check).
A Sync Impact Report was prepended as an HTML comment. Dependent templates were
audited: plan-template.md's Constitution Check gate is generic and needs no edit;
spec/tasks templates contain no constitution references; no commands/ template
directory exists. Ratified and last-amended dates set to 2026-08-03.

## Outcome

- ✅ Impact: Initial constitution ratified (v1.0.0); SDD quality gates now have a concrete rule set to enforce.
- 🧪 Tests: None — documentation/governance artifact only.
- 📁 Files: .specify/memory/constitution.md (overwritten from template)
- 🔁 Next prompts: /sp.specify for the first feature; /sp.adr if stack/architecture decisions are made.
- 🧠 Reflection: Earlier attempts passed empty @prompt.md/@input.md files; principles arrived inline on the third invocation — verify referenced files are saved before invoking.

## Evaluation notes (flywheel)

- Failure modes observed: Command args referenced empty files twice before content was supplied inline.
- Graders run and results (PASS/FAIL): Placeholder scan PASS; version/date coherence PASS; routing PASS.
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): Have create-phr.sh pre-fill ID/date/branch to reduce manual placeholder filling.
