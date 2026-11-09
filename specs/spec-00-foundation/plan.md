# Implementation Plan: Platform Foundation & Core System Architecture

**Branch**: `00-platform-foundation` | **Date**: 2026-08-04 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/spec-00-foundation/spec.md`

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

**Gate result**: PASS.

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
```

## 2. Monorepo Structure

```text
specs/spec-00-foundation/
├── spec.md              # Feature specification
├── plan.md              # This architecture plan
├── data-model.md        # Foundation entities
└── tasks.md             # Test-first task breakdown
```

### Dependency rules (enforced by import-linter in CI):
1. Dependencies point inward: API → Service → Domain; Repositories implement Domain-defined
   interfaces (ports & adapters).
2. A module may import another module ONLY via `modules/<name>/public.py` (its published
   interface) or by consuming its events. Importing another module's internals fails CI.
3. `shared/` packages may not import from any module. Modules may import `shared/`.
