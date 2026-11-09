# Spec 03 — AI Agent Core Platform ⭐

**Project**: Atlas AI Trading OS  
**Status**: Ratified | **Version**: 1.0.0 | **Date**: 2026-09-21  
**Target Path**: `specs/spec-03-agent-platform/`  
**Constitutional Compliance**: Core Principles I, III, IV, V, VI, X, XI, XII Verified  

---

## 1. Vision & Goals

### 1.1 System Vision
Spec 03 represents the heart of Atlas AI Trading OS. It establishes the multi-agent cognitive architecture powered by LangGraph, coordinating 13 specialized AI agents into a collaborative, decentralized intelligence network. No single agent possesses absolute trading authority; rather, specialized analytical agents contribute evidence and perspectives to a Manager Agent, which synthesizes recommendations and enforces constitutional constraints before seeking human approval.

### 1.2 Core Business & Technical Goals
- **Decentralized Multi-Agent Specialization**: Thirteen dedicated agents each mastering one domain (Market, News, Social, Economic, Technical, Risk, Portfolio, Journal, Learning, Execution, Notification, Memory, overseen by Manager Agent).
- **LangGraph State Graph Orchestration**: Deterministic, cyclic, and checkpointed state machines managing inter-agent debate, data sharing, tool invocations, and error recovery.
- **Human-Centered Control Gate**: Unbypassable interrupt nodes (`interrupt_before`) enforcing that consequential actions (trade submission, strategy activation, risk limit modifications) pause for explicit human sign-off.
- **Explainability & Transparent Output**: Strict enforcement of Principle III: every recommendation generated across the agent mesh MUST include Confidence Score (0–100%), Supporting Evidence, Risk Assessment, and Alternative Scenarios.
- **Multi-Agent Event Bus Coordination**: Seamless synchronization between background reactive event streams (Kafka) and interactive user-driven conversational sessions.

---

## 2. Functional Requirements

- **FR-001**: The platform MUST implement the complete roster of 13 Specialized Agents:
  1. `Manager Agent`: High-level workflow orchestration, task delegation, consensus synthesis, and final user communication.
  2. `Market Agent`: 24/7 real-time price monitoring, anomaly detection, volatility alerts, and market regime classification.
  3. `News Agent`: Breaking financial news ingestion, entity extraction, sentiment scoring, and market impact assessment.
  4. `Social Agent`: Real-time sentiment aggregation from Twitter/X, Reddit (`r/wallstreetbets`, `r/forex`), Telegram, and Discord trading channels.
  5. `Economic Agent`: Macroeconomic calendar tracking, interest rate decision monitoring, CPI/NFP release impact prediction.
  6. `Technical Agent`: Chart pattern recognition, multi-timeframe indicator analysis (RSI, MACD, Bollinger Bands), and advanced methodology models (ICT, Smart Money Concepts [SMC], Wyckoff).
  7. `Risk Agent`: Real-time Value-at-Risk (VaR) calculation, portfolio margin stress testing, correlation risk analysis, and constitutional risk gate verification.
  8. `Portfolio Agent`: Multi-asset allocation health, equity curve tracking, beta exposure, and rebalancing recommendations.
  9. `Journal Agent`: Automatic trade capture, emotional tagging, execution post-mortem documentation, and trade performance attribution.
  10. `Learning Agent`: User behavioral pattern analysis, recurring mistake identification (e.g. FOMO, revenge trading), and coaching insight generation.
  11. `Execution Agent`: Broker order formatting, smart order routing, execution slippage tracking, and venue execution status reporting.
  12. `Notification Agent`: Multi-channel dispatch (Push, Email, Telegram, Discord, SMS) with priority filtering and user quiet-hours enforcement.
  13. `Memory Agent`: Dynamic retrieval and consolidation of user preferences, historical interactions, and episodic trade context via pgvector.
- **FR-002**: Agents MUST communicate via a typed inter-agent messaging protocol adhering to the `AgentMessageEnvelope` schema.
- **FR-003**: Tool invocations MUST be validated against the `ToolRegistry`, enforcing per-agent permission policies and JSON schema constraints.
- **FR-004**: Graph execution MUST be persistent and resumable across worker restarts using PostgreSQL-backed LangGraph checkpointers.
- **FR-005**: The system MUST implement an automated Retry & Circuit Breaker mechanism for LLM provider failures, seamlessly falling back across model provider aliases (`primary-reasoning` -> `fallback-reasoning`).
- **FR-006**: Agent scheduling MUST support both continuous background execution (cron / event triggers via Celery & Kafka) and reactive on-demand user conversations.

---

## 3. Non-Functional Requirements

- **NFR-001 (Graph Node Latency)**: Non-LLM agent processing nodes (data transformation, routing, validation) MUST execute in < 20ms at p95.
- **NFR-002 (Inter-Agent Consensus Latency)**: End-to-end multi-agent research and debate pipeline MUST deliver a synthesized recommendation within 8 seconds when utilizing fast reasoning models.
- **NFR-003 (State Checkpoint Persistence)**: LangGraph state snapshots MUST persist to PostgreSQL in < 15ms per node transition.
- **NFR-004 (Token Efficiency)**: Context window management MUST compress and prune intermediate tool outputs, ensuring agent context lengths do not exceed model limits or waste token budgets.
- **NFR-005 (Auditability)**: 100% of LLM prompts, raw completions, tool arguments, and agent thoughts MUST be captured in structured tracing logs for audit and explainability.

---

## 4. User Stories

### US-001: Comprehensive Multi-Agent Market Analysis (Priority: P1)
- **Given** a user requesting an in-depth analysis on `BTC/USDT`,
- **When** the user sends "Analyze BTC" through chat or dashboard,
- **Then** the Manager Agent dispatches tasks in parallel to Technical, Market, News, Economic, and Social Agents, aggregates their findings, runs a Risk Agent check, and returns a unified report with Confidence %, Evidence, and Alternative Scenarios.

### US-002: Autonomous Risk Intervention During High-Impact Events (Priority: P1)
- **Given** the Economic Agent detecting an upcoming unexpected Federal Reserve rate hike announcement,
- **When** open positions exceed allowable event volatility risk limits,
- **Then** the Risk Agent flags the condition to the Manager Agent, which immediately dispatches a high-priority notification to the trader with recommended hedging actions.

### US-003: Human-in-the-Loop Trade Proposal Approval (Priority: P1)
- **Given** a high-confidence trade opportunity formulated by the agent network,
- **When** the proposal reaches the execution stage,
- **Then** LangGraph halts at the `human_approval` interrupt node, dispatches an approval ticket to the user's dashboard and Telegram, and awaits explicit approval before the Execution Agent dispatches the order.

---

## 5. Agent Architecture

```text
+-----------------------------------------------------------------------------------+
|                                  Manager Agent                                    |
|                   (Supervisor, Intent Classifier, Synthesis Engine)               |
+-----------------------------------------+-----------------------------------------+
                                          |
        +---------------------------------+---------------------------------+
        |                                 |                                 |
+-------v-------+                 +-------v-------+                 +-------v-------+
|  Market Team  |                 | Analysis Team |                 | Control Team  |
+-------+-------+                 +-------+-------+                 +-------+-------+
        |                                 |                                 |
        +-- Market Agent (24/7 Ticks)     +-- Technical Agent (ICT/SMC)     +-- Risk Agent (VaR/Limits)
        +-- News Agent (Headlines/NLP)    +-- Portfolio Agent (Allocations) +-- Execution Agent (Orders)
        +-- Social Agent (Sentiment)      +-- Journal Agent (Logging)       +-- Notification Agent (Alerts)
        +-- Economic Agent (Macro/CPI)    +-- Learning Agent (Coaching)     +-- Memory Agent (Context/RAG)
```

### Agent Responsibilities & Bounds Matrix
| Agent Name | Primary Inputs | Permitted Tools | Max Authority |
|---|---|---|---|
| `Manager` | User commands, Team reports | Subagent dispatch, User response | High-level orchestration |
| `Market` | Live ticks, L2 order books | Market scanner, Volume profiler | Advisory only |
| `News` | RSS, News APIs, SEC filings | Web scraper, NLP sentiment tool | Advisory only |
| `Social` | Twitter API, Reddit, Discord | Social scraper, Sentiment analyzer | Advisory only |
| `Economic` | Macro calendars, Central banks | Calendar API, Interest rate DB | Advisory only |
| `Technical` | OHLCV historical & live bars | Indicator engine, Pattern detector | Advisory only |
| `Risk` | Account equity, Open positions | Risk calculator, Stress tester | Hard veto power |
| `Portfolio` | Multi-account balances | Allocation analyzer, Beta calculator | Advisory only |
| `Journal` | Completed trades, User notes | Journal DB writer, Chart capturer | Internal record-keeping |
| `Learning` | Journal history, Win/Loss stats | Pattern classifier, Coaching engine | Advisory only |
| `Execution` | Confirmed trade intents | Venue adapter order submitter | Submits ONLY with human token |
| `Notification` | System events, Agent alerts | Omnichannel push, Telegram bot | Outbound messaging only |
| `Memory` | User chats, Trade history | Vector search, Profile store | Read / Write memory store |

---

## 6. State Design

### 6.1 Multi-Agent Shared State Schema (`AgentSystemState`)
```python
class AgentSystemState(TypedDict):
    session_id: str
    user_id: str
    symbol: str
    timeframe: str
    user_query: str
    
    # Intelligence inputs
    market_data: dict[str, Any]
    technical_analysis: dict[str, Any]
    news_sentiment: dict[str, Any]
    social_sentiment: dict[str, Any]
    economic_context: dict[str, Any]
    
    # Risk & Evaluation
    risk_evaluation: dict[str, Any]
    portfolio_impact: dict[str, Any]
    
    # Synthesis & Recommendation
    confidence_score: Decimal  # 0.00 to 100.00
    evidence: list[str]
    risks: list[str]
    alternative_scenarios: list[str]
    synthesized_recommendation: str
    
    # Execution & Human Gate
    requires_human_approval: bool
    human_approved: bool | None
    execution_result: dict[str, Any] | None
    
    # Conversation & Scratchpad
    messages: Annotated[list[BaseMessage], add_messages]
```

---

## 7. LangGraph Workflow Integration

The core LangGraph definition orchestrating multi-agent analysis and trade proposal:

```text
               +-----------------------+
               |     Start / Input     |
               +-----------+-----------+
                           |
                           v
               +-----------------------+
               |  Manager: Plan & Route|
               +-----------+-----------+
                           |
            +--------------+--------------+
            |              |              |
            v              v              v
     +------------+ +------------+ +------------+
     | Technical  | | Market/News| |  Economic  |  (Parallel Sub-Tasks)
     +------+-----+ +-----+------+ +------+-----+
            |             |               |
            +-------------+---------------+
                           |
                           v
               +-----------------------+
               |   Risk & Portfolio    |
               |      Evaluation       |
               +-----------+-----------+
                           |
                           v
               +-----------------------+
               |   Manager Synthesis   |
               | (Confidence/Evidence) |
               +-----------+-----------+
                           |
            +--------------+--------------+
            |                             |
   (Informational Only)        (Trade Recommendation)
            |                             |
            v                             v
     +--------------+           +--------------------+
     | Send Response|           |   Human Approval   |  <-- interrupt_before
     +--------------+           |     Interrupt      |
                                +---------+----------+
                                          |
                                 (User Approves / Rejects)
                                          |
                                          v
                                +--------------------+
                                |  Execution Agent   |
                                +---------+----------+
                                          |
                                          v
                                +--------------------+
                                |  Journal / Notify  |
                                +--------------------+
```

---

## 8. Tool Specifications

### 8.1 Technical Indicator Calculation Tool (`tool_calc_indicators`)
- **Description**: Computes RSI, MACD, EMA ribbons, and Bollinger Bands over historical bars.
- **Input Schema**:
  ```json
  {
    "type": "object",
    "required": ["symbol", "timeframe", "indicators"],
    "properties": {
      "symbol": { "type": "string" },
      "timeframe": { "type": "string", "enum": ["1m", "5m", "15m", "1h", "4h", "1d"] },
      "indicators": { "type": "array", "items": { "type": "string" } },
      "period": { "type": "integer", "default": 100 }
    }
  }
  ```
- **Output Schema**: Returns calculated series and current indicator values.

### 8.2 Macro Calendar Query Tool (`tool_macro_calendar`)
- **Description**: Fetches scheduled high-impact economic releases (CPI, Interest Rates, NFP).
- **Input Schema**:
  ```json
  {
    "type": "object",
    "required": ["currency", "days_ahead"],
    "properties": {
      "currency": { "type": "string", "enum": ["USD", "EUR", "GBP", "JPY"] },
      "days_ahead": { "type": "integer", "default": 3 },
      "minimum_impact": { "type": "string", "enum": ["LOW", "MEDIUM", "HIGH"], "default": "HIGH" }
    }
  }
  ```

---

## 9. API Specifications

### 9.1 Agent Interaction Endpoints
- **`POST /api/v1/agents/chat`**: Initiates or continues an interactive multi-agent analysis session.
  - Request: `{"session_id": "...", "message": "What is your outlook on EUR/USD today?"}`
  - Response: Server-Sent Events (SSE) streaming thought tokens and final response envelope.
- **`GET /api/v1/agents/active-workflows`**: Lists active or paused LangGraph workflow executions.
- **`POST /api/v1/agents/workflows/{run_id}/resume`**: Resumes a paused workflow with user decision (`{"approved": true, "adjusted_size": "0.1"}`).
- **`POST /api/v1/agents/workflows/{run_id}/cancel`**: Cancels an active or paused agent workflow.

---

## 10. Database Schema

### 10.1 LangGraph Checkpoint Tables (`agent_checkpoints`)
```sql
CREATE TABLE agent_checkpoints (
    thread_id VARCHAR(128) NOT NULL,
    checkpoint_ns VARCHAR(128) NOT NULL DEFAULT '',
    checkpoint_id VARCHAR(128) NOT NULL,
    parent_checkpoint_id VARCHAR(128),
    type VARCHAR(64),
    checkpoint BYTEA NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

CREATE INDEX idx_checkpoints_created ON agent_checkpoints (thread_id, created_at DESC);
```

### 10.2 Agent Execution Log (`agent_execution_traces`)
```sql
CREATE TABLE agent_execution_traces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(128) NOT NULL,
    agent_name VARCHAR(64) NOT NULL,
    node_name VARCHAR(64) NOT NULL,
    prompt_tokens INT NOT NULL DEFAULT 0,
    completion_tokens INT NOT NULL DEFAULT 0,
    model_alias VARCHAR(64) NOT NULL,
    input_payload JSONB NOT NULL,
    output_payload JSONB NOT NULL,
    duration_ms INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_traces_session ON agent_execution_traces (session_id);
```

---

## 11. Frontend Screens & Components

### 11.1 Multi-Agent Cognitive Cockpit
- **Live Agent Status Ribbon**: Displays real-time status chips for all 13 agents (`IDLE`, `ANALYZING`, `CONSENSUS_DEBATE`, `WAITING_APPROVAL`) with pulsing activity rings.
- **Consensus & Confidence Meter**: Interactive radial dial displaying the synthesized Confidence Score (0–100%) with color-coded risk bands.
- **Agent Rationale Timeline**: Visual tree graph displaying the exact line of reasoning, data points contributed by each agent, and conflicting opinions resolved by the Manager Agent.
- **Interactive Approval Modal**: Slide-in card presenting the trade hypothesis, supporting evidence bullets, counter-arguments, stop-loss justification, and dual "Approve & Execute" / "Decline" buttons.

---

## 12. Security Requirements

- **SEC-001 (Tool Sandbox Isolation)**: Tools run in strictly bounded Python environments with network access restricted to authorized endpoints.
- **SEC-002 (Prompt Injection Defense)**: All external inputs (news feeds, social posts, user chat) are sanitized and tagged as untrusted data in LLM prompt templates.
- **SEC-003 (Constitutional Overrides)**: Risk Agent vetoes are evaluated deterministically in Python code, preventing LLMs from hallucinating past risk rules.

---

## 13. Testing Strategy

- **Agent Unit Tests**: Mock LLM responses using deterministic fixtures to test graph state transitions and edge routing.
- **Multi-Agent Evaluation Benchmarks**: Automated evaluation harness measuring synthesis quality, hallucination rate, and adherence to the 4-part recommendation contract.
- **Human-in-the-Loop Interrupt Verification**: Integration tests confirming workflows unconditionally pause at `human_approval` and resume only upon receiving cryptographic user tokens.

---

## 14. Deployment Plan

- **Distributed Graph Workers**: Celery / Redis worker pools dedicated to background agent workflows with independent scaling for CPU/IO heavy tasks.
- **Model Gateway Fallback Clusters**: Configuration supporting automated failover between Anthropic, OpenAI, and local self-hosted inference servers (vLLM / Ollama).

---

## 15. Future Enhancements

- **Autonomous Agent Evolution**: Self-improving prompt adjustments based on historical trade win/loss outcomes evaluated by the Learning Agent.
- **Voice Agent Interface**: Ultra-low latency full-duplex voice interface for natural language hands-free trading commands.
- **Decentralized Multi-Agent Swarms**: Collaborative consensus across multiple independent user agent clusters.
