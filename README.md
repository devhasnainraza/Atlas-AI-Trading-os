# Atlas AI Trading OS

An AI-first trading operating system built platform-first: modular monolith backend
(FastAPI), event-driven communication, AI platform interfaces, and a Next.js frontend —
all in one monorepo.

## Repository layout

| Path | Purpose |
|---|---|
| `apps/api` | FastAPI application — unified API layer composed of isolated modules |
| `apps/web` | Next.js 15 frontend |
| `services/worker` | Event consumers, outbox relay, background jobs |
| `services/scheduler` | Scheduled jobs (cron-style) |
| `shared/` | Shared Python packages: `atlas_core`, `atlas_events`, `atlas_observability`, `atlas_ai` |
| `packages/` | Shared TypeScript packages: `config` (+ future `ui`, `api-client`) |
| `infra/` | Docker, Kubernetes, Terraform, observability provisioning |
| `specs/` | Spec-Driven Development artifacts (spec → plan → tasks per feature) |
| `docs/` | Architecture, runbooks, onboarding |
| `history/` | Prompt History Records and ADRs |

## Quickstart

See `specs/00-platform-foundation/quickstart.md` (canonical, validated) or:

```bash
pnpm install && uv sync          # toolchains
docker compose -f infra/docker/compose.yaml up -d    # infra deps
uv run uvicorn atlas_api.main:create_app --factory --reload   # API on :8000
uv run pytest                    # test suite
```

## Governance

Engineering rules live in `.specify/memory/constitution.md` (v1.0.0). Every feature flows
spec → plan → tasks → implementation under `specs/`.
