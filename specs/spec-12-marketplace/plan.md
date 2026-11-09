# Implementation Plan: AI Marketplace

**Branch**: `12-marketplace` | **Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/spec-12-marketplace/spec.md`

## Summary

Deliver Atlas's decentralized AI Trading Marketplace ("The App Store for Trading Agents"): an ecosystem enabling developers, quants, and traders to publish, monetize, discover, and install custom Trading Agents, LangGraph Strategy Graphs, Technical Indicators, Prompt Packs, Custom Workflows, and Dashboard Widgets. Features automated AST security verification and gVisor sandbox testing, verifiable backtest performance curves, 1-click installation with sandboxed subgraph execution, strict pre-trade risk gate overrides, and a creator monetization engine powered by Stripe Connect (70/30 revenue split).

## Technical Context

**Language/Version**: Python 3.12 (marketplace catalog, verification pipeline, sandboxed execution runtime in `apps/api`), TypeScript 5.x / Next.js 15 (marketplace discovery portal, creator studio, review widgets in `apps/web`)  
**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2 (async) + Alembic, stripe (Stripe Connect custom onboarding & split transfers), gVisor (runsc) / WebAssembly (Wasmtime) for sandboxed plugin runtime, ast / bandit (static code security linter), algoliasearch / pgvector (hybrid catalog search)  
**Storage**: PostgreSQL 16 + pgvector (marketplace plugins, versions, installations, creator accounts, reviews), MinIO / S3 (signed plugin code bundles, backtest reports, preview graphics), Redis 7 (search index cache, download rate limiters)  
**Testing**: pytest-asyncio, sandbox escape penetration suite, mock Stripe Connect webhooks, backtest replication tests (verifying claimed Sharpe against paper engine replay), Schemathesis (marketplace API contracts)  
**Target Platform**: Dedicated Kubernetes sandboxed node pool running gVisor `runsc` runtime for third-party plugin isolation  
**Performance Goals**: Sandboxed execution overhead < 10ms per inference invocation; 1-click installation & provisioning < 2s; marketplace search query response < 30ms p95; 100% exact Decimal accounting on royalties  
**Constraints**: Zero access to host filesystem, environment variables, or network sockets for untrusted code; third-party agents strictly cannot bypass host Pre-Trade Risk Gate; all financial transactions require strict `Decimal` accounting  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Compliance in this plan | Status |
|---|-----------|------------------------|--------|
| I | Human First | Marketplace agents cannot execute live orders without passing the host human approval gate or explicit user mandate. | ✅ |
| II | Security First | gVisor / WASM sandboxing, AST static security scanners, ECDSA bundle signing, and zero raw credential access. | ✅ |
| III | Transparency | Every listing displays verified backtest drawdown curves, independent audit scores, and user reviews. | ✅ |
| IV | Multi-Agent Collab | Third-party strategy graphs integrate seamlessly as sandboxed subgraphs into host Manager Agent orchestration. | ✅ |
| V | Explainability | Installed agents must conform to the 4-part output contract (Confidence %, Evidence, Risks, Alternative Scenarios). | ✅ |
| VI | Risk Before Profit | Host platform Pre-Trade Risk Gate strictly overrides any marketplace agent trade proposals; cannot be disabled. | ✅ |
| VII | Continuous Learning | Creator performance rankings update dynamically based on live forward-testing win rates and subscriber feedback. | ✅ |
| VIII | Privacy by Design | Creator plugins execute without access to user account balances, personal memories, or identities. | ✅ |
| IX | Reliability | If a marketplace agent crashes or exceeds resource quotas, the host supervisor isolates the failure without impacting core trading. | ✅ |
| X | Modular Architecture | Clean plugin manifest specification (`AtlasPluginManifest`) establishes standard plug-and-play extension contracts. | ✅ |
| XI | Observability | Plugin execution latencies, exception frequencies, and token consumptions tracked per installation. | ✅ |
| XII | Scalability | Asynchronous package verification workers; static marketplace metadata cached globally on edge CDNs. | ✅ |

**Gate result**: PASS.

## 1. High-Level Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│ Creator Studio (Publish Package, Set Pricing, Connect Stripe)          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Upload Manifest & Code Bundle (.zip)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Automated Marketplace Verification Pipeline                            │
│  - Static AST Linter (Blocks sockets, eval, subprocess, os modules)   │
│  - gVisor / WASM Sandboxed Execution & Memory Benchmark               │
│  - Historical Backtest Verification against 3-Year Tick Data           │
├───────────────────────────────────┬────────────────────────────────────┤
│ Fails Verification?               │ Passes Verification?               │
│ -> Return Rejection Audit Report  │ -> Sign Package with Platform Key  │
└───────────────────────────────────┼────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Marketplace Storefront (Next.js Discovery Portal & pgvector Search)    │
│  - Verified Listings (Sharpe, Drawdown, Ratings, Pricing)              │
│  - 1-Click Install Button -> Provisions `marketplace_installations`    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Host Runtime Execution (User's Personal Atlas Instance)                │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ Manager Agent: Resolves Installed Plugin Subgraph              │   │
│   └───────────────────────────────┬────────────────────────────────┘   │
│                                   │                                    │
│                                   ▼                                    │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ Sandboxed Plugin Execution Pod (gVisor runsc)                  │   │
│   │  - Restricted CPU/Memory · No raw credentials · Mock inputs    │   │
│   └───────────────────────────────┬────────────────────────────────┘   │
│                                   │ Trade Proposal Formulated          │
│                                   ▼                                    │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ Host Pre-Trade Risk Gate & Human Interrupt (Non-Bypassable)    │   │
│   └────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

## 2. Directory Structure

```text
specs/spec-12-marketplace/
├── spec.md              # Specification document
├── plan.md              # This architecture plan
├── data-model.md        # Data models (plugins, installations, payouts)
└── tasks.md             # Test-first task breakdown
```

## 3. Core Technical Decisions & Rationale

### ADR-12-01: gVisor / WASM Sandboxed Execution Environment
- **Context**: Running untrusted third-party Python code inside the trading platform introduces severe security risks (arbitrary code execution, credential exfiltration, resource exhaustion).
- **Decision**: Execute all third-party marketplace plugins inside lightweight gVisor (`runsc`) isolated containers or WebAssembly sandboxes with strict CPU, RAM, and network virtualization.
- **Consequences**: Complete containment of malicious or buggy plugins; zero access to the host kernel or network stack.

### ADR-12-02: Non-Bypassable Host Pre-Trade Risk Enforcement
- **Context**: An aggressive or poorly tested marketplace agent could submit extreme position sizes or ignore portfolio drawdown rules.
- **Decision**: Marketplace plugins only output standardized trade proposals; they possess zero direct execution capability. Every proposal must pass the host platform's native Pre-Trade Risk Gate and Human Approval Gate.
- **Consequences**: Users can safely test third-party algorithms with total certainty that their capital limits will be respected.

### ADR-12-03: Verifiable Backtest Provenance Engine
- **Context**: Online trading marketplaces are rife with fraudulent backtests, overfitted curves, and false marketing claims.
- **Decision**: The marketplace verification pipeline independently runs the plugin code against raw historical tick data in the paper execution engine, generating the published equity curve and Sharpe ratio automatically.
- **Consequences**: Eliminates fabricated marketing; buyers inspect mathematical, reproducible performance data.
