# Implementation Plan: Platform Foundation & Core System Architecture

**Branch**: `00-platform-foundation` | **Date**: 2026-08-04 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-platform-foundation/spec.md`

## Summary

Establish the complete engineering foundation for Atlas AI Trading OS: a modular monorepo
(Next.js frontend, FastAPI backend, LangGraph-ready AI platform), event-driven communication
over Kafka with retry/DLQ/replay, shared platform services (logging, config, cache, secrets,
metrics, storage, flags), zero-trust security seams, full observability (OpenTelemetry +
Prometheus/Grafana/Loki/Tempo), containerized local development via Docker Compose, and a
Kubernetes + Terraform deployment path — with no trading, auth, or agent features implemented.
This plan is the blueprint every future spec (01-Authentication onward) builds on.

## Technical Context

**Language/Version**: Python 3.12 (backend, AI platform), TypeScript 5.x / Node 22 LTS (frontend, shared TS packages)
**Primary Dependencies**: FastAPI + Pydantic v2, SQLAlchemy 2 (async) + Alembic, LangGraph/LangChain-core (interfaces only), Next.js 15 (App Router), Tailwind + shadcn/ui, TanStack Query, aiokafka, Celery + Celery Beat, OpenTelemetry SDKs
**Storage**: PostgreSQL 16 + pgvector (system of record + vectors), Redis 7 (cache, rate limits, realtime fan-out, Celery broker), S3-compatible object storage (MinIO locally), Kafka (event log)
**Testing**: pytest (+pytest-asyncio, testcontainers), Vitest + Testing Library, Playwright (E2E), Schemathesis (API contract), k6 (load), Bandit/Trivy/gitleaks (security)
**Target Platform**: Linux containers — Docker Compose locally, Kubernetes (managed, cloud-agnostic via Terraform + Helm) for dev/staging/production
**Project Type**: web (monorepo: frontend + backend + AI platform + infra)
**Performance Goals**: p95 < 1s for API requests (SC-003), 1,000 concurrent clients initially, horizontal scale to thousands (SC-004); event publish→consume p95 < 2s
**Constraints**: Zero silent event loss (SC-005); alerting on dependency failure < 60s (SC-007); flag propagation < 1 min (SC-008); no secrets in repo/images/logs (SC-009); stateless services by default
**Scale/Scope**: ~4 deployable units at foundation stage (web, api, worker, scheduler) + infra; 52 FRs; designed for years of module growth (agents, brokers, trading engine)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Compliance in this plan | Status |
|---|-----------|------------------------|--------|
| I | Human First | Foundation only; no automated actions. Flag kill-switches + audit trail give humans override control. | ✅ |
| II | Security First | TLS everywhere, secrets via env/secret manager (never client/repo), broker credentials server-side only (future), redaction in logging layer. | ✅ |
| III | Transparency | N/A at foundation (no recommendations yet); event/audit schemas carry evidence fields for future use. | ✅ |
| IV | Multi-Agent Collaboration | Agent/Tool/Prompt/Workflow registries + event bus designed as the coordination substrate; no agent autonomy implemented. | ✅ |
| V | Explainability | Correlation IDs + tracing + Langfuse-ready AI observability make every future decision reconstructable. | ✅ |
| VI | Risk Before Profit | N/A at foundation; error taxonomy + circuit breakers establish the "safe default = stop" machinery. | ✅ |
| VII | Continuous Learning | Event log + object storage provide the journaled history substrate; privacy scoping in memory interface. | ✅ |
| VIII | Privacy by Design | Per-user scoping in memory/data model; minimal collection; deletion supported in data model design. | ✅ |
| IX | Reliability (Fail Safe) | Timeouts mandatory, retries + circuit breakers, readiness-gated degradation, DLQ for poison events. | ✅ |
| X | Modular Architecture | Module boundaries + import-linter/dependency-cruiser enforcement; contracts-only interaction. | ✅ |
| XI | Observability | Structured logs, metrics, traces, dashboards, alerts are deliverables of this spec, not afterthoughts. | ✅ |
| XII | Scalability | Stateless services, Kafka consumer groups, HPA in Kubernetes, capacity assumptions stated. | ✅ |

**Gate result (pre-Phase-0)**: PASS — no violations. **Post-Phase-1 re-check**: PASS (design
artifacts introduce no new coupling; one complexity entry justified below).

## 1. Architecture Overview

### 1.1 System architecture

Atlas is a **modular monolith-first, service-ready** platform: a single FastAPI application
composed of strictly isolated modules behind one API layer, plus separate worker and
scheduler processes, communicating internally through an event bus. Modules can be promoted
to standalone services later without changing their contracts — the seams (events + typed
interfaces) exist from day one.

```text
┌────────────────────────────────────────────────────────────────────────┐
│ Clients: Web (Next.js) │ future: Mobile, WhatsApp, Desktop, 3rd-party │
└───────────────┬────────────────────────────────────────────────────────┘
                │ HTTPS (TLS, versioned REST /v1, WebSocket /ws)
┌───────────────▼───────────────┐
│ Edge: K8s Ingress (NGINX)     │  TLS termination, WAF headers, LB
└───────────────┬───────────────┘
┌───────────────▼───────────────────────────────────────────────────────┐
│ apps/api (FastAPI "gateway app")                                      │
│  middleware: authN/authZ seams · rate limit · validation · errors ·   │
│  correlation ID · security headers · OpenAPI                          │
│  ┌─────────┐ ┌─────────┐ ┌───────────────┐ ┌────────────────────┐    │
│  │ platform │ │ sample  │ │ ai-platform   │ │ future modules:    │    │
│  │ module   │ │ module  │ │ (registries,  │ │ auth, brokers,     │    │
│  │ (health, │ │ (proof) │ │  interfaces)  │ │ trading, journal…  │    │
│  │ flags,   │ └─────────┘ └───────────────┘ └────────────────────┘    │
│  │ admin)   │        modules talk ONLY via interfaces + events        │
│  └─────────┘                                                          │
└───────┬───────────────┬──────────────────────┬────────────────────────┘
        │               │                      │
┌───────▼──────┐ ┌──────▼───────┐   ┌──────────▼──────────┐
│ PostgreSQL16 │ │ Redis 7      │   │ Kafka (event bus)   │
│ + pgvector   │ │ cache·RL·rt  │   │ events·retry·DLQ    │
└──────────────┘ └──────────────┘   └──────────┬──────────┘
                                               │ consumer groups
                        ┌──────────────────────▼─────────────────────┐
                        │ services/worker (Celery + Kafka consumers) │
                        │ services/scheduler (Celery Beat)           │
                        └────────────────────────────────────────────┘
Observability plane: OpenTelemetry → Prometheus · Grafana · Loki · Tempo · Alertmanager
Object storage: S3/MinIO      Secrets: env → External Secrets Operator (cloud)
```

### 1.2 Layered architecture (per module)

```text
API layer (routers, request/response schemas)      ← HTTP only, no business logic
   ↓ depends on
Service layer (use cases, orchestration, events)   ← business rules live here
   ↓ depends on
Domain layer (entities, value objects, domain errors) ← pure, framework-free
   ↑ implemented by
Repository layer (SQLAlchemy, Redis, Kafka adapters)  ← I/O only, behind interfaces
```

**Dependency rules (enforced by import-linter / dependency-cruiser in CI):**

1. Dependencies point inward: API → Service → Domain; Repositories implement Domain-defined
   interfaces (ports & adapters).
2. A module may import another module ONLY via `modules/<name>/public.py` (its published
   interface) or by consuming its events. Importing another module's internals fails CI.
3. `shared/` packages may not import from any module. Modules may import `shared/`.
4. Frontend features may import `packages/*` and their own folder; cross-feature imports are
   linted out.

### 1.3 Service & module boundaries

Deployable units at foundation stage: `web` (Next.js), `api` (FastAPI), `worker`,
`scheduler`. Module boundaries inside `api`: `platform` (health, flags, admin, audit),
`sample` (throwaway proof module, removed later), `ai_platform` (registries + interfaces).
Each future capability (auth, brokers, trading, journal, notifications) becomes a new module
with its own router, services, domain, repositories, events, and tests.

### 1.4 Event-driven, API-first, AI-first, cloud-native

- **Event-driven**: state changes publish domain events to Kafka; consumers react. Commands
  use APIs; facts use events (see §7).
- **API-first**: every capability is exposed via versioned REST (`/v1/...`) with generated
  OpenAPI; the web app consumes the same API as any future client (see §4, contracts/).
- **AI-first**: the AI platform's registries, memory, model-provider, and workflow interfaces
  are first-class platform citizens with the same observability and security treatment
  (see §6).
- **Cloud-native**: 12-factor services, containers, config from env, stateless by default,
  health probes, horizontal scaling, IaC (see §10, §15–§17).

## 2. Technology Decisions

Full rationale, alternatives, and tradeoffs are in [research.md](./research.md). Summary:

| Area | Decision | Key alternatives rejected |
|------|----------|---------------------------|
| Frontend | Next.js 15 (App Router) + TypeScript + Tailwind + shadcn/ui + TanStack Query + Zustand | Remix, Vite SPA, Angular |
| Backend | Python 3.12 + FastAPI + Pydantic v2 | NestJS, Go (chi), Django |
| Database | PostgreSQL 16 (SQLAlchemy 2 async + Alembic) | MySQL, MongoDB, CockroachDB |
| Vector DB | pgvector extension (same Postgres) | Pinecone, Qdrant, Weaviate |
| Cache | Redis 7 | Memcached, Valkey-only path |
| Event bus | Apache Kafka (Redpanda single-binary for local dev) | Redis Streams, RabbitMQ, NATS JetStream |
| Background jobs | Celery 5 + Redis broker; Celery Beat for schedules | ARQ, Dramatiq, Temporal |
| Realtime | FastAPI WebSockets + Redis pub/sub fan-out; SSE fallback | Pusher/Ably, Socket.IO, Centrifugo |
| AI framework | LangGraph (+ LangChain-core) — interfaces only this spec | CrewAI, AutoGen, custom orchestrator |
| LLM gateway | LiteLLM (proxy mode) behind our ModelProvider interface | Direct SDKs per provider, OpenRouter |
| AI observability | Langfuse (self-hosted) wired via interface, enabled later | LangSmith, Phoenix |
| Auth (seams only) | OAuth2/OIDC-compatible JWT middleware seam; provider chosen in Spec 00 | — (deferred by design) |
| Feature flags | OpenFeature SDK + flagd provider | Unleash, LaunchDarkly, homegrown |
| Monitoring | OpenTelemetry → Prometheus, Grafana, Loki, Tempo, Alertmanager; Sentry for errors | Datadog, ELK |
| CI/CD | GitHub Actions; GHCR images; Helm deploy; ArgoCD in M6 | GitLab CI, Jenkins |
| Testing | pytest / Vitest / Playwright / Schemathesis / k6 | — |
| Object storage | S3-compatible API; MinIO locally | Cloud-specific SDK lock-in |
| Secrets | .env (local) → K8s External Secrets Operator + cloud secret manager | Vault self-hosted (revisit at scale) |
| Containers | Docker + Compose (local), multi-stage builds | Podman |
| Orchestration | Kubernetes (managed) + Helm + Terraform | ECS, Nomad, plain VMs |
| Cloud | Cloud-agnostic; first target any managed K8s (recommendation: start GKE or DO K8s for cost) | Hard-binding to one vendor |
| Monorepo tooling | pnpm + Turborepo (TS), uv workspaces (Python) | Nx, Bazel, Poetry |

## 3. Monorepo Structure

### Documentation (this feature)

```text
specs/001-platform-foundation/
├── plan.md              # This file
├── research.md          # Phase 0 — technology decisions & rationale
├── data-model.md        # Phase 1 — platform entities
├── quickstart.md        # Phase 1 — clone-to-running guide
├── contracts/           # Phase 1 — OpenAPI + event catalog
└── tasks.md             # Phase 2 (/sp.tasks — NOT created by /sp.plan)
```

### Source Code (repository root)

```text
atlas-ai-trading-os/
├── apps/                        # Deployable user-facing applications
│   ├── web/                     # Next.js 15 App Router frontend
│   │   └── src/
│   │       ├── app/             # routes, layouts, route groups
│   │       ├── features/        # feature-based UI modules
│   │       ├── components/      # app-local composition components
│   │       └── lib/             # app-local utilities (api client init, ws)
│   └── api/                     # FastAPI application (unified API layer)
│       └── src/atlas_api/
│           ├── main.py          # app factory, middleware stack
│           ├── middleware/      # correlation, errors, rate-limit, security headers, auth seam
│           └── modules/         # ← module homes (platform/, sample/, ai_platform/)
│               └── <module>/
│                   ├── public.py        # ONLY legal cross-module import surface
│                   ├── router.py        # API layer (versioned)
│                   ├── schemas.py       # request/response models
│                   ├── service.py       # service layer
│                   ├── domain/          # entities, value objects, errors
│                   ├── repository/      # DB/cache/bus adapters
│                   └── events.py        # events this module publishes/consumes
├── services/                    # Non-HTTP deployable units
│   ├── worker/                  # Celery app + Kafka consumers (retry/DLQ handling)
│   └── scheduler/               # Celery Beat schedules + missed-run policies
├── agents/                      # FUTURE agent implementations (empty scaffold + README now)
├── packages/                    # Shared TypeScript packages
│   ├── ui/                      # design system / component library (shadcn-based)
│   ├── api-client/              # generated typed client from OpenAPI
│   └── config/                  # shared TS configs (eslint, tsconfig, tailwind preset)
├── shared/                      # Shared Python packages (uv workspace members)
│   ├── atlas_core/              # config loading, errors taxonomy, result types, ids/correlation
│   ├── atlas_events/            # event envelope, publisher/subscriber, idempotency, registry
│   ├── atlas_observability/     # logging, metrics, tracing setup (OTel)
│   └── atlas_ai/                # AI platform interfaces + in-memory reference impls
├── infra/
│   ├── docker/                  # Dockerfiles, compose files, .env.example
│   ├── k8s/                     # Helm charts (atlas-api, atlas-web, worker, scheduler)
│   └── terraform/               # cluster, DB, Redis, Kafka, secrets, DNS per environment
├── docs/                        # architecture docs, runbooks, onboarding, ADR index
├── specs/                       # SDD feature specs (this directory tree)
├── scripts/                     # dev tooling: bootstrap, db, lint-all, generate-client
├── tests/                       # cross-cutting suites: e2e/ (Playwright), load/ (k6), contract/
├── history/                     # PHRs + ADRs
├── .github/workflows/           # CI/CD pipelines
├── turbo.json · pnpm-workspace.yaml · package.json
└── pyproject.toml               # uv workspace root
```

**Structure Decision**: Web-application monorepo (Option 2 extended). `apps/` = deployables
with UIs/APIs; `services/` = headless deployables; `shared/` = Python libraries; `packages/`
= TypeScript libraries; `agents/` reserved to keep future agent code out of the API app;
`tests/` holds only cross-cutting suites (module tests live beside their module).

## 4. Backend Architecture

- **App factory & DI**: `create_app()` assembles middleware and mounts module routers.
  Dependency injection uses FastAPI `Depends` with provider functions defined per module
  (`deps.py`); no global singletons — session, cache, publisher, settings are injected,
  making every layer testable. A lightweight container (plain module-level providers) is
  preferred over a DI framework until proven insufficient.
- **Modules**: each module owns router → service → domain → repository as in §1.2, plus its
  event definitions and Alembic migration branch. Modules register with the app via a
  `ModuleDef` (name, router, event subscriptions, health dependencies) — adding a module is
  additive only (FR-003).
- **Service layer**: orchestrates use cases; the only layer that both calls repositories and
  publishes events; transactional boundary (unit-of-work) lives here.
- **Repository layer**: async SQLAlchemy repositories implementing domain-defined protocols;
  Redis and Kafka adapters follow the same port/adapter pattern.
- **Domain layer**: Pydantic-free pure dataclasses/value objects where practical; domain
  errors from the shared taxonomy (§11).
- **API layer**: thin routers; Pydantic v2 schemas validate 100% of input (FR-010); versioned
  under `/v1`; OpenAPI generated and published (FR-013).
- **Background workers**: `services/worker` runs (a) Celery tasks for imperative jobs and
  (b) aiokafka consumer groups for event subscriptions, both reusing module service code via
  `public.py` imports. Task states persisted (FR-028/029).
- **Scheduling**: Celery Beat with schedules declared in code + per-job missed-run policy
  (`catch_up: once | skip`) recorded in the ScheduledJob entity (FR-027).
- **Configuration & validation**: `atlas_core.config` — Pydantic Settings, fail-fast on
  missing/invalid values at startup with named-field errors (FR-006).
- **Shared utilities**: correlation ID context vars, clock abstraction (no naked
  `datetime.now()` in domain logic), pagination, idempotency helpers.

## 5. Frontend Architecture

- **Next.js App Router** with route groups: `(public)`, `(app)` (authenticated shell later),
  `(admin)` (platform admin: flags, DLQ, health). Server Components by default; Client
  Components only for interactivity.
- **Feature-based architecture**: `src/features/<feature>/{components,hooks,api,types}`;
  features are isolated the same way backend modules are (dependency-cruiser enforced).
- **Component library**: `packages/ui` wraps shadcn/ui + Tailwind tokens; app imports only
  from `@atlas/ui` — no raw copy-paste divergence. Storybook documents components.
- **Layouts**: root layout (theme, fonts, providers) → group layouts (app shell, admin
  shell); loading/error boundaries per route segment.
- **State management**: server state via TanStack Query (single source for API data, retry &
  cache policy centralized); client/UI state via Zustand slices per feature; no global Redux.
- **API layer**: `packages/api-client` generated from the backend OpenAPI on every contract
  change (CI job) — type drift between front and back is a build failure, not a runtime bug.
- **Realtime**: thin WebSocket client with auto-reconnect + resubscribe + server sequence
  numbers for resynchronization (edge case: real-time disconnects); falls back to SSE.
- **Theme system**: CSS variables + Tailwind design tokens in `packages/ui`; light/dark from
  day one; no hardcoded colors in features.

## 6. AI Platform Foundation (interfaces only)

All contracts live in `shared/atlas_ai` with in-memory reference implementations + contract
tests (FR-026). No agent logic, no live model calls in this spec.

- **Agent Registry**: register/discover `AgentDefinition` (id, name, version, capabilities,
  allowed tools, status: registered|active|suspended). Backed by Postgres later; in-memory now.
- **Tool Registry**: `ToolDefinition` (name, version, JSON-schema input/output, required
  permissions, rate class). Tools are the ONLY way future agents touch the platform — same
  zero-trust posture as human clients.
- **Prompt Registry**: named, semver-versioned prompts with metadata (owner, intended model,
  eval status); immutable versions; `get(name, version|latest-stable)`.
- **Workflow Registry**: named LangGraph graph definitions with version + checkpoint policy;
  interface exposes `run/pause/resume/cancel` semantics and failure states (FR-025) without
  binding callers to LangGraph types.
- **Memory Interface**: `MemoryStore.read/write/search/delete(scope)` where scope =
  (user_id, agent_id, kind: short_term|long_term); per-user isolation is part of the contract
  (Principle VIII); pgvector-backed implementation arrives with the first real agent spec.
- **Model Provider Interface**: `complete/stream/embed` with model alias routing (e.g.
  `reasoning-large` → provider model) resolved via LiteLLM config; providers swappable
  without agent changes (FR-024). Budget/timeout/retry policy declared per alias.
- **Agent communication**: agents never call each other directly — they publish/consume
  events and are orchestrated by future Manager-Agent workflows (Constitution IV).
- **Agent configuration**: per-agent config schema validated like service config; secrets
  never inline.
- **Shared AI utilities**: token counting, redaction-before-logging, structured
  trace emission (Langfuse-compatible) behind an interface.

## 7. Event System

- **Envelope** (see contracts/platform-events.md): `event_id (UUIDv7)`, `event_type`,
  `schema_version`, `occurred_at`, `correlation_id`, `causation_id`, `producer`, `payload`.
- **Naming**: `atlas.<domain>.<entity>.<action>` past tense — e.g. `atlas.platform.module.registered`,
  future `atlas.auth.user.created`, `atlas.trading.trade.opened`. Topics map 1:1 to
  `atlas.<domain>` with type-based routing inside.
- **Versioning**: additive changes bump minor (compatible); breaking changes create
  `<event_type>.v2` alongside v1 with a documented migration window; schemas registered in
  the event catalog (FR-019) and checked in CI (compat test).
- **Publishers**: only service layers publish, via `atlas_events.Publisher` (outbox pattern:
  events written in the same DB transaction as state, relayed to Kafka by the worker —
  guarantees no lost/phantom events).
- **Subscribers**: declared in `ModuleDef`; consumer groups per (module, event_type);
  handlers MUST be idempotent — the envelope's `event_id` + a processed-events table give
  exactly-once *effect* on top of at-least-once delivery.
- **Retries**: exponential backoff with jitter — retry topics `…retry.1m`, `…retry.10m`,
  then `atlas.dlq.<domain>` after N attempts (default 5).
- **DLQ**: dead-lettered events persist with failure reason + attempt history (FR-016);
  admin API supports inspect + re-drive (FR-017); DLQ depth is an alerted metric.
- **Replay**: Kafka retention 30 days (assumption in spec); admin-triggered replay by
  type/time-range publishes to a `…replay` topic consumed only by designated subscribers;
  envelope gains `replay_of` marker so handlers can distinguish (FR-018).
- **Correlation**: correlation_id propagated from edge → events → tasks (FR-034); clock-skew
  tolerated by ordering on Kafka offsets, never wall clocks.

## 8. Shared Platform Services

| Service | Design |
|---|---|
| Logging | `atlas_observability.get_logger()` — structlog JSON to stdout; fields: ts, service, severity, correlation_id, request_id, user_id?; redaction filter for secret-shaped values (FR-037); per-service rate cap prevents log flooding |
| Metrics | OTel metrics → Prometheus; RED metrics auto-instrumented per route/consumer/task; custom counters via one helper |
| Tracing | OTel traces → Tempo; auto-instrument FastAPI, SQLAlchemy, Redis, aiokafka, httpx; baggage carries correlation_id |
| Caching | `atlas_core.cache` — Redis wrapper with namespaced keys, TTL required (no immortal keys), stampede protection (single-flight) |
| Storage | S3 interface (`put/get/presign/delete`); MinIO locally; bucket-per-concern |
| Notifications | Interface only this spec: `Notifier.send(channel, template, payload)` with a logging stub implementation |
| Secrets | `atlas_core.secrets` — reads env (local) / mounted secrets (K8s); modules never read `os.environ` directly |
| Configuration | Pydantic Settings per service + shared base; see §10 |
| Health | `/v1/health/live` (process up) and `/v1/health/ready` (dependencies: db, redis, kafka — each reported with status + latency) (FR-032) |
| Rate limiting | Redis sliding-window per client key at middleware; per-route overrides; standard 429 + Retry-After (FR-011); abusive clients isolated by key |
| Search | Postgres FTS now; interface allows OpenSearch later — no work this spec beyond the seam |

## 9. Security Foundation

- **AuthN boundary**: middleware seam validates bearer tokens on every non-public route;
  until Spec 01, non-production uses an explicit `DevIdentityProvider` (header-based, refuses
  to load if `ENV=production`) — no route can silently opt out (FR-009/045).
- **AuthZ boundary**: routes declare `required_permissions=[...]` metadata now; enforcement
  activates with Spec 01 RBAC; registry of permissions lives in the platform module (FR-046).
- **Zero trust**: every request authenticated + authorized regardless of network origin;
  internal service-to-service calls (worker→api if ever needed) use short-lived service
  tokens (K8s service account JWTs), not network trust.
- **Secrets**: never in repo (gitleaks in CI), never in images (Trivy scan), never in logs
  (redaction filter); local `.env` from `.env.example`; cloud via External Secrets Operator.
- **Encryption**: TLS at ingress + internal mTLS optional flag (enable when multi-service);
  Postgres/Redis/Kafka encryption-at-rest via cloud volumes; column-level encryption helper
  in `atlas_core` for future broker credentials (Constitution II).
- **Audit logging**: append-only `audit_log` table via `AuditLogger.record(actor, action,
  target, correlation_id)`; flag changes, DLQ re-drives, replays, config-affecting admin
  actions all audited (FR-047).
- **API hardening**: strict Pydantic validation (reject unknown fields on writes), CORS
  allowlist per environment, security headers middleware (HSTS, CSP for web, X-Content-Type-
  Options, frame-ancestors none), request size limits, 429 rate limits (FR-048).

## 10. Configuration Strategy

- **Sources & precedence**: defaults (code) < env-specific values < environment variables <
  secrets mounts. One `Settings` class per service composing shared sections (db, redis,
  kafka, observability, flags).
- **Environments**: `local` (Compose), `development`, `staging`, `production` (K8s) —
  identical code/artifacts; only config differs (FR-005, spec US5). Config values documented
  in `.env.example` with placeholder-only values (FR-007).
- **Fail fast**: startup validates all required fields and dependency URLs; process exits
  non-zero naming the offending variable (FR-006). Security-relevant settings have NO
  defaults (must be explicit).
- **Testing**: test settings profile uses testcontainers endpoints; никогда production
  resources — guardrail: settings refuse `ENV=test` with production hostnames.
- **Feature flags**: OpenFeature SDK both backend + frontend; flagd sidecar/service reads a
  versioned flag config (GitOps) → change lands < 1 min without deploy (SC-008); every flag
  declares a safe default used when flagd is unreachable (FR-040); flag changes audited.

## 11. Error Handling Strategy

- **Hierarchy** (`atlas_core.errors`): `AtlasError` → `ValidationError`,
  `AuthenticationError`, `AuthorizationError`, `NotFoundError`, `ConflictError`,
  `RateLimitedError`, `DependencyUnavailableError`, `InternalError` (FR-039). Each maps to a
  stable machine code (`ATLAS-VAL-001` style), HTTP status, and default user-safe message.
- **API envelope** (contracts/): `{ "error": { "code", "message", "correlation_id",
  "details"? } }` — never stack traces or internals (FR-038); unhandled exceptions become
  `InternalError` + Sentry event + ERROR log with full context server-side.
- **Retry policy**: outbound calls wrapped in tenacity policies — idempotent operations
  retry 3× exponential+jitter; non-idempotent never auto-retry. Event consumers per §7.
- **Timeouts**: every outbound call has an explicit timeout (FR-041); defaults: HTTP 10s,
  DB statement 30s, Redis 2s, Kafka produce 10s; no infinite waits pass review.
- **Circuit breakers**: per-dependency breaker (aiobreaker) — open after 5 consecutive
  failures, half-open probe after 30s; open breaker → `DependencyUnavailableError` →
  degraded-mode response + readiness reflects it (FR-042, Constitution IX).
- **Graceful degradation**: read paths serve cached data with staleness marker where safe;
  write paths fail explicitly — never silently queue user-facing writes.

## 12. Observability

- **Logging/tracing/metrics**: as §8; single OTel bootstrap called by every entrypoint.
- **Dashboards** (Grafana, provisioned as code in `infra/`): API overview (RED per route),
  Event bus (lag, throughput, retry rate, DLQ depth), Workers (task states, duration),
  Scheduler (last-run per job, missed runs), Infrastructure (DB/Redis/Kafka saturation).
- **Alerts** (Alertmanager, as code): API 5xx > 1% 5m; p95 > 1s 10m; readiness failing 60s
  (SC-007); DLQ depth > 0 for 10m; consumer lag growing 15m; scheduler job missed; cert
  expiry; disk pressure. Every alert names a runbook page in `docs/runbooks/`.
- **Health endpoints**: §8; K8s probes wired to them.
- **AI workflow monitoring**: trace emission interface in `atlas_ai` (Langfuse-compatible)
  so every future agent step/tool call/token count is captured from the first agent onward
  (Constitution V/XI); no-op exporter this spec.
- **Performance monitoring**: k6 baseline scenario committed; performance budget checked in
  CI against staging weekly (p95 < 1s @ 1k VU — SC-003).

## 13. Testing Strategy

| Layer | Tooling | Gate |
|---|---|---|
| Unit (Py) | pytest + pytest-asyncio; domain/services with fakes for ports | PR-blocking; coverage ≥ 80% on shared/ + modules |
| Unit (TS) | Vitest + Testing Library on packages/ui + features | PR-blocking |
| Integration | testcontainers (Postgres, Redis, Redpanda); repository + consumer tests against real deps | PR-blocking |
| Contract | Schemathesis fuzzes implemented API against OpenAPI; event schema compat tests; `atlas_ai` interface contract suite runs against every implementation (FR-026, FR-050) | PR-blocking |
| E2E | Playwright: health, sample module flow, flag toggle, admin DLQ view | main-branch + nightly |
| Load | k6: 1k VU baseline; publish→consume latency scenario | staging, weekly + pre-release |
| Security | Bandit, npm audit/pnpm audit, gitleaks, Trivy (fs + image), ZAP baseline vs staging | PR (static) / nightly (dynamic) |
| AI workflow | Contract tests only this spec (stub registries/memory/provider); eval harness arrives with first agent spec | PR-blocking |
| Infrastructure | `helm template` + kubeconform; `terraform validate/plan` in CI; Compose smoke boot test | PR-blocking |

## 14. CI/CD Pipeline

- **Git strategy**: trunk-based; short-lived feature branches `NNN-name` (SDD) → PR → squash
  merge to `main`; `main` always deployable; releases tagged `vX.Y.Z`.
- **PR pipeline** (GitHub Actions, path-filtered via Turborepo/uv): lint (ruff, eslint,
  prettier check, import-linter, dependency-cruiser) → typecheck (mypy --strict on shared/,
  tsc) → unit + integration + contract tests → security static scans → build images →
  `helm template` validation. All gates block merge (FR-051).
- **Main pipeline**: build + push images (GHCR, tagged sha + semver) → deploy to
  `development` automatically → smoke tests → manual promotion to `staging` → E2E + load →
  manual promotion to `production`.
- **Rollback**: Helm rollback to previous release (one command, documented runbook); DB
  migrations must be backward-compatible one version (expand→migrate→contract pattern).
- **Release strategy**: continuous to dev; batched promotions with release notes generated
  from conventional commits; production deploys behind flags where risk exists. ArgoCD
  (GitOps pull model) adopted in M6 once cluster count justifies it.

## 15. Docker Strategy

- **Images**: one per deployable (`web`, `api`, `worker`, `scheduler`); multi-stage builds
  (builder → slim runtime); non-root user; read-only rootfs; pinned base digests;
  `.dockerignore` aggressive; target < 300MB (api) / < 200MB (web standalone).
- **Local development**: `docker compose up` starts postgres+pgvector, redis, redpanda,
  minio, flagd, grafana/prom/loki/tempo (optional profile), api, worker, scheduler, web —
  with hot-reload volume mounts for api/web (SC-002: < 30 min clone-to-running).
- **Compose files**: `compose.yaml` (core deps) + `compose.dev.yaml` (apps, hot reload) +
  `compose.observability.yaml` (optional profile) — documented in quickstart.md.
- **Networking**: single compose network; only web (3000) and api (8000) published to host;
  infra reachable by service name.
- **Volumes**: named volumes for pg/kafka/minio data; `scripts/dev-reset` wipes clean.
- **Optimization**: layer-cache-friendly ordering (deps before source), uv/pnpm lockfile
  caching in CI, buildkit cache mounts.

## 16. Kubernetes Strategy

- **Namespaces**: `atlas-dev`, `atlas-staging`, `atlas-prod` (+ `observability`,
  `platform-system` for flagd/ESO); NetworkPolicies default-deny between namespaces.
- **Workloads**: Deployments for api/web/worker/scheduler (scheduler: 1 replica + leader
  election; workers: per-queue Deployments later); probes = health endpoints; resource
  requests/limits mandatory; PodDisruptionBudgets for api/web.
- **Services/Ingress**: ClusterIP services; NGINX Ingress + cert-manager (Let's Encrypt);
  one host per environment; WebSocket-aware annotations.
- **Secrets**: External Secrets Operator syncing from cloud secret manager → K8s Secrets;
  no secret in Helm values files.
- **Autoscaling**: HPA on api/web (CPU + RPS custom metric) and workers (Kafka consumer lag
  via KEDA); cluster autoscaler on.
- **Persistent storage**: managed Postgres/Redis/Kafka preferred over in-cluster; if
  in-cluster (dev), StatefulSets + SSD storage class; object storage always external.
- **Monitoring**: kube-prometheus-stack; the dashboards/alerts from §12 shipped via Helm
  values as code.

## 17. Infrastructure Architecture

- **Edge/API gateway**: NGINX Ingress terminates TLS; FastAPI gateway app owns app-level
  gateway concerns (authN seam, rate limit, validation, versioning) — a dedicated gateway
  product (Kong) is deliberately deferred until multi-service reality demands it.
- **PostgreSQL 16 + pgvector**: single primary + read replica (staging/prod); PITR backups
  (daily base + WAL, 30-day window); restore drill quarterly runbook.
- **Redis 7**: managed, single shard + replica; separate logical DBs for cache / rate-limit /
  celery / realtime.
- **Kafka**: 3 brokers (prod) or Redpanda dev-mode single node (local/dev); topics
  provisioned via IaC with retention/partitions declared per topic in the event catalog.
- **Workers/AI services**: worker + scheduler Deployments now; `agents/` deployables get
  their own Deployment pattern (GPU node pool option documented) in future specs.
- **Monitoring stack**: kube-prometheus-stack + Loki + Tempo (S3-backed) + Grafana +
  Alertmanager → on-call notification channel.
- **Storage/CDN**: S3 buckets (uploads, artifacts, loki/tempo chunks); web static assets via
  Next.js standalone behind CDN (CloudFront/Cloudflare) when public traffic warrants.
- **IaC**: Terraform modules per environment (cluster, db, redis, kafka, buckets, secrets,
  DNS); state in remote backend with locking; `terraform plan` in CI on infra PRs.

## 18. Coding Standards

- **Python**: ruff (lint+format), mypy --strict on `shared/` and module service/domain
  layers; no bare `except`; all I/O async; public functions typed + docstrings (Google
  style); import-linter contracts enforce §1.2 rules.
- **TypeScript**: strict tsconfig; eslint (typescript-eslint, react-hooks, boundaries
  rule) + prettier; no `any` without inline justification; zod at runtime boundaries.
- **Naming**: Python `snake_case` / TS `camelCase`; folders kebab-case (TS) and snake_case
  (Py packages); events per §7; API: plural nouns, kebab-case paths (`/v1/feature-flags`),
  no verbs in resource paths; DB snake_case tables singular module prefix.
- **Documentation**: every module has README (purpose, public interface, events, owner);
  OpenAPI descriptions mandatory per route; docs/ holds architecture + runbooks; ADRs in
  `history/adr/` for significant decisions.
- **Commits**: Conventional Commits (`feat(api): …`, `fix(events): …`); commitlint in CI;
  PR template requires spec/task reference and constitution check.
- **Architecture rules**: SOLID; Clean Architecture dependency rule (§1.2); DDD-lite —
  entities/value objects/domain events per module without over-modeling; YAGNI enforced in
  review — the platform stays smallest-viable (Constitution/CLAUDE default policies).

## 19. Development Roadmap

| M | Goal | Key deliverables | Depends on | Complexity | Top risk | Acceptance |
|---|------|------------------|------------|-----------|----------|------------|
| M1 | Repo & toolchain skeleton | Monorepo layout (§3), uv+pnpm+turbo, lint/type/test harness, CI PR pipeline, pre-commit, .env.example, CODEOWNERS | — | Medium | Tooling friction on Windows dev machines → document WSL2 path | Fresh clone → `pnpm i && uv sync` → all linters/tests green in CI |
| M2 | Compose dev environment | Dockerfiles ×4, compose files, MinIO/Redpanda/flagd wiring, scripts/bootstrap + dev-reset, quickstart.md validated | M1 | Medium | Compose drift vs K8s parity → same images both places | SC-002: clone → running platform < 30 min; smoke boot test in CI |
| M3 | API core + platform module | App factory, middleware stack (correlation, errors, rate limit, security headers, auth seam + DevIdentityProvider), config fail-fast, health endpoints, error envelope, OpenAPI publish, sample module | M2 | High | Middleware ordering subtleties → integration tests per middleware | US1/US4 acceptance scenarios pass; Schemathesis green; FR-005..013, 038..048 seams demo'd |
| M4 | Event system | atlas_events (envelope, outbox publisher, consumer runtime, idempotency store), retry topics + DLQ + re-drive admin API, replay mechanism, event catalog + compat CI, worker + scheduler services with ScheduledJob/BackgroundTask persistence | M3 | High | Outbox relay throughput; DLQ edge cases → chaos tests with poison events | US2 scenarios pass incl. poison-event and replay tests; SC-005 zero silent loss demonstrated |
| M5 | Observability + flags + AI interfaces | OTel bootstrap everywhere, Grafana dashboards + alert rules as code, log redaction, audit log, OpenFeature+flagd, `atlas_ai` interfaces + in-memory impls + contract tests, frontend shell (Next.js app + packages/ui + generated client + ws client) | M3 (M4 for event dashboards) | High | Alert noise tuning; flag UX | US3/US6 scenarios pass; SC-006 5-min trace reconstruction; SC-007 60s alert; SC-008 1-min flag |
| M6 | Cloud deployment | Terraform envs, Helm charts, ESO secrets, ingress+TLS, HPA/KEDA, kube-prometheus-stack, main-branch CD to dev + promotion flow, rollback runbook, k6 baseline vs staging | M2–M5 | High | Cloud cost creep; secret sync misconfig | US5 scenarios pass; SC-003/004 load results recorded; SC-009 scans clean; deploy+rollback drill executed |

Exit criteria for Spec 00 overall = all SC-001..011 verified + Spec 01 unblocked (SC-011).

## 20. Risks

| Risk | Type | Impact | Mitigation |
|------|------|--------|-----------|
| Kafka operational burden before team has ops maturity | Technical/Infra | Dev slowdown, outages | Redpanda locally, managed Kafka in cloud; event abstraction allows brokerless test mode; runbooks + alerts from day one |
| Modular monolith erodes into big ball of mud | Technical | Future extraction impossible | import-linter CI contracts, `public.py`-only imports, module READMEs with owners, architecture tests |
| Outbox/consumer bugs cause duplicate side effects | Technical | Data corruption | Idempotency store + contract tests + chaos suite (duplicate/poison/replay) in M4 acceptance |
| Foundation over-engineering delays first user value | Operational | Runway burn | Milestones each end in demo-able acceptance; YAGNI in review; defer Kong/Vault/ArgoCD/multi-region explicitly |
| Cloud cost creep (K8s + managed services) | Operational | Budget | Start 1 small cluster + managed lowest tiers; cost dashboard; monthly review; local-first dev |
| Secrets/config misconfiguration across 4 envs | Security | Credential leak, outage | ESO single source, no secrets in Helm values, gitleaks/Trivy gates, fail-fast config, SC-009 scans |
| Auth seam design conflicts with Spec 01 choice | Security | Rework | Seam is OIDC/JWT-standard middleware with narrow interface; Spec 01 review of seam before M3 merge completes |
| WebSocket scale-out state (sticky sessions) | Scalability | Realtime degradation | Redis pub/sub fan-out keeps ws nodes stateless; sequence-number resync protocol; load test in M6 |
| LLM/vendor churn invalidates AI interfaces | AI | Interface rework | Interfaces model capabilities (complete/stream/embed, registries) not vendors; LiteLLM aliasing isolates model names; contract tests catch drift |
| pgvector performance ceiling at large embedding scale | AI/Future | Slow retrieval | Acceptable to thousands-user target; interface allows dedicated vector DB swap; benchmark gate before first heavy-RAG spec |
| Single-cluster blast radius | Infra/Future | Full outage | PDBs + HPA + managed DB PITR now; multi-AZ node pools; multi-region explicitly future scope |
| Observability data volume costs | Operational | Cost, noise | Sampling on traces (parent-based 10% prod), log rate caps, retention tiers (7d logs dev / 30d prod) |

## Complexity Tracking

> Constitution Check passed; one deliberate complexity choice recorded:

| Violation/Choice | Why Needed | Simpler Alternative Rejected Because |
|-----------------|------------|--------------------------------------|
| Kafka event bus at foundation stage (vs Redis Streams) | Replay, 30-day retained event log, multi-consumer groups, and DLQ semantics are spec requirements (FR-014..019) that future agents depend on; migrating an event backbone later is the costliest possible retrofit | Redis Streams handles pub/sub + consumer groups but replay/retention/schema-registry story is weak at "thousands of users, years of evolution" scale; a later Redis→Kafka migration would touch every module |
| Modular monolith instead of microservices | Small team, one deployable API keeps velocity; seams (events + public.py) preserve extraction path | Microservices now would multiply operational surface (N pipelines, N on-call surfaces) before any feature exists — rejected as premature |

---

**Phase 0 output**: [research.md](./research.md) · **Phase 1 outputs**:
[data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)
