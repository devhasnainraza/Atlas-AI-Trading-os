# Quickstart: Atlas Platform Foundation (Local Development)

**Feature**: 00-platform-foundation | **Target**: fresh clone → running platform in < 30
minutes (SC-002). This guide is the acceptance artifact for User Story 5. Operational
procedures live in [`docs/runbooks/platform-foundation.md`](../../docs/runbooks/platform-foundation.md);
this file stays with the spec as its acceptance evidence (see §7).

## Prerequisites

- Docker Desktop (or Docker Engine + Compose v2) — 8 GB RAM allocated recommended
- Node.js 22 LTS + pnpm 9 (`corepack enable`)
- Python 3.12 + uv (`pipx install uv` or installer)
- Git. Windows users: WSL2 is the supported path for the Python toolchain.

## 1. Clone & bootstrap

```bash
git clone <repo-url> atlas-ai-trading-os && cd atlas-ai-trading-os
cp infra/docker/.env.example .env        # placeholder values only — never commit real secrets
pnpm install                              # TS workspaces (web, packages)
uv sync                                   # Python workspaces (api, services, shared)
./scripts/bootstrap                       # pre-commit hooks, local certs, sanity checks
```

## 2. Start the platform

```bash
docker compose up -d                      # postgres+pgvector, redis, redpanda, minio, flagd
docker compose -f compose.yaml -f compose.dev.yaml up api worker scheduler web
# optional observability profile (grafana/prometheus/loki/tempo):
docker compose --profile observability up -d
```

Hot reload: `apps/api` and `apps/web` mount source volumes — edits apply live.

## 3. Verify (smoke checklist)

| Check | Command / URL | Expect |
|---|---|---|
| API liveness | `curl localhost:8000/v1/health/live` | `{"status":"alive"}` |
| API readiness | `curl localhost:8000/v1/health/ready` | `status: ready`, postgres/redis/kafka `up` |
| OpenAPI docs | http://localhost:8000/docs | browsable spec |
| Web app | http://localhost:3000 | shell renders, health widget green |
| Event pipeline | `./scripts/smoke-events` | publishes sample echo → consumer processes → 0 in DLQ |
| Grafana (profile) | http://localhost:3001 | API overview dashboard live |

## 4. Run tests

```bash
uv run pytest                             # unit + integration + contract (all Python suites)
uv run pytest tests/contract              # contract suites only
uv run pytest tests/e2e                   # local-stack smoke — skips itself if the API is down
```

Frontend test suites are not wired yet: `pnpm test` currently executes no tasks, and the
end-to-end smoke in `tests/e2e/test_local_stack.py` is pytest, not Playwright. Both arrive
with the first UI feature.

## 5. Everyday commands

```bash
./scripts/dev-reset            # wipe volumes → pristine local state
./scripts/db migrate           # alembic upgrade head
./scripts/db makemigration m   # autogenerate migration (review before commit!)
./scripts/generate-client      # regenerate packages/api-client from OpenAPI
./scripts/lint-all             # ruff + mypy + import-linter + bandit + eslint + dep-cruiser + tsc
```

## 6. Environment model

`ENV=local|development|staging|production`. Local uses `.env`; deployed environments get
config from Helm values + External Secrets. Startup fails fast naming any missing variable —
if the api container exits immediately, read its first log line.

## 7. Validation evidence

Recorded 2026-08-22 on Windows 11 / Python 3.12 / Node 22. Reproduce with
`uv run pytest` and `bash scripts/lint-all`.

| Gate | Command | Result |
|---|---|---|
| Python tests | `uv run pytest` | **47 passed, 9 skipped** |
| Lint | `uv run ruff check .` | clean |
| Format | `uv run ruff format --check .` | 116 files already formatted |
| Types (Python) | `uv run mypy <4 shared pkgs> --strict` | Success — 17 source files |
| Module boundaries | `uv run lint-imports` | 44 files, 71 deps, 2 contracts kept, **0 broken** |
| Python security | `uv run bandit -r shared/ apps/ services/ -c .bandit.yml` | no issues |
| Dependency CVEs | `uv run pip-audit` | no known vulnerabilities (4 local workspace packages skipped — not on PyPI) |
| TS lint + boundaries | `pnpm lint` | 4/4 packages; dep-cruiser 7 modules, **0 violations** |
| TS types | `pnpm typecheck` | 4/4 packages |
| Lockfiles | `pnpm install --frozen-lockfile`, `uv lock --check` | no drift |

**Smoke notes.** The 9 skipped tests are `tests/e2e/test_local_stack.py` — they self-skip
when `localhost:8000` is not answering, so a green run without Docker does **not** prove the
live stack. To close that gap, bring the stack up (§2) and re-run `uv run pytest tests/e2e`;
those 9 must then pass, and every row of the §3 checklist must hold. Everything above was
verified without Docker: the in-memory event bus, outbox, processed-event ledger, feature-flag
provider, and audit log all exercise their real code paths through the FastAPI test client.

## Troubleshooting

- **Ports busy**: only 3000 (web), 8000 (api), 3001 (grafana) are published — free them or
  override in `compose.dev.yaml`.
- **Redpanda unhealthy on low RAM**: raise Docker memory or `docker compose up` core deps
  only.
- **Windows path issues**: run everything inside WSL2; keep the repo on the WSL filesystem.
- **Readiness shows kafka down**: `docker compose logs redpanda`; then `./scripts/dev-reset`
  if the volume is corrupted.
