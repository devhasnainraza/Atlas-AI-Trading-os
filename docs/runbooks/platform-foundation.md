# Runbook: Platform Foundation

Operational procedures for the Spec 00 platform. Each section is an alert anchor.

## api-errors

1. `curl /v1/health/ready` — is a dependency down? Follow **dependency-outage** if so.
2. Search logs by a failing request's `X-Correlation-ID` (single ID reconstructs the
   whole path — SC-006).
3. Check the most recent deploy; roll back via Helm if errors started with it.

## api-latency

1. Grafana → API overview → which routes regressed?
2. Check DB/Redis/Kafka saturation panels; scale replicas (HPA should have already).
3. If a single route: inspect recent changes to that module only (module isolation).

## dependency-outage

1. `/v1/health/ready` names the failing dependency and its latency.
2. Managed-service console → status. Local: `docker compose ps`, `docker compose logs <svc>`.
3. Platform degrades rather than fails (Constitution IX); recovery is automatic when the
   dependency returns — verify readiness flips back without restarts.

## dead-letters

1. `GET /v1/platform/dead-letter-events` — inspect failure_reason and attempts.
2. Fix the consumer bug or the poison payload cause.
3. Re-drive: `POST /v1/platform/dead-letter-events/{event_id}/redrive?consumer=<name>`
   (audited). Never delete DLQ entries silently.

## consumer-lag

1. Event bus dashboard → which consumer group?
2. Scale worker replicas; check for a poison-event retry loop (see dead-letters).

## scheduler

1. Scheduler logs → `scheduler_heartbeat` present? If not, restart the deployment.
2. Missed runs follow each job's declared policy (`catch_up_once` | `skip`) — verify, do
   not manually re-run without checking the policy first.

## flag-desync

A flag change landed in Git but the API still serves the old value.

1. Flags are read from a file provider that reloads on **content change**, not on a timer
   alone — an unchanged redeploy is deliberately not a flag event.
2. Force a re-read: `POST /v1/platform/feature-flags/sync` with `{"revision": "<sha>"}`.
   The webhook is a *hint*: it triggers a re-read of the flag source and is never trusted
   for values, so a spoofed payload cannot set flag state.
3. Confirm it landed: `GET /v1/platform/audit-log?action=feature_flags.sync` — the entry
   records `actor=gitops:<source>` and the claimed revision.
4. Still stale? The source file itself is wrong or unreadable. The worker's sync watcher
   ignores malformed/missing sources rather than clearing flags, so check worker logs for
   the read failure before touching flag state.
5. Evaluation failures fall back to the declared default (fail-safe, Constitution IX) —
   a broken provider degrades to defaults, it does not error the request.

## local-stack

- Reset: `./scripts/dev-reset`
- Event pipeline smoke: `./scripts/smoke-events`
- Ports: web 3000, api 8000, postgres 5432, redis 6379, redpanda 19092, minio 9000/9001.

## verification (post-deploy / post-clone smoke)

Run in this order; each step is cheap and the first failure localizes the problem.

```bash
bash scripts/lint-all          # ruff + mypy --strict + import-linter + bandit + eslint + dep-cruiser + tsc
uv run pytest                  # expect 47 passed, 9 skipped without Docker
uv run pytest tests/e2e        # with the stack up, the 9 must pass instead of skip
./scripts/smoke-events         # publish → consume → assert 0 dead letters
```

Then walk the §3 checklist in
[`specs/00-platform-foundation/quickstart.md`](../../specs/00-platform-foundation/quickstart.md),
which also carries the recorded gate evidence.

**Caveat worth knowing during an incident:** `tests/e2e/test_local_stack.py` self-skips when
`localhost:8000` is not answering. A green `uv run pytest` with 9 skips proves the in-process
platform (event bus, outbox, processed-event ledger, feature flags, audit log) and proves
nothing about the live stack. Read the skip count, not just the color.
