# Implementation Plan: AI Agent Core Platform

**Branch**: `03-agent-platform` | **Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/spec-03-agent-platform/spec.md`

## Summary

Deliver Atlas's multi-agent cognitive architecture: an enterprise-grade LangGraph orchestration framework coordinating 13 specialized AI agents into a collaborative, decentralized intelligence network. The platform features deterministic, cyclic state machines, PostgreSQL-backed checkpointers for long-lived resumable execution threads, strict tool registry permission sandboxing, multi-model fallback routing, real-time SSE streaming to the frontend cognitive cockpit, and non-bypassable human-in-the-loop interrupts (`interrupt_before`) for all consequential trading and risk decisions.

## Technical Context

**Language/Version**: Python 3.12 (agent graph runtime & worker services in `apps/api`), TypeScript 5.x / Next.js 15 (cognitive cockpit & SSE streaming in `apps/web`)  
**Primary Dependencies**: LangGraph 0.2+, LangChain-core, Pydantic v2, FastAPI, SQLAlchemy 2 (async) + Alembic, asyncpg, Redis 7 (agent pub/sub, tool locks, cache), Celery (background agent triggers), LiteLLM / direct SDKs (Anthropic Claude 3.5 Sonnet, OpenAI GPT-4o, DeepSeek-R1 / local vLLM)  
**Storage**: PostgreSQL 16 + pgvector (LangGraph thread checkpointers, agent execution traces, prompt versions, evaluation benchmarks), Redis 7 (ephemeral scratchpads, streaming tokens, active thread locks), Kafka (`atlas.agent.*` topics)  
**Testing**: pytest-asyncio, pytest-mock (deterministic LLM cassette mocking via vcrpy / mock providers), LangSmith / Langfuse evaluation harnesses, Schemathesis (SSE/REST API contracts), concurrency stress tests (100+ concurrent graph threads)  
**Target Platform**: Distributed Linux container pods (FastAPI SSE gateways + Celery worker pools with GPU/API gateway connectivity)  
**Performance Goals**: Non-LLM routing nodes < 20ms p95; checkpoint serialization & persistence < 15ms p95; multi-agent debate synthesis < 8s p95; streaming token time-to-first-byte < 800ms  
**Constraints**: Consequential actions (trades, strategy changes) unconditionally blocked at `interrupt_before` node; 100% of LLM prompts and completions captured in audit traces; zero execution without signed human approval token; strict tool execution privilege boundaries per agent  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Compliance in this plan | Status |
|---|-----------|------------------------|--------|
| I | Human First | LangGraph `interrupt_before` halts workflow prior to execution; explicit interactive approval modal requires cryptographic user confirmation. | ✅ |
| II | Security First | Agents execute tools through tightly bound, validated schemas; raw venue credentials never passed into agent context or model prompts. | ✅ |
| III | Transparency | 4-part output contract enforced: Confidence % (0-100), Supporting Evidence, Risk Assessment, Alternative Scenarios. | ✅ |
| IV | Multi-Agent Collab | 13 dedicated agents communicate through typed message envelopes (`AgentMessageEnvelope`) and shared state graph with explicit roles. | ✅ |
| V | Explainability | Full execution traces with inputs, intermediate tool outputs, prompt versions, and model completions persisted to `agent_execution_traces`. | ✅ |
| VI | Risk Before Profit | Risk Agent possesses hard programmatic veto over Manager Agent proposals; Python-level pre-checks override all LLM recommendations. | ✅ |
| VII | Continuous Learning | Journal & Learning Agents track execution outcomes, recurring errors, and user feedback, feeding episodic memory in pgvector. | ✅ |
| VIII | Privacy by Design | Multi-agent state and threads are strictly scoped to `user_id`; tenant isolation enforced across checkpoints and memory retrieval. | ✅ |
| IX | Reliability | Multi-tier LLM fallback routing (Anthropic -> OpenAI -> DeepSeek/local); persistent PostgreSQL checkpointers survive worker crashes and restarts. | ✅ |
| X | Modular Architecture | Agent nodes, tools, and registries are decoupled from venue execution adapters, communicating via standard event bus and interfaces. | ✅ |
| XI | Observability | OpenTelemetry spans wrap every agent node and tool call; token metrics, latencies, and costs exported to Prometheus and Langfuse. | ✅ |
| XII | Scalability | Stateless graph runners pull threads from Redis/Kafka queues; checkpointer uses indexed UUIDv7 threads with partition capability. | ✅ |

**Gate result**: PASS.

## 1. High-Level Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│ Client Cockpit (Next.js 15 App Router / SSE / WebSockets)              │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ POST /api/v1/agents/chat (SSE)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ apps/api: Agent Orchestrator Gateway (FastAPI)                         │
│  - Session Auth & User Scoping                                         │
│  - SSE Streaming Response Manager                                      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ LangGraph StateGraph Execution Engine                                  │
│  - PostgreSQL Checkpointer (`agent_checkpoints`)                       │
│  - Redis Active Run Lock (`run_id`)                                    │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                      Manager Agent Node                        │   │
│   │           (Intent Classification, Plan Decomposition)          │   │
│   └──────┬───────────────────────┬──────────────────────────┬──────┘   │
│          │                       │                          │          │
│          ▼                       ▼                          ▼          │
│   ┌───────────────┐       ┌───────────────┐          ┌───────────────┐ │
│   │ Market Team   │       │ Analysis Team │          │ Control Team  │ │
│   │  - Market     │       │  - Technical  │          │  - Risk (VETO)│ │
│   │  - News       │       │  - Portfolio  │          │  - Memory     │ │
│   │  - Social     │       │  - Journal    │          │  - Execution  │ │
│   │  - Economic   │       │  - Learning   │          │  - Notify     │ │
│   └──────┬────────┘       └──────┬────────┘          └──────┬────────┘ │
│          │                       │                          │          │
│          └───────────────────────┼──────────────────────────┘          │
│                                  ▼                                     │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                   Consensus & Synthesis Node                   │   │
│   │    Enforces: Confidence % + Evidence + Risks + Alternatives    │   │
│   └──────────────────────────────┬─────────────────────────────────┘   │
│                                  │                                     │
│                     Requires Trade Action?                             │
│                     /                  \                               │
│                   No                    Yes                            │
│                  /                        \                            │
│                 ▼                          ▼                           │
│        ┌─────────────────┐       ┌──────────────────────┐              │
│        │ Stream Response │       │ Human Approval Gate  │              │
│        │ to User Cockpit │       │ (interrupt_before)   │              │
│        └─────────────────┘       └──────────┬───────────┘              │
│                                             │ Paused                   │
└─────────────────────────────────────────────┼──────────────────────────┘
                                              │
                                     User Signs Action
                                              │
                                              ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Resume Graph Workflow (`POST /workflows/{run_id}/resume`)              │
│  - Execution Agent dispatches to Spec 02 Venue Engine                  │
│  - Journal Agent records post-mortem & emotional state                 │
│  - Notification Agent dispatches omnichannel alerts                    │
└────────────────────────────────────────────────────────────────────────┘
```

## 2. Directory Structure

```text
specs/spec-03-agent-platform/
├── spec.md              # Specification document
├── plan.md              # This architecture plan
├── data-model.md        # Data models (checkpoints, traces, prompts, tools)
└── tasks.md             # Test-first task breakdown
```

## 3. Core Technical Decisions & Rationale

### ADR-03-01: Native LangGraph StateGraph with Postgres Checkpointers
- **Context**: Autonomous multi-agent coordination requires cycle support, dynamic conditional branching, long-lived pauses for human review, and crash resilience.
- **Decision**: Adopt native LangGraph 0.2 `StateGraph` backed by asynchronous PostgreSQL checkpointers (`AsyncPostgresSaver`).
- **Consequences**: Eliminates fragile custom workflow engines; enables zero-loss recovery from server restarts while maintaining persistent thread execution state.

### ADR-03-02: Strict Four-Part Recommendation Contract
- **Context**: Unchecked LLM trading advice frequently produces vague or hallucinated conviction without quantifiable rationale or risk boundaries.
- **Decision**: Programmatically validate every synthesized recommendation schema against Pydantic validators requiring: (1) `confidence_score` (0.00-100.00 Decimal), (2) `evidence` (list of verified signals), (3) `risks` (counter-theses and volatility drivers), (4) `alternative_scenarios` (invalidation triggers).
- **Consequences**: Fails graph execution if LLM synthesis omits risk analysis; guarantees complete transparency to human operators.

### ADR-03-03: Sandboxed Tool Registry with Role-Based Tool Binding
- **Context**: Unrestricted tool access exposes execution infrastructure to malicious prompt injection or unauthorized agent actions.
- **Decision**: Implement a centralized `ToolRegistry` where tools declare required roles. Agents receive only their whitelisted tools during LLM runtime binding (e.g. only `Execution Agent` has access to `tool_submit_order`, and only under an approved human token).
- **Consequences**: Hard boundaries prevent analytical agents from triggering execution or modifying system configurations.

## 4. Operational Readiness & Reliability

- **Model Fallback Circuit Breaker**: If primary LLM endpoint encounters 429 / 5xx or latency > 10s, requests automatically fail over to designated secondary provider (e.g. Claude 3.5 Sonnet -> GPT-4o -> local vLLM).
- **Trace Redaction & Sanitization**: Prompts and completions are scanned prior to trace storage to redact inadvertent PII, API tokens, or session cookies.
