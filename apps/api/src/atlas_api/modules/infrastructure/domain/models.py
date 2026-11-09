"""Domain models for Production Infrastructure & SRE Operations (Spec 11 §2, §5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid


@dataclass
class ServiceDeployment:
    id: str
    service_name: str  # atlas-api | atlas-web | atlas-worker | atlas-scheduler | atlas-ingestion
    environment: str   # production | staging | development
    git_commit_sha: str
    image_tag: str
    replicas_count: int
    rollout_strategy: str  # CANARY | ROLLING_UPDATE
    status: str            # DEPLOYING | HEALTHY | DEGRADED | FAILED | ROLLED_BACK
    canary_weight: int     # 0 to 100
    deployed_by: str
    deployed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class HealthProbe:
    id: str
    service_name: str
    pod_id: str
    probe_type: str  # HTTP_READINESS | DB_CONNECTION_POOL | REDIS_PING | KAFKA_LAG | VENUE_LATENCY
    status: str      # HEALTHY | DEGRADED | UNHEALTHY
    latency_ms: int
    error_detail: str | None = None
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SreIncident:
    id: str
    incident_number: str
    title: str
    severity: str    # P0_CRITICAL | P1_HIGH | P2_MEDIUM | P3_LOW
    affected_component: str
    alert_source: str
    root_cause: str = ""
    mitigation_steps: str = ""
    triggered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime | None = None


@dataclass
class CapacityMetric:
    id: str
    node_pool: str
    active_nodes: int
    total_cpu_millicores: int
    used_cpu_millicores: int
    total_memory_mb: int
    used_memory_mb: int
    active_pods_count: int
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
