# Data Model: AI Agent Core Platform

**Feature**: 03-agent-platform | **Date**: 2026-09-21 | **Plan**: [plan.md](./plan.md)

Conventions per Spec 00: UUIDv7 `id` primary keys, `created_at` / `updated_at` `timestamptz`, snake_case names, enums CHECK-constrained. User-scoped tables carry indexed `user_id`. Checkpoint tables support LangGraph 0.2 async persistence interfaces.

## agent_thread

Represents an ongoing or completed multi-agent conversation or autonomous analytical execution session.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| user_id | uuid | FK user; indexed |
| title | text | Human-readable session summary |
| status | text | `active | paused_approval | completed | cancelled | failed` |
| current_node | text | Currently active or paused LangGraph node name |
| symbol | text | Primary asset context (e.g. `BTC/USDT`, `EUR/USD`), optional |
| timeframe | text | Primary analysis timeframe, optional |
| total_prompt_tokens | int | Cumulative prompt tokens consumed |
| total_completion_tokens| int | Cumulative completion tokens generated |
| total_cost_usd | numeric(12, 6) | Estimated LLM inference cost |
| created_at | timestamptz | Session creation time |
| updated_at | timestamptz | Last activity timestamp |

**Transitions**: `active -> paused_approval` (on reaching `human_approval` interrupt node); `paused_approval -> active` (on user confirmation token); `active -> completed` (on final report generation); `active/paused_approval -> cancelled` (on user abort).

## agent_checkpoints

Low-level state snapshots managed by LangGraph PostgreSQL checkpointer (`AsyncPostgresSaver`).

| Field | Type | Rules |
|---|---|---|
| thread_id | text | Composite PK component (maps to `agent_thread.id`) |
| checkpoint_ns | text | Composite PK component (graph namespace, default empty string) |
| checkpoint_id | text | Composite PK component (deterministic snapshot ID) |
| parent_checkpoint_id | text | Snapshot lineage link |
| type | text | Serializer type (e.g. `json`, `msgpack`) |
| checkpoint | bytea | Compressed binary state dictionary payload |
| metadata | jsonb | Step number, writing agent, timestamp, write channel tags |
| created_at | timestamptz | Checkpoint capture timestamp; indexed |

## agent_execution_traces

Granular telemetry capturing every individual agent node execution and LLM inference invocation.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| thread_id | uuid | FK agent_thread; indexed |
| session_id | text | Logical session or correlation ID |
| agent_name | text | Originating agent (`manager`, `technical`, `risk`, etc.) |
| node_name | text | LangGraph node identifier |
| model_alias | text | e.g. `primary-reasoning` (Claude 3.5 Sonnet), `fast-eval` (GPT-4o) |
| prompt_tokens | int | Input token count |
| completion_tokens| int | Output token count |
| input_payload | jsonb | Node input state slice / prompt messages (sanitized) |
| output_payload | jsonb | Node output delta / completion / tool calls |
| duration_ms | int | Execution latency in milliseconds |
| created_at | timestamptz | Timestamp of trace record |

## agent_tool_registry

Static catalog of validated tools accessible to agents within the platform.

| Field | Type | Rules |
|---|---|---|
| code | text | Unique tool identifier (e.g. `tool_calc_indicators`, `tool_macro_calendar`) |
| display_name | text | Human-readable tool title |
| description | text | Detailed documentation provided to LLMs for tool calling |
| parameters_schema | jsonb | Strict JSON Schema declaring parameter types, required fields, and bounds |
| authorized_agents | text[] | Array of agent codes permitted to invoke this tool |
| is_consequential | boolean | If true, requires explicit human approval token or active trading mandate |
| is_active | boolean | Toggles tool availability without code redeployment |

## agent_approval_ticket

Ephemeral or durable ticket generated when an agent workflow pauses for human approval.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| thread_id | uuid | FK agent_thread; indexed |
| user_id | uuid | FK user; indexed |
| action_type | text | `order_execution | limit_override | strategy_activation` |
| proposal_summary | text | Synthesized human-readable summary of requested action |
| proposed_payload | jsonb | Normalized trade intent or configuration modification parameters |
| confidence_score | numeric(5, 2) | Stated confidence (0.00 to 100.00) |
| evidence_bullets | jsonb | Array of supporting evidence strings |
| risk_bullets | jsonb | Array of identified risks and invalidation levels |
| status | text | `pending | approved | rejected | expired` |
| expires_at | timestamptz | TTL after which ticket invalidates (default 5 minutes) |
| resolved_at | timestamptz | Timestamp of user action |
| resolved_by_ip | inet | IP address of approving device |
| resolution_signature| text | Cryptographic proof of human approval |
