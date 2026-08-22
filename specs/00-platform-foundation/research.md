# Phase 0 Research: Technology Decisions — Platform Foundation

**Feature**: 00-platform-foundation | **Date**: 2026-08-04
**Method**: Each area below records Decision / Rationale / Alternatives considered /
Tradeoffs accepted. All NEEDS CLARIFICATION items from Technical Context: **none remained**
(the user's plan input fixed the stack: FastAPI, Next.js, LangGraph, Kafka, Redis,
PostgreSQL + pgvector, Docker, Kubernetes); research below validates those mandates and
resolves the genuinely open choices (jobs runtime, flags, LLM gateway, monorepo tooling,
secrets, realtime fan-out, CI/CD shape).

## 1. Frontend — Next.js 15 (App Router) + TypeScript + Tailwind + shadcn/ui + TanStack Query + Zustand

- **Decision**: Next.js App Router, Server Components by default; shadcn/ui on Tailwind as
  the component base in `packages/ui`; TanStack Query for server state; Zustand for UI state.
- **Rationale**: Mandated by project vision; App Router gives layouts/streaming/route groups
  matching our admin/app shells; shadcn/ui gives owned-source components (no library lock-in)
  fitting a long-lived design system; TanStack Query centralizes caching/retry consistent
  with our API-first client generation.
- **Alternatives**: Remix (smaller ecosystem for our team), Vite SPA (loses SSR/streaming and
  standalone server output for K8s), Angular (team skill mismatch, heavier).
- **Tradeoffs**: App Router server/client mental model has a learning curve; RSC caching
  requires explicit discipline (documented in frontend standards).

## 2. Backend — Python 3.12 + FastAPI + Pydantic v2

- **Decision**: Single FastAPI app as unified API layer; async throughout; Pydantic v2 for
  validation/settings.
- **Rationale**: Mandated; best-in-class fit with the AI ecosystem (LangGraph is Python);
  OpenAPI generation satisfies API-first (FR-013); Pydantic v2 performance is adequate for
  p95 < 1s targets.
- **Alternatives**: NestJS (TS symmetry but splits AI stack across languages), Go (raw
  performance but AI ecosystem gap + team velocity), Django (batteries but sync-first ORM
  and heavier coupling).
- **Tradeoffs**: Python GIL limits per-process CPU parallelism → we scale horizontally
  (uvicorn workers + HPA), acceptable for I/O-bound API work.

## 3. Database — PostgreSQL 16 + SQLAlchemy 2 (async) + Alembic

- **Decision**: Postgres as the single system of record; async SQLAlchemy repositories;
  Alembic migrations with expand→migrate→contract discipline.
- **Rationale**: Mandated; ACID + JSONB + FTS + pgvector in one engine keeps the foundation
  small; SQLAlchemy 2 typed API aligns with mypy --strict.
- **Alternatives**: MySQL (weaker JSON/extension story), MongoDB (no cross-entity
  transactions fit for financial audit trails), CockroachDB (premature global scale).
- **Tradeoffs**: Single-writer primary is a known ceiling — read replicas + partitioning are
  the documented path before any sharding conversation.

## 4. Vector store — pgvector (in Postgres)

- **Decision**: pgvector extension in the same Postgres, behind the `MemoryStore`/search
  interfaces.
- **Rationale**: Zero extra infrastructure at foundation stage; transactional co-location of
  vectors with entities; interface allows swap-out.
- **Alternatives**: Qdrant/Weaviate (better ANN at big scale — premature), Pinecone (managed
  cost + data-residency coupling).
- **Tradeoffs**: HNSW in pgvector is fine to low-millions of vectors; a benchmark gate is
  required before the first heavy-RAG feature (recorded in plan §20 risks).

## 5. Cache — Redis 7

- **Decision**: Managed Redis; namespaced logical usage: cache, rate-limit counters, Celery
  broker/result, realtime pub/sub.
- **Rationale**: One battle-tested in-memory system covers four platform needs; sliding-
  window rate limiting and single-flight cache patterns are well known.
- **Alternatives**: Memcached (cache-only, no pub/sub/streams), Valkey (viable; Redis-
  compatible so a later switch is trivial — not a blocking decision).
- **Tradeoffs**: Redis as Celery broker is at-least-once with visibility-timeout caveats —
  acceptable because domain events (the correctness-critical path) ride Kafka, not Celery.

## 6. Event bus — Apache Kafka (Redpanda for local dev)

- **Decision**: Kafka semantics as the event backbone; Redpanda single-binary in Compose for
  dev parity (Kafka-API compatible); managed Kafka in cloud.
- **Rationale**: Spec requires retained event history, replay, consumer groups, DLQ
  (FR-014..019); Kafka's log model natively provides retention + replay + offset-based
  ordering; consumer-group scaling matches "agents react to events" vision.
- **Alternatives**: Redis Streams (weak replay/retention/schema story at target scale),
  RabbitMQ (queue semantics, replay bolt-on), NATS JetStream (lighter ops, but smaller
  ecosystem and team familiarity; revisit if Kafka ops cost bites).
- **Tradeoffs**: Highest operational complexity of the alternatives — mitigated by Redpanda
  locally, managed service in cloud, and the outbox/consumer abstractions in `atlas_events`
  so application code never touches Kafka APIs directly. Recorded in Complexity Tracking.

## 7. Background jobs & scheduling — Celery 5 + Celery Beat (Redis broker)

- **Decision**: Celery for imperative background tasks and Beat for cron-style schedules;
  domain-event consumption handled by aiokafka consumers in the same worker deployable.
- **Rationale**: Mature, well-documented, supports retries/acks-late/task states we must
  persist (FR-027..029); Beat covers minute/hour/day/week cadences with our own
  missed-run-policy wrapper.
- **Alternatives**: ARQ (async-native, but thin ecosystem/monitoring), Dramatiq (clean but
  smaller community), Temporal (superb durability — adopt later for complex agent workflows
  if LangGraph checkpointing proves insufficient; too heavy for foundation).
- **Tradeoffs**: Celery is sync-first — CPU-light I/O tasks use a threads pool; the
  correctness-critical event path deliberately does NOT depend on Celery.

## 8. Realtime — FastAPI WebSockets + Redis pub/sub fan-out (SSE fallback)

- **Decision**: WS endpoint in the api app; Redis pub/sub distributes messages to all api
  replicas so any pod can serve any client (stateless scale-out); server-side sequence
  numbers enable reconnect-resync.
- **Rationale**: No extra vendor; satisfies FR-030 including reconnection semantics; scales
  with HPA because no sticky sessions are required.
- **Alternatives**: Centrifugo (great, but another service to run before needed),
  Socket.IO (protocol lock-in), Pusher/Ably (vendor cost + data path exit).
- **Tradeoffs**: Redis pub/sub is fire-and-forget — missed messages during disconnect are
  recovered via the resync-by-sequence protocol, not the transport.

## 9. AI framework — LangGraph (+ LangChain-core), interfaces only

- **Decision**: LangGraph is the intended workflow engine; this spec ships only the
  `WorkflowEngine`, registry, memory, and model-provider interfaces with in-memory
  reference implementations — no LangGraph runtime dependency in production code yet.
- **Rationale**: Mandated by vision; graph model with checkpointing matches Manager-Agent
  orchestration (Constitution IV); wrapping it behind our interfaces keeps agents decoupled
  from framework churn.
- **Alternatives**: CrewAI (higher-level, less control), AutoGen (research-flavored API
  instability), custom orchestrator (reinventing checkpointing/state machines).
- **Tradeoffs**: LangGraph API still evolves — hence interface-first now, binding at first
  agent spec.

## 10. LLM gateway — LiteLLM behind our ModelProvider interface

- **Decision**: LiteLLM (library/proxy) implements the `ModelProvider` port; model aliases
  (`reasoning-large`, `fast-cheap`, `embed-default`) map to concrete models in config.
- **Rationale**: One integration surface for many providers; native cost/limit tracking;
  alias indirection means agents never name vendor models (FR-024).
- **Alternatives**: Direct provider SDKs (N integrations, N retry policies), OpenRouter
  (external dependency on the hot path + data egress).
- **Tradeoffs**: Extra hop/abstraction; acceptable because it is config-local and the
  interface allows bypass for a specific provider if ever needed.

## 11. AI observability — Langfuse (self-hosted), seam only this spec

- **Decision**: Trace-emission interface in `atlas_ai` shaped to Langfuse's model; no-op
  exporter until first agent.
- **Alternatives**: LangSmith (SaaS coupling), Arize Phoenix (eval-centric).
- **Tradeoffs**: None at this stage — pure seam.

## 12. Authentication — deferred to Spec 01; OIDC/JWT-standard seam now

- **Decision**: Middleware seam validating standard bearer JWTs + pluggable
  `IdentityProvider`; `DevIdentityProvider` for non-production only. No provider selection
  here (candidates for Spec 01: Better Auth, Auth.js, Keycloak, custom FastAPI JWT).
- **Rationale**: Spec 00 non-goal; seams keep every route protected-by-default (FR-009/045)
  without prejudging Spec 01.
- **Tradeoffs**: Slight risk of seam rework — mitigated by sticking to OIDC-shaped claims.

## 13. Feature flags — OpenFeature SDK + flagd

- **Decision**: OpenFeature (CNCF standard API) in backend + frontend; flagd as the
  provider, flags defined in a GitOps-versioned config file.
- **Rationale**: Vendor-neutral API (swap to Unleash/LaunchDarkly without touching call
  sites); flagd is tiny, self-hosted, file/GitOps-driven — flag change < 1 min (SC-008) with
  audit via git + audit log; safe defaults per flag (FR-040).
- **Alternatives**: Unleash (heavier server + DB to run now), LaunchDarkly (cost),
  homegrown table (reinvents targeting/rollouts, no ecosystem).
- **Tradeoffs**: flagd targeting is simpler than commercial tools — sufficient for
  env/user-percentage targeting needed in the next year.

## 14. Monitoring — OpenTelemetry + Prometheus/Grafana/Loki/Tempo + Sentry

- **Decision**: OTel as the single instrumentation API; kube-prometheus-stack, Loki (logs),
  Tempo (traces), Grafana dashboards-as-code; Sentry for exception aggregation.
- **Rationale**: Vendor-neutral (Datadog exit stays open); one bootstrap function in
  `atlas_observability`; satisfies FR-032..037 and SC-006/007 measurably.
- **Alternatives**: Datadog (fastest setup, $$ at scale + lock-in), ELK (heavier ops than
  Loki for our volume).
- **Tradeoffs**: Self-managed observability stack is real ops work — shipped as Helm values
  in M6 with managed-service escape hatch documented.

## 15. CI/CD — GitHub Actions + GHCR + Helm (ArgoCD at M6+)

- **Decision**: GitHub Actions with path-filtered monorepo pipelines (Turborepo/uv aware);
  images to GHCR; push-based Helm deploys with manual promotion; ArgoCD adoption deferred
  until it earns its keep.
- **Alternatives**: GitLab CI (repo migration), Jenkins (maintenance tax), ArgoCD-from-day-1
  (GitOps purity before there's an ops team — premature).
- **Tradeoffs**: Push-based deploys are less auditable than GitOps — mitigated by
  environment protection rules + deploy logs; revisit at M6.

## 16. Testing toolchain

- **Decision**: pytest (+asyncio, testcontainers), Vitest, Playwright, Schemathesis (OpenAPI
  contract fuzzing), k6 (load), Bandit/gitleaks/Trivy/pnpm-audit (security), kubeconform +
  `terraform validate` (infra). Coverage gate 80% on shared/ + module logic.
- **Rationale**: Each is the de-facto standard of its niche; Schemathesis directly enforces
  FR-010/013 contract fidelity; testcontainers keep integration tests hermetic.
- **Tradeoffs**: testcontainers in CI needs Docker-in-Docker service — standard GitHub
  Actions pattern, documented in workflow.

## 17. Object storage — S3-compatible API (MinIO local)

- **Decision**: All storage via S3 API in `atlas_core.storage`; MinIO in Compose; any
  S3-compatible bucket in cloud.
- **Rationale**: Cloud-agnostic; presigned URLs cover future upload/download needs.
- **Tradeoffs**: None material.

## 18. Secrets — env files (local) → External Secrets Operator + cloud secret manager

- **Decision**: Local: `.env` from `.env.example` (never committed with values). K8s:
  External Secrets Operator syncs cloud secret manager → K8s Secrets → env/volume mounts.
- **Alternatives**: HashiCorp Vault (most capable; heavy to operate now — revisit when
  dynamic DB credentials or PKI needed), SOPS-encrypted files (workable, weaker rotation).
- **Tradeoffs**: ESO ties rotation cadence to sync interval — acceptable; broker-credential
  encryption (future) additionally uses app-level column encryption per Constitution II.

## 19. Containers & orchestration — Docker (Compose local) + Kubernetes + Helm + Terraform

- **Decision**: As mandated. Multi-stage non-root images; Compose for the full local stack;
  one Helm chart per deployable + umbrella; Terraform for cluster + managed data services.
- **Alternatives**: ECS/Fargate (simpler, AWS lock-in vs cloud-agnostic goal), Nomad
  (ecosystem), bare VMs (snowflakes).
- **Tradeoffs**: K8s complexity before large scale — accepted because the constitution's
  scalability principle and multi-service future make it the terminal state anyway; Compose
  keeps daily development K8s-free.

## 20. Cloud — cloud-agnostic, first environment on any managed K8s

- **Decision**: No hard vendor binding in code (S3 API, OIDC, OTel, Postgres/Redis/Kafka
  managed equivalents everywhere). First deployment target chosen at M6 by cost review
  (candidates: GKE Autopilot, DigitalOcean K8s for cost; EKS if team pre-exists on AWS).
- **Rationale**: Foundation spec requires deployability, not a vendor marriage (FR-052).
- **Tradeoffs**: Slight lowest-common-denominator effect (no vendor-proprietary services on
  the critical path) — that is exactly the extensibility property the spec demands.

## 21. Monorepo tooling — pnpm + Turborepo (TS) · uv workspaces (Python)

- **Decision**: pnpm workspaces + Turborepo caching for web/packages; uv workspace with
  editable shared packages for Python; single root `scripts/` entry points.
- **Alternatives**: Nx (heavier plugin model), Bazel (build-team-sized cost), Poetry
  (slower resolver, no workspace ergonomics vs uv).
- **Tradeoffs**: Two package ecosystems in one repo is inherent to the stack choice; CI
  path-filtering keeps pipelines fast.
