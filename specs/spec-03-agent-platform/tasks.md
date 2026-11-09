# Tasks: AI Agent Core Platform ⭐

**Input**: Design documents from `/specs/spec-03-agent-platform/`
**Prerequisites**: [spec.md](./spec.md), `shared/atlas_ai/interfaces.py`, `shared/atlas_events/`
**Tests**: INCLUDED — constitution mandates test-first for multi-agent state machines, tool validations, and human approval interrupts.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: `US1`–`US3`, or blank for setup/foundational/polish

---

## Phase 1: Setup

**Purpose**: Scaffolding, dependencies, and environment config for LangGraph multi-agent platform.

- [ ] T001 [P] Add LangGraph dependencies (`langgraph`, `langchain-core`, `pydantic-settings`) to `apps/api/pyproject.toml` and `shared/atlas_ai/pyproject.toml` via uv
- [x] T002 [P] Scaffold agent module skeleton in `apps/api/src/atlas_api/modules/agents/` (`public.py`, `router.py`, `schemas.py`, `service.py`, `domain/`)
- [ ] T003 [P] Configure `AgentSettings` (LLM provider keys, model alias mapping: `fast-reasoning`, `deep-analysis`, `fallback-reasoning`, token limits, timeout budgets) in `shared/atlas_core/config.py`
- [ ] T004 [P] Register agent domain events in `shared/atlas_events/catalog.py`: `agent.task.dispatched`, `agent.thought.emitted`, `agent.approval.requested`, `agent.approval.received`

---

## Phase 2: Foundational (⚠️ CRITICAL — blocks every user story)

**Purpose**: Agent registries, state checkpointing, and tool dispatch infrastructure.

- [x] T005 [P] Implement LangGraph Checkpoint Saver in `shared/atlas_ai/checkpointer.py` using `InMemoryCheckpointSaver` & `CheckpointSaver` interface
- [ ] T006 [P] Implement concrete `PostgresAgentRegistry` and `PostgresToolRegistry` adhering to `shared/atlas_ai/interfaces.py`
- [x] T007 [P] Implement Model Provider Router (`shared/atlas_ai/providers.py`) resolving symbolic aliases (`fast-reasoning`, `deep-analysis`) with automatic provider failover
- [x] T008 [P] Implement Tool Executor with strict JSON schema validation, execution timeout guards, and permission checks in `shared/atlas_ai/tools.py`
- [x] T009 [P] Implement `AgentMessageEnvelope` and inter-agent message serialization in `shared/atlas_ai/messages.py`
- [ ] T010 Create Alembic migration for `agent_checkpoints` and `agent_execution_traces` in `apps/api/src/atlas_api/modules/agents/migrations/`

**Checkpoint**: Core LangGraph runtime, persistence, and tool dispatch interfaces ready.

---

## Phase 3: User Story 1 — Multi-Agent Market Analysis (Priority: P1) 🎯 MVP

**Goal**: A user requests market analysis; Manager Agent delegates in parallel to Technical, Market, News, Economic, and Social Agents, synthesizing a 4-part transparent report.

### Tests for User Story 1 ⚠️ write first, must fail

- [x] T011 [P] [US1] Unit test: Manager Agent plans and dispatches sub-tasks to analytical agents in parallel
- [x] T012 [P] [US1] Unit test: 4-part output contract (Confidence %, Evidence, Risks, Alternatives) is strictly validated on synthesized responses
- [x] T013 [P] [US1] Integration test: Multi-agent graph execution with mocked LLM provider fixtures in `tests/agents/test_service_and_interrupt.py`
- [x] T014 [P] [US1] Contract test: `/v1/agents/chat` endpoint against OpenAPI schema in `tests/agents/test_api_endpoints.py`

### Implementation for User Story 1

- [x] T015 [P] [US1] Implement `TechnicalAgent` node (ICT, SMC, RSI/MACD indicator calculations) in `apps/api/src/atlas_api/modules/agents/domain/nodes.py`
- [x] T016 [P] [US1] Implement `MarketAgent` node (price action, volatility, volume profiling) in `apps/api/src/atlas_api/modules/agents/domain/nodes.py`
- [ ] T017 [P] [US1] Implement `NewsAgent` and `EconomicAgent` nodes (macro calendar, headline sentiment) in `apps/api/src/atlas_api/modules/agents/domain/macro.py`
- [ ] T018 [P] [US1] Implement `SocialAgent` node (social sentiment scoring) in `apps/api/src/atlas_api/modules/agents/domain/social.py`
- [x] T019 [US1] Implement `ManagerAgent` synthesis node and dialectic resolution in `apps/api/src/atlas_api/modules/agents/domain/nodes.py`
- [x] T020 [US1] Construct the LangGraph StateGraph compiling parallel branches, fan-in synthesis, and state checkpointing in `apps/api/src/atlas_api/modules/agents/service.py`
- [x] T021 [US1] Implement endpoint `POST /v1/agents/chat` returning constitutional 4-part recommendation envelope
- [ ] T022 [P] [US1] Web: Cognitive Cockpit widget rendering real-time thought streams and agent status ribbons in `apps/web/src/features/agents/`

---

## Phase 4: User Story 2 — Autonomous Risk Intervention (Priority: P1)

**Goal**: High-impact macro events or volatility surges trigger Risk Agent intervention to protect portfolio capital.

### Tests for User Story 2 ⚠️ write first, must fail

- [x] T023 [P] [US2] Unit test: Risk Agent flags portfolio margin breach and enforces hard veto in `tests/agents/test_agent_nodes.py`
- [ ] T024 [P] [US2] Integration test: High-impact economic event broadcast triggers reactive agent evaluation via Kafka consumer

### Implementation for User Story 2

- [x] T025 [US2] Implement `RiskAgent` node computing VaR, margin stress, and constitutional hard veto in `apps/api/src/atlas_api/modules/agents/domain/nodes.py`
- [ ] T026 [US2] Implement `PortfolioAgent` node tracking asset allocation health in `apps/api/src/atlas_api/modules/agents/domain/portfolio.py`
- [ ] T027 [US2] Implement Kafka event consumer in `services/worker` listening to `atlas.market.anomaly` events and dispatching risk intervention workflows
- [ ] T028 [US2] Wire emergency hedging recommendations to notification dispatchers

---

## Phase 5: User Story 3 — Human-in-the-Loop Trade Proposal Approval (Priority: P1)

**Goal**: Trade recommendations pause at an unbypassable interrupt node, resuming only after explicit user approval.

### Tests for User Story 3 ⚠️ write first, must fail

- [x] T029 [P] [US3] Unit test: LangGraph unconditionally interrupts before `execution_agent` when trade action is proposed
- [x] T030 [P] [US3] Integration test: Resume workflow with cryptographic human approval token successfully executes order dispatch
- [x] T031 [P] [US3] Integration test: User rejection or timeout cancels graph run safely without order submission

### Implementation for User Story 3

- [x] T032 [US3] Implement `interrupt_before=["execution_node"]` in LangGraph StateGraph service
- [x] T033 [US3] Implement `ExecutionAgent` node formatting and dispatching orders
- [ ] T034 [US3] Implement `JournalAgent` node logging trade rationale upon fill confirmation
- [x] T035 [US3] Implement `POST /v1/agents/workflows/{run_id}/resume` and `/cancel` endpoints
- [ ] T036 [P] [US3] Web: Interactive Trade Approval modal rendering proposal details, risk metrics, and one-click confirm/reject buttons

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T037 [P] Implement LLM token usage tracking and trace logger recording into `agent_execution_traces`
- [ ] T038 [P] SRE Dashboards: Agent invocation latency, LLM token costs, provider error rates, and interrupt pause durations
- [ ] T039 [P] Automated benchmark evaluation script measuring 4-part output contract compliance across 100 sample prompts
