# Event Contract: Envelope & Foundation Catalog

**Feature**: 00-platform-foundation | **Date**: 2026-08-04
This file is the seed of the platform event catalog (FR-019). Every new event type MUST be
added here (or its successor registry) with schema + version before first publish; CI runs
compatibility checks against this catalog.

## Envelope (v1) — required on every event

| Field | Type | Notes |
|---|---|---|
| event_id | uuid (UUIDv7) | globally unique; idempotency key for consumers |
| event_type | string | `atlas.<domain>.<entity>.<action>` past tense |
| schema_version | semver | payload schema version |
| occurred_at | RFC3339 | domain time, set by producer at fact time |
| correlation_id | uuid | propagated from edge; NOT NULL |
| causation_id | uuid? | event_id of the cause, when caused by another event |
| producer | string | service/module name |
| replay_of | uuid? | set only on replayed events (consumers may branch) |
| payload | object | validated against the registered schema |

## Rules

- **Naming**: lowercase dotted; past-tense action (`…created`, `…failed`, `…redriven`).
- **Topics**: `atlas.<domain>` (e.g. `atlas.platform`, `atlas.sample`); retry topics
  `atlas.<domain>.retry.1m` / `.retry.10m`; DLQ topic `atlas.dlq.<domain>`; replay topic
  `atlas.<domain>.replay`.
- **Versioning**: additive payload changes bump minor (consumers must tolerate unknown
  fields); breaking changes register a new `event_type` suffixed `.v2` and run both during a
  documented migration window.
- **Idempotency**: consumers record (consumer, event_id) in the processed_event ledger and
  no-op on duplicates.
- **Ordering**: per-partition Kafka offset order only; no wall-clock ordering assumptions.
- **PII/secrets**: payloads carry references (ids) not sensitive values; the redaction rules
  applied to logs apply to payload design reviews too.

## Foundation catalog (v1.0.0)

| event_type | Producer | Payload (summary) | Purpose |
|---|---|---|---|
| atlas.platform.module.registered | api | {name, version, owner} | Module composed into platform at startup/registration |
| atlas.platform.event.dead_lettered | worker | {event_id, event_type, consumer, failure_reason} | DLQ arrival — drives alerting + admin UI |
| atlas.platform.event.redriven | api | {event_id, consumer, actor} | Audited re-drive occurred |
| atlas.platform.replay.started | api | {replay_id, event_type, from, to, actor} | Replay initiated |
| atlas.platform.replay.completed | worker | {replay_id, events_replayed} | Replay finished |
| atlas.platform.job.run_completed | scheduler | {job_name, status, started_at, finished_at} | Scheduled job outcome (drives missed-run alerting) |
| atlas.platform.task.state_changed | worker | {task_id, task_type, status, attempts} | Background task lifecycle visibility |
| atlas.platform.flag.changed | api (GitOps webhook) | {flag_key, changed_by, change} | Flag change fact (audited) |
| atlas.sample.echo.requested | api (sample module) | {message_length} | Throwaway proof event exercising the full pipeline; removed with sample module |

Reserved future domains (naming stability for Spec 01+): `atlas.auth.*`, `atlas.broker.*`,
`atlas.trading.*`, `atlas.portfolio.*`, `atlas.journal.*`, `atlas.notification.*`,
`atlas.ai.*` (e.g. `atlas.ai.recommendation.generated`).
