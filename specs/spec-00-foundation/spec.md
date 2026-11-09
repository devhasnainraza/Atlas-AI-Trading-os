# Spec 00 — Foundation & System Architecture

**Project**: Atlas AI Trading OS  
**Status**: Ratified | **Version**: 1.0.0 | **Date**: 2026-09-21  
**Target Path**: `specs/spec-00-foundation/`  
**Constitutional Compliance**: Core Principles I–XII Verified  

---

## 1. Vision & Goals

### 1.1 System Vision
Atlas AI Trading OS is an enterprise-grade multi-agent AI operating system designed for retail and institutional traders in Forex and Cryptocurrency markets. Spec 00 establishes the foundational monorepo, execution runtime, event infrastructure, AI interface abstraction layer, and observability framework upon which all higher-level trading, intelligence, and agent workflows depend.

### 1.2 Core Business & Technical Goals
- **Modular Monolith First**: Single deployable backend codebase (`apps/api`) composed of isolated domain modules with strict port-and-adapters seams, enabling horizontal scaling and future service extraction without contract churn.
- **Resilient Asynchronous Event Backbone**: Event-driven communication powered by Apache Kafka / Redpanda with transactional outbox patterns, guaranteed at-least-once delivery, idempotency ledgers, and dead-letter queue (DLQ) replay capabilities.
- **Provider-Agnostic AI Gateway**: Abstract protocols for agent registration, tool dispatch, prompt versioning, scoped memory, and model providers, completely decoupling domain logic from proprietary LLM vendor APIs.
- **High-Assurance Observability**: Zero-leakage structured logging, end-to-end W3C distributed trace context propagation, and sub-second operational metrics across all services.
- **Zero-Trust & Compliance Ready**: Deny-by-default routing, correlation ID tracking on 100% of network traffic, and strict isolation of broker secrets from client environments.

---

## 2. Functional Requirements

- **FR-001**: Monorepo orchestration MUST support multi-language builds (`Python 3.12+` managed via `uv`, `TypeScript 5.x` / `Node 22 LTS` managed via `pnpm` and `Turborepo`).
- **FR-002**: Backend API MUST follow the port-and-adapters module layout (`router.py -> service.py -> domain/ -> repository/`).
- **FR-003**: Cross-module communication MUST occur strictly via public interfaces (`public.py`) or asynchronous domain events published to the event bus. Direct cross-module internal imports MUST be prevented at lint and test time.
- **FR-004**: The platform MUST implement a Transactional Outbox pattern ensuring database writes and event emission occur within the same ACID transaction.
- **FR-005**: The background worker service (`services/worker`) MUST consume outbox tables and relay events to Kafka topics with exponential backoff retries and DLQ dead-letter routing.
- **FR-006**: The platform MUST maintain an immutable Processed Event Ledger preventing duplicate event processing (idempotent consumers).
- **FR-007**: The AI Gateway (`shared/atlas_ai`) MUST expose versioned registries for `AgentDefinition`, `ToolDefinition`, and `PromptDefinition`.
- **FR-008**: Model provider access MUST resolve models by internal symbolic aliases (`fast-reasoning`, `deep-analysis`, `embedding-fast`), forbidding hardcoded vendor model strings in business logic.
- **FR-009**: The API Gateway MUST inject and propagate W3C `traceparent` headers and a unique correlation ID (`X-Correlation-ID`) across all requests, background tasks, and event messages.
- **FR-010**: The platform MUST implement centralized error handling adhering to the Atlas Error Taxonomy with uniform JSON envelopes and machine-readable error codes.
- **FR-011**: The platform MUST provide multi-tiered rate limiting (Redis token bucket) with distinct quotas for anonymous, authenticated, and privileged identities.
- **FR-012**: The platform MUST expose standardized health endpoints (`/health/live`, `/health/ready`) verifying database, cache, broker, and worker subsystem readiness.

---

## 3. Non-Functional Requirements

- **NFR-001 (Latency)**: API Gateway gateway middleware overhead MUST NOT exceed 5ms at p95 and 10ms at p99.
- **NFR-002 (Event Throughput)**: The transactional outbox and worker relay pipeline MUST sustain a minimum of 2,500 events/second under peak load without consumer lag accumulation exceeding 5 seconds.
- **NFR-003 (Availability)**: Core API platform availability SLO is 99.95% uptime (< 21.9 minutes downtime/month).
- **NFR-004 (Precision & Float Ban)**: All monetary values, quantities, balances, and prices across all layers MUST be represented using arbitrary-precision `Decimal` (Python) and string-backed BigNumber structures (TypeScript). The use of floating-point numbers (`float`, `double`) for monetary calculations is strictly forbidden and rejected by AST linters.
- **NFR-005 (Resource Footprint)**: Base API container memory footprint MUST remain under 256MB at idle; worker memory under 180MB.

---

## 4. User Stories

### US-001: Platform Engineer Extends Capability via Module Template (Priority: P1)
- **Given** an engineer developing a new platform capability,
- **When** they scaffold a module from `apps/api/src/atlas_api/modules/_template/`,
- **Then** the module registers its public contract without modifying any internal code in existing modules, passes import linter boundaries, and participates in API routing.

### US-002: Reliable Event-Driven Inter-Module Coordination (Priority: P1)
- **Given** a module initiating a state change that other subsystems depend upon,
- **When** the state mutation commits in PostgreSQL,
- **Then** the corresponding domain event is saved to the outbox table within the same transaction and delivered to Kafka within 200ms, triggering registered downstream consumers.

### US-003: Operational Observability & Degraded State Diagnosis (Priority: P2)
- **Given** an operator monitoring production health during a network partition,
- **When** a dependency (e.g. Redis or Kafka) becomes unreachable,
- **Then** `/health/ready` immediately returns HTTP 503 with a granular subsystem diagnostic payload, and all related error logs carry identical correlation IDs for cross-service tracing.

---

## 5. Agent Architecture

While higher-level trading agents are defined in Spec 03, Spec 00 establishes the foundational execution environment and runtime host for all agents:

```text
+-------------------------------------------------------------------------+
|                          Atlas Agent Host Runtime                        |
|                                                                         |
|  +--------------------+   +---------------------+   +----------------+  |
|  |  Agent Registry    |   |    Tool Registry    |   | Prompt Registry|  |
|  |  (Spec & Version)  |   | (Schemas & Policies)|   | (Templates)    |  |
|  +---------+----------+   +----------+----------+   +--------+-------+  |
|            |                         |                       |          |
|            +-------------------------+-----------------------+          |
|                                      |                                  |
|                         +------------v------------+                     |
|                         |    Supervisor / Engine  |                     |
|                         |      (LangGraph Core)   |                     |
|                         +------------+------------+                     |
|                                      |                                  |
|           +--------------------------+-------------------------+        |
|           |                                                    |        |
|  +--------v---------+                                 +--------v-----+  |
|  | Memory Store     |                                 | Model Router |  |
|  | (User-Scoped KV) |                                 | (Alias -> LLM|  |
|  +------------------+                                 +--------------+  |
+-------------------------------------------------------------------------+
```

### Agent Registry Interfaces (`shared/atlas_ai/interfaces.py`)
- `AgentRegistry`: Canonical catalogue tracking agent status (`registered`, `active`, `suspended`), versions, capabilities, and permitted tool bindings.
- `ToolRegistry`: Validates JSON schema specifications for all agent-callable functions and enforces granular execution permission checks.
- `PromptRegistry`: Version-controlled prompt repository with hydration and template metadata verification.

---

## 6. State Design

### 6.1 Process State & Correlation Context
All runtime execution contexts hold an immutable `CorrelationContext` stored in Python's `contextvars`:
```python
@dataclass(frozen=True)
class CorrelationContext:
    correlation_id: str
    trace_id: str
    span_id: str
    user_id: str | None = None
    session_id: str | None = None
```

### 6.2 Outbox Event State Machine
```text
[CREATED] (Atomic with DB Transaction)
    |
    v
[PENDING_RELAY]
    |
    +---> [RELAYED] (Acknowledged by Kafka)
    |
    +---> (Fail 3x) ---> [DEAD_LETTER] (Requires Manual / Script Replay)
```

---

## 7. LangGraph Workflow Integration

Spec 00 provides the execution harness for LangGraph graphs:
- **Base Checkpoint Saver**: Async PostgreSQL checkpointer persisting graph snapshots after each node completion.
- **Interrupt Protocol**: Built-in state suspension mechanism (`interrupt_before=["human_approval"]`) ensuring graphs pause safely and yield control to user approval endpoints.
- **Workflow Engine Protocol**:
```python
class WorkflowEngine(Protocol):
    async def run(self, workflow: str, version: str, inputs: dict[str, Any]) -> str: ...
    async def pause(self, run_id: str) -> None: ...
    async def resume(self, run_id: str, feedback: dict[str, Any] | None = None) -> None: ...
    async def cancel(self, run_id: str) -> None: ...
```

---

## 8. Tool Specifications

The foundation defines foundational platform tools accessible to administrative and maintenance agents:

### 8.1 System Health Tool (`tool_system_health`)
- **Description**: Queries real-time health metrics and dependency states across services.
- **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "include_metrics": { "type": "boolean", "default": false },
      "subsystems": { 
        "type": "array", 
        "items": { "type": "string", "enum": ["db", "redis", "kafka", "workers"] } 
      }
    }
  }
  ```
- **Output Schema**: Returns status object with latencies and degraded status indicators.
- **Security**: Requires `platform:read` permission. Read-only, side-effect free.

### 8.2 Event Replay Tool (`tool_event_replay`)
- **Description**: Initiates controlled replay of events from DLQ or historical offset ranges.
- **Input Schema**:
  ```json
  {
    "type": "object",
    "required": ["topic", "from_timestamp"],
    "properties": {
      "topic": { "type": "string" },
      "from_timestamp": { "type": "string", "format": "date-time" },
      "to_timestamp": { "type": "string", "format": "date-time" },
      "dry_run": { "type": "boolean", "default": true }
    }
  }
  ```
- **Security**: Requires `platform:admin` permission. Emits high-priority audit events.

---

## 9. API Specifications

Base URL: `/api/v1`

### 9.1 Platform Health & Status
- **`GET /health/live`**: Fast liveness probe. Returns `{"status": "alive"}` (HTTP 200).
- **`GET /health/ready`**: Deep readiness probe. Verifies PostgreSQL pool, Redis ping, Kafka metadata.
  - Success: HTTP 200 `{"status": "ready", "components": {"database": "up", "redis": "up", "kafka": "up"}}`
  - Failure: HTTP 503 with degraded component details.
- **`GET /health/version`**: Build hash, release version, and environment tag.

### 9.2 Audit Log Inspection
- **`GET /api/v1/platform/audit-logs`**: Query immutable audit log records.
  - **Query Params**: `user_id`, `action`, `from_time`, `to_time`, `page`, `page_size`.
  - **Response**: Paginated array of audit events with redacted parameters and IP hashes.

### 9.3 Standard Error Envelope
All error responses adhere to the unified envelope:
```json
{
  "error": {
    "code": "ATLAS-PLAT-004",
    "message": "Resource could not be located.",
    "correlation_id": "c1d4e789-9821-4f4c-8fa2-3c224b172a81",
    "details": {},
    "timestamp": "2026-09-21T20:05:00Z"
  }
}
```

---

## 10. Database Schema

### 10.1 Transactional Outbox Table (`platform_outbox`)
```sql
CREATE TABLE platform_outbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_type VARCHAR(64) NOT NULL,
    aggregate_id VARCHAR(128) NOT NULL,
    event_type VARCHAR(128) NOT NULL,
    payload JSONB NOT NULL,
    headers JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    retry_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    relayed_at TIMESTAMPTZ
);

CREATE INDEX idx_outbox_pending ON platform_outbox (status, created_at) 
WHERE status = 'PENDING';
```

### 10.2 Processed Event Ledger (`platform_event_ledger`)
```sql
CREATE TABLE platform_event_ledger (
    event_id UUID PRIMARY KEY,
    consumer_group VARCHAR(64) NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_event_consumer UNIQUE (event_id, consumer_group)
);
```

### 10.3 Immutable Audit Log (`platform_audit_log`)
```sql
CREATE TABLE platform_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id VARCHAR(64) NOT NULL,
    actor_role VARCHAR(32) NOT NULL,
    action VARCHAR(128) NOT NULL,
    resource_type VARCHAR(64) NOT NULL,
    resource_id VARCHAR(128) NOT NULL,
    client_ip VARCHAR(45) NOT NULL,
    user_agent VARCHAR(256),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_actor_created ON platform_audit_log (actor_id, created_at DESC);
CREATE INDEX idx_audit_action ON platform_audit_log (action, created_at DESC);
```

---

## 11. Frontend Screens & Components

While core trading screens reside in Spec 09, Spec 00 supplies foundational UI tokens and system error shells in `packages/ui` and `apps/web`:

### 11.1 Design System & Aesthetic Foundations
- **Color Palette**: Dark-mode first with deep obsidian bases (`#0A0B0E`), subtle dark indigo elevations (`#12151F`), glassmorphic borders (`rgba(255, 255, 255, 0.08)`), vibrant telemetry accents (Emerald `#10B981` for profit/healthy, Crimson `#EF4444` for drawdown/danger, Electric Blue `#3B82F6` for agent thought/active state).
- **Typography**: Inter / Outfit sans-serif pairing with JetBrains Mono for monetary values and order ticket IDs.
- **Global Error Shell**: Full-screen reactive fallback capturing unhandled React boundary faults, rendering correlation IDs and one-click diagnostics download.
- **System Status Indicator**: Persistent navbar pill widget reflecting live WebSocket connectivity and platform health status.

---

## 12. Security Requirements

- **SEC-001 (Zero Secret Exposure)**: Broker secrets, private keys, and encryption credentials MUST never enter client browsers, application logs, or error responses.
- **SEC-002 (Transport Encryption)**: All internal and external network communication MUST use TLS 1.3 in transit.
- **SEC-003 (Header Hardening)**: API responses MUST include standard defensive HTTP headers (`Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, strict `Content-Security-Policy`).
- **SEC-004 (Import Boundary Enforcement)**: Python architecture boundaries are enforced using `import-linter` in CI; cross-module leaks prevent build pass.
- **SEC-005 (Secret Scanning)**: Git commit hooks and CI security pipelines run Gitleaks and Trivy vulnerability scans on all dependencies and container layers.

---

## 13. Testing Strategy

```text
Unit Tests (Pure logic, mocked IO)             --> uv run pytest tests/unit
Contract Tests (OpenAPI schema, event formats)  --> uv run pytest tests/contract
Integration Tests (Postgres, Redis, Kafka testcontainers) --> uv run pytest tests/integration
Import Boundary Compliance                     --> uv run lint-imports
```
- **Contract Testing**: Schemathesis verifies API endpoints against `contracts/platform-api.openapi.yaml`.
- **Event Validation**: Every event type is strictly verified against `EventCatalog` schemas before serialization.
- **AST Float Checker**: Automated AST verification (`tests/contract/test_no_float_money.py`) scans code trees to ensure zero usage of native float for monetary quantities.

---

## 14. Deployment Plan

- **Containerization**: Multi-stage Dockerfiles (`infra/docker/Dockerfile.api`, `infra/docker/Dockerfile.worker`, `infra/docker/Dockerfile.web`) building stripped production wheels with non-root runtime users.
- **Orchestration**: Kubernetes deployment manifests and Helm charts (`infra/k8s/`) configuring:
  - Horizontal Pod Autoscaler (HPA) targeting 70% CPU / 75% Memory utilization.
  - Pod Disruption Budgets (PDB) guaranteeing minimum 2 replicas during node drains.
  - Readiness and Liveness HTTP probes bound to `/health/ready` and `/health/live`.
- **Zero-Downtime Rolling Updates**: Blue/Green or RollingUpdate strategy with 25% maxSurge and 0 maxUnavailable.

---

## 15. Future Enhancements

- **Phase 2 Extraction**: Autonomous extraction of high-throughput modules (e.g. Market Data Ingestion) into standalone microservices using the identical public interfaces.
- **Multi-Region Event Mirroring**: Active-active Kafka cluster mirroring using MirrorMaker 2 for ultra-low latency geo-routing.
- **Hardware-Accelerated Token Processing**: Dedicated inference sidecars for specialized local LLM reasoning models.
