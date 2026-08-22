# Local development onboarding

Target: fresh clone → running platform in under 30 minutes (Spec 00 SC-002).

## Prerequisites

- Docker Desktop (8 GB RAM allocated recommended)
- Node 22 LTS + pnpm (`corepack enable`)
- Python 3.12 + uv
- Windows: run the Python toolchain inside WSL2; keep the repo on the WSL filesystem.

## Steps

```bash
git clone <repo-url> atlas-ai-trading-os && cd atlas-ai-trading-os
./scripts/bootstrap                 # uv sync + pnpm install + .env from example
docker compose -f infra/docker/compose.yaml up -d          # postgres, redis, redpanda, minio
uv run uvicorn atlas_api.main:create_app --factory --reload  # api on :8000
pnpm --dir apps/web dev             # web on :3000 (separate terminal)
```

## Verify

| Check | Expect |
|---|---|
| `curl localhost:8000/v1/health/live` | `{"status":"alive"}` |
| `curl localhost:8000/v1/health/ready` | `ready` (dependencies up) |
| http://localhost:8000/docs | browsable OpenAPI |
| http://localhost:3000 | shell with green health widget |
| `./scripts/smoke-events` | event published, consumed, DLQ empty |
| `uv run pytest` | all green |
| `./scripts/lint-all` | all gates pass |

## Troubleshooting

- **api exits at startup**: read the first log line — config fail-fast names the missing
  variable.
- **redpanda unhealthy**: raise Docker memory, or `./scripts/dev-reset`.
- **port busy**: only 3000/8000 (+ infra ports) are used; free or remap in compose.dev.
