# Atlas Platform Architecture

**Version**: Spec 00 (Platform Foundation) | **Date**: 2026-08-04

## System overview

Atlas is a **modular monolith-first** platform. One FastAPI application (`apps/api`) is
composed of isolated modules; worker and scheduler run as separate processes but share the
same code via the workspace. The event bus connects them. Clients talk exclusively through
the unified API.

```text
Clients → Ingress (TLS) → apps/api (middleware → modules) → PostgreSQL + Redis + Kafka
                                                          ↓
                               services/worker (event relay, consumers) ← Kafka
                               services/scheduler (cron jobs)
```

## Module system

Each module in `apps/api/src/atlas_api/modules/<name>/` follows the port-and-adapters
layout defined in `modules/_template/README.md`:

```
router.py → service.py → domain/ → repository/
```

Import rule (enforced by import-linter in CI): **other modules may only import a module's
`public.py`**. Cross-module communication flows through events (`shared/atlas_events`) or
typed public interfaces. This is checked on every PR — violations are build failures.

## Shared packages

| Package | Responsibility |
|---|---|
| `atlas_core` | config, errors, correlation IDs, feature flags, dependencies |
| `atlas_events` | event envelope, bus, outbox, ledger, catalog |
| `atlas_observability` | structured logging (structlog JSON), OTel bootstrap |
| `atlas_ai` | AI platform interfaces + in-memory reference impls |

Shared packages **must not** import the API app. That constraint is also enforced by
import-linter.

## Key design decisions

Full rationale in `specs/001-platform-foundation/research.md`. Short version:

- **Modular monolith** over microservices: one deployment, clear seams, horizontal scale
  via workers and HPA. Modules can be extracted later without changing their contracts.
- **Kafka** (Redpanda locally) for the event bus: retained log, consumer groups, replay —
  the AI agent architecture depends on these semantics.
- **Outbox pattern**: events are written transactionally with state; the worker relays them.
  No event is lost if the broker is briefly down.
- **In-memory reference implementations**: every shared protocol ships a testable in-memory
  implementation so the full logic can run without Docker in unit/contract tests.

## Adding a new module

1. Copy `apps/api/src/atlas_api/modules/_template/` to your module name.
2. Register new event types in `shared/atlas_events/catalog.py` (before first publish).
3. Add one line to `create_app` in `apps/api/src/atlas_api/main.py`.
4. Run `uv run pytest` and `./scripts/lint-all` — no other file changes are needed.
