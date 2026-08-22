# Data Model: Platform Foundation

**Feature**: 00-platform-foundation | **Date**: 2026-08-04
**Scope**: Platform-level entities only (no auth/trading/agent business entities). All
tables snake_case, UUIDv7 primary keys (`id`), `created_at`/`updated_at` timestamptz, and
soft-delete only where stated. User references are nullable placeholders until Spec 00
introduces the identity model.

## Entity: module_registration

Registry of modules composed into the platform (FR-002/003; supports health + ownership).

| Field | Type | Rules |
|---|---|---|
| name | text UNIQUE | kebab-case; immutable |
| version | text | semver of module contract |
| owner | text | team/person accountable |
| status | enum | `active` \| `disabled` |
| health_dependencies | jsonb | declared deps (db, redis, kafka, …) |

## Entity: event_outbox

Transactional outbox for reliable publishing (plan §7; SC-005).

| Field | Type | Rules |
|---|---|---|
| event_id | uuid UNIQUE | UUIDv7, becomes envelope id |
| event_type | text | `atlas.<domain>.<entity>.<action>` |
| schema_version | text | semver |
| correlation_id | uuid | NOT NULL |
| causation_id | uuid NULL | event that caused this one |
| producer | text | service/module name |
| payload | jsonb | validated against catalog schema |
| occurred_at | timestamptz | event time (not publish time) |
| published_at | timestamptz NULL | set by relay |
| status | enum | `pending` → `published` \| `failed` |

**State transitions**: `pending → published` (relay success); `pending → failed` (relay
exhausted; alerted; manual re-drive). Rows pruned after retention window once `published`.

## Entity: processed_event

Idempotency ledger for consumers (plan §7 exactly-once effect).

| Field | Type | Rules |
|---|---|---|
| consumer | text | module.handler identifier |
| event_id | uuid | envelope id |
| processed_at | timestamptz | |
| PK | (consumer, event_id) | duplicate delivery → no-op |

## Entity: dead_letter_event

Spec Key Entity "Dead Letter Entry" (FR-016/017).

| Field | Type | Rules |
|---|---|---|
| event_id | uuid | original envelope id |
| event_type | text | |
| envelope | jsonb | full original envelope |
| consumer | text | failing subscriber |
| failure_reason | text | last error, truncated + redacted |
| attempts | jsonb | [{at, error}] history |
| status | enum | `dead` → `redriven` \| `discarded` |
| redriven_at / redriven_by | timestamptz / text NULL | audit link |

**Transitions**: `dead → redriven` (admin re-drive; audited) ; `dead → discarded` (admin,
audited, reason required). Depth of `status='dead'` is an alerting metric.

## Entity: scheduled_job

Spec Key Entity "Scheduled Job" (FR-027).

| Field | Type | Rules |
|---|---|---|
| name | text UNIQUE | |
| schedule | text | cron expression |
| missed_run_policy | enum | `catch_up_once` \| `skip` |
| enabled | boolean | flag-controllable |
| last_run_at / last_status | timestamptz / enum NULL | `succeeded` \| `failed` |
| next_run_at | timestamptz | computed |

Plus `scheduled_job_run` child table: (job_id, started_at, finished_at, status, error,
correlation_id) — execution history.

## Entity: background_task

Spec Key Entity "Background Task" (FR-028/029).

| Field | Type | Rules |
|---|---|---|
| task_type | text | registered task name |
| status | enum | `queued` → `running` → `succeeded` \| `failed`; `failed → queued` on retry |
| attempts | int | ≤ max_attempts |
| correlation_id | uuid | NOT NULL |
| payload_ref | text NULL | pointer (object storage) for large payloads |
| result_ref / error | text NULL | terminal outcome — REQUIRED at terminal state |
| queued_at / started_at / finished_at | timestamptz | lifecycle audit |

**Invariant**: no row may remain non-terminal past `timeout_at` — janitor task marks
`failed(timeout)` (edge case: worker crash).

## Entity: feature_flag_audit

flagd owns flag definitions (GitOps file); the platform persists only evaluations of record
and changes (FR-040, FR-047).

| Field | Type | Rules |
|---|---|---|
| flag_key | text | |
| change | jsonb | old→new summary from GitOps webhook |
| changed_by | text | git author / admin actor |
| changed_at | timestamptz | |

## Entity: audit_log_entry

Spec Key Entity "Audit Log Entry" (FR-047). Append-only — no UPDATE/DELETE grants.

| Field | Type | Rules |
|---|---|---|
| actor | text | user id / service identity |
| action | text | verb.noun (`dlq.redrive`, `flag.change`, `replay.start`) |
| target | text | resource identifier |
| correlation_id | uuid | |
| metadata | jsonb | redacted context |
| occurred_at | timestamptz | |

## Entities: AI platform registries (interface-backed; Postgres tables created now, populated by future specs)

- **agent_definition**: name+version UNIQUE, capabilities jsonb, allowed_tools text[],
  status enum (`registered|active|suspended`), config_schema jsonb.
- **tool_definition**: name+version UNIQUE, input_schema jsonb, output_schema jsonb,
  required_permissions text[], rate_class text.
- **prompt_definition**: name+version UNIQUE (immutable rows — new version = new row),
  body text, metadata jsonb (owner, intended_model, eval_status), status enum
  (`draft|stable|deprecated`).
- **workflow_definition**: name+version UNIQUE, graph_ref text (definition location),
  checkpoint_policy jsonb, status enum.
- **memory_record** (schema reserved; used by first agent spec): scope columns
  (user_id, agent_id, kind enum `short_term|long_term`), content jsonb, embedding
  vector(1536) NULL, expires_at NULL. Per-user isolation enforced by mandatory
  `user_id` in every query path (Constitution VIII); deletion by user cascades here.

## Relationships (summary)

```text
module_registration 1─n event subscriptions (declared in code, mirrored for admin UI)
event_outbox ─(relay)→ Kafka ─(failure)→ dead_letter_event ─(re-drive)→ audit_log_entry
scheduled_job 1─n scheduled_job_run
background_task ─ correlation_id ─ logs/traces (join key, not FK)
agent_definition n─n tool_definition (allowed_tools by name+version)
prompt_definition / workflow_definition: versioned catalogs, immutable rows
```

## Validation rules (cross-cutting)

- All enums CHECK-constrained; all jsonb payloads validated at the application boundary
  against registered schemas before persistence (FR-010).
- `correlation_id` NOT NULL on outbox, tasks, audit, DLQ — traceability is structural
  (FR-034, SC-006).
- Retention: outbox published rows 7d; DLQ 90d; job runs 30d; audit_log ≥ 1y (append-only);
  event log (Kafka) 30d — all configurable per environment.
