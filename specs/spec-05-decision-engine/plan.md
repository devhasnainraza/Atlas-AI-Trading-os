# Implementation Plan: Decision Engine & Risk Management

**Branch**: `05-decision-engine` | **Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/spec-05-decision-engine/spec.md`

## Summary

Deliver Atlas's cognitive decision core: an adversarial dialectic decision pipeline orchestrating structured AI debate (Bull Advocate vs. Bear Advocate vs. Synthesis Arbitrator), non-bypassable pre-trade mathematical risk evaluation (Principle VI), calibrated Bayesian confidence scoring (0.00-100.00%), and explainable trade proposal formulation adhering to the constitutional 4-part output contract. Features unbypassable LangGraph interrupt nodes (`interrupt_before`) for human approval, cryptographic proposal integrity hashing, deterministic setup verification against active database state, and fail-safe "WAIT / NO_TRADE" recommendations when signals lack statistical edge.

## Technical Context

**Language/Version**: Python 3.12 (decision graph runtime & risk validation services in `apps/api`), TypeScript 5.x / Next.js 15 (adversarial debate visualizer & proposal cards in `apps/web`)  
**Primary Dependencies**: LangGraph 0.2+, Pydantic v2, FastAPI, SQLAlchemy 2 (async) + Alembic, scipy / numpy (Bayesian confidence calibration & VaR models), Redis 7 (ephemeral debate streams & distributed account risk locks), LiteLLM (multi-model adversarial pairing: Claude 3.5 Sonnet vs. GPT-4o)  
**Storage**: PostgreSQL 16 (decision proposals, risk rules, debate transcripts, validation audit logs), Redis 7 (active proposal TTL caches, risk margin tallies), Kafka (`atlas.decision.*` topics)  
**Testing**: pytest-asyncio, Hypothesis (property-based invariant testing on risk formulas & proposal state transitions), mock LLM debate harnesses, Schemathesis (API contracts), zero-hallucination verification tests  
**Target Platform**: Linux containerized microservices (stateless decision graph workers + low-latency risk engine instances)  
**Performance Goals**: Adversarial debate & synthesis < 6s p95; mathematical pre-trade risk evaluation < 5ms; Bayesian confidence calibration < 2ms; proposal state transitions < 10ms  
**Constraints**: Absolute ban on floating-point arithmetic (`Decimal` / `NUMERIC(28,10)` for all prices, sizes, and risk metrics); risk engine veto is programmatic and non-negotiable; proposals expire unconditionally after 10-minute TTL; human approval token required for execution  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Compliance in this plan | Status |
|---|-----------|------------------------|--------|
| I | Human First | LangGraph halts at `interrupt_before` node; every proposal requires explicit user click or active delegated mandate. | ✅ |
| II | Security First | SHA-256 integrity hash binds proposal fields; proposal payload cannot be tampered with between generation and order dispatch. | ✅ |
| III | Transparency | 4-part output contract enforced on all proposals: Confidence %, Evidence bullets, Risk & Invalidation levels, Alternative Scenarios. | ✅ |
| IV | Multi-Agent Collab | Bull, Bear, Arbitrator, and Risk agents engage in structured peer review with distinct analytical roles. | ✅ |
| V | Explainability | Full debate transcripts, counter-arguments, risk formulas, and weights saved to `decision_proposals.debate_transcript`. | ✅ |
| VI | Risk Before Profit | Pure Python pre-trade risk checks override high-confidence signals; daily loss, drawdown, and correlation limits are absolute. | ✅ |
| VII | Continuous Learning | Trader rejection rationales and trade post-mortems logged for Learning Agent analysis and weight calibration. | ✅ |
| VIII | Privacy by Design | Risk limits, active proposals, and account equity are strictly partitioned by `user_id`. | ✅ |
| IX | Reliability | If confidence < 65% or market data is stale, the engine defaults to "NO_TRADE / WAIT" (Fail-Safe default). | ✅ |
| X | Modular Architecture | Risk engine and dialectic debate are independent modules decoupled from venue-specific order execution. | ✅ |
| XI | Observability | Debate durations, agent consensus scores, risk rejection frequencies, and proposal conversion rates exported to Prometheus. | ✅ |
| XII | Scalability | Stateless debate workers scale horizontally; active proposals indexed with TTL cleanups prevent table bloat. | ✅ |

**Gate result**: PASS.

## 1. High-Level Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│ Candidate Market Signal (From Spec 03 Agent / Spec 04 Intelligence)    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Dialectic AI Debate Stage (Multi-Model Adversarial Arena)              │
│                                                                        │
│   ┌───────────────────────────┐     ┌───────────────────────────┐      │
│   │       Bull Advocate       │     │       Bear Advocate       │      │
│   │  (Breakouts, Momentum,    │<--->│  (Resistance, Liquidity   │      │
│   │   Inflows, Macro Tailwinds│     │   Traps, Macro Headwinds) │      │
│   └─────────────┬─────────────┘     └─────────────┬─────────────┘      │
│                 │                                 │                    │
│                 └────────────────┬────────────────┘                    │
│                                  ▼                                     │
│   ┌─────────────────────────────────────────────────────────────┐      │
│   │                    Synthesis Arbitrator                     │      │
│   │     (Fallacy Detection, Thesis Balance, Consensus Weight)   │      │
│   └──────────────────────────────┬──────────────────────────────┘      │
└──────────────────────────────────┼─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Pre-Trade Risk Engine (Deterministic Pure-Python Gate)                 │
│  - Account Max Risk / Position Size Calculator (Decimal)               │
│  - Daily Loss Circuit Breaker Check                                    │
│  - Cross-Asset Correlation & Portfolio Heat Check                      │
│  - High-Impact Macro Release Proximity Check                           │
├──────────────────────────────────┬─────────────────────────────────────┤
│ Pass Risk Checks?                │ Violates Risk Rules?                │
│                                  ▼                                     │
│                                  ┌───────────────────────────────┐     │
│                                  │ Hard Programmatic Veto Issued │     │
│                                  │ (Logs Reason & Halts Graph)   │     │
│                                  └───────────────────────────────┘     │
│                                                                        │
│ Approved by Risk                                                       │
▼                                                                        │
┌────────────────────────────────────────────────────────────────────────┐
│ Bayesian Confidence Calibration Node                                   │
│  - Confluence (30%) + Consensus (25%) + Debate (20%) + Regime (15%)    │
│  - If Confidence < 65.00% -> Output "NO_TRADE / WAIT"                  │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ Confidence >= 65.00%
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Proposal Formulation & Cryptographic Hashing                           │
│  - Generates SHA-256 hash of (Symbol, Side, Entry, SL, TP, Risk USD)  │
│  - Stores in `decision_proposals` with 10-minute TTL                   │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Human Approval Gate (`interrupt_before: execute_proposal`)             │
│  - Renders Interactive Proposal Card in Web Cockpit & Telegram Bot     │
│  - Trader clicks "Confirm Execution" or "Pass"                         │
└────────────────────────────────────────────────────────────────────────┘
```

## 2. Directory Structure

```text
specs/spec-05-decision-engine/
├── spec.md              # Specification document
├── plan.md              # This architecture plan
├── data-model.md        # Data models (proposals, risk rules, debates)
└── tasks.md             # Test-first task breakdown
```

## 3. Core Technical Decisions & Rationale

### ADR-05-01: Multi-Model Adversarial Debate Arena
- **Context**: Relying on a single LLM to generate both trading thesis and risk critiques causes confirmation bias and sycophantic self-validation.
- **Decision**: Assign distinct models and prompt identities: Bull Advocate (Claude 3.5 Sonnet), Bear Advocate (GPT-4o), and Synthesis Arbitrator (Claude 3.5 Sonnet / DeepSeek R1).
- **Consequences**: Rigorous stress-testing of assumptions; exposes structural blindspots before capital deployment.

### ADR-05-02: Cryptographic Proposal Hash Binding
- **Context**: In asynchronous trading architectures, race conditions or UI tampering could alter trade parameters between user review and venue execution.
- **Decision**: Compute `proposal_hash = SHA256(user_id + symbol + side + entry_min + entry_max + stop_loss + risk_usd + timestamp)` at formulation. The execution gateway re-verifies this hash against the signed user payload.
- **Consequences**: Zero risk of parameter mutation; creates an indisputable audit trail for every executed trade.

### ADR-05-03: Deterministic Price Verification Guard
- **Context**: LLM agents occasionally cite hallucinated price levels or historical resistance zones that are mathematically inaccurate.
- **Decision**: Before a proposal leaves the synthesizer, every cited support/resistance price is verified against active L1/L2 order book and daily pivot calculations. Hallucinated levels trigger automatic correction or rejection.
- **Consequences**: Guarantees stop-losses and take-profit targets reflect mathematical market reality.
