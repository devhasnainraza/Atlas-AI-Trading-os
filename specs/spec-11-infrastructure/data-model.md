# Data Model: Production Infrastructure

**Feature**: 11-infrastructure | **Date**: 2026-09-21 | **Plan**: [plan.md](./plan.md)

Conventions per Spec 00: UUIDv7 `id` primary keys, `created_at` / `checked_at` `timestamptz`, snake_case names, enums CHECK-constrained. Operational and telemetry tables managed in PostgreSQL administrative schema with automated 90-day partition purging.

## infra_service_deployments

Tracks CI/CD release deployments, container images, and canary promotion states across environments.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| service_name | text | `atlas-api | atlas-web | atlas-worker | atlas-scheduler | atlas-ingestion` |
| environment | text | `production | staging | development` |
| git_commit_sha | text | Full 40-character commit hash |
| image_tag | text | Container image reference in GHCR/ECR |
| replicas_count | int | Number of active pods |
| rollout_strategy | text | `CANARY | ROLLING_UPDATE` |
| status | text | `DEPLOYING | HEALTHY | DEGRADED | FAILED | ROLLED_BACK` |
| canary_weight | int | Current percentage of traffic routed to canary (0 to 100) |
| deployed_by | text | Triggering actor or ArgoCD bot |
| deployed_at | timestamptz | Rollout start timestamp; indexed |

## infra_health_probes

Continuous SRE telemetry capturing service readiness, database connections, and venue network latency.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| service_name | text | Monitored service identifier |
| pod_id | text | Kubernetes pod name |
| probe_type | text | `HTTP_READINESS | DB_CONNECTION_POOL | REDIS_PING | KAFKA_LAG | VENUE_LATENCY` |
| status | text | `HEALTHY | DEGRADED | UNHEALTHY` |
| latency_ms | int | Execution latency of health probe |
| error_detail | text | Sanitized diagnostic error string on failure |
| checked_at | timestamptz | Periodic check timestamp; indexed |

## infra_sre_incidents

Durable record of operational outages, threshold breaches, and post-mortem investigations.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| incident_number | text | Unique human-readable code (e.g. `INC-2026-0814`) |
| title | text | Brief summary of anomaly |
| severity | text | `P0_CRITICAL | P1_HIGH | P2_MEDIUM | P3_LOW` |
| affected_component| text | e.g. `Binance-Ingestion`, `PostgreSQL-Primary`, `Worker-Pool` |
| alert_source | text | `Prometheus | CloudWatch | PagerDuty | HealthProbe` |
| root_cause | text | Detailed technical explanation post-resolution |
| mitigation_steps | text | Actions taken to restore normal service |
| triggered_at | timestamptz | Outage start timestamp; indexed |
| resolved_at | timestamptz | Resolution timestamp |

## infra_capacity_metrics

Periodic snapshots of cluster compute utilization, node scaling, and pod saturation.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| node_pool | text | e.g. `general-compute`, `ingestion-high-net`, `gpu-inference` |
| active_nodes | int | Current active EC2 instances |
| total_cpu_millicores| int | Total provisioned CPU capacity |
| used_cpu_millicores | int | Total utilized CPU |
| total_memory_mb | int | Total provisioned RAM |
| used_memory_mb | int | Total consumed RAM |
| active_pods_count | int | Number of pods scheduled on pool |
| recorded_at | timestamptz | Snapshot timestamp; indexed |
