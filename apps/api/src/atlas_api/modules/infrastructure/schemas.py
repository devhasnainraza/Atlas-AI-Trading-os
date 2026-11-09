"""Pydantic schemas for Infrastructure & SRE API (Spec 11 §2, §9)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RecordDeploymentRequest(BaseModel):
    service_name: str = Field(..., description="atlas-api | atlas-web | atlas-worker | atlas-scheduler | atlas-ingestion")
    environment: str = Field(default="production")
    git_commit_sha: str = Field(..., min_length=7, max_length=40)
    image_tag: str = Field(...)
    replicas_count: int = Field(default=4, ge=1, le=100)
    rollout_strategy: str = Field(default="CANARY", description="CANARY | ROLLING_UPDATE")
    canary_weight: int = Field(default=10, ge=0, le=100)
    deployed_by: str = Field(default="ArgoCD")


class ServiceDeploymentResponse(BaseModel):
    id: str
    service_name: str
    environment: str
    git_commit_sha: str
    image_tag: str
    replicas_count: int
    rollout_strategy: str
    status: str
    canary_weight: int
    deployed_by: str
    deployed_at: str


class RecordHealthProbeRequest(BaseModel):
    service_name: str
    pod_id: str
    probe_type: str = Field(default="HTTP_READINESS", description="HTTP_READINESS | DB_CONNECTION_POOL | REDIS_PING | KAFKA_LAG | VENUE_LATENCY")
    status: str = Field(default="HEALTHY", description="HEALTHY | DEGRADED | UNHEALTHY")
    latency_ms: int = Field(..., ge=0)
    error_detail: str | None = None


class HealthProbeResponse(BaseModel):
    id: str
    service_name: str
    pod_id: str
    probe_type: str
    status: str
    latency_ms: int
    error_detail: str | None
    checked_at: str


class CreateIncidentRequest(BaseModel):
    title: str = Field(..., min_length=5)
    severity: str = Field(default="P1_HIGH", description="P0_CRITICAL | P1_HIGH | P2_MEDIUM | P3_LOW")
    affected_component: str
    alert_source: str = Field(default="Prometheus")


class ResolveIncidentRequest(BaseModel):
    root_cause: str = Field(..., min_length=10)
    mitigation_steps: str = Field(..., min_length=10)


class SreIncidentResponse(BaseModel):
    id: str
    incident_number: str
    title: str
    severity: str
    affected_component: str
    alert_source: str
    root_cause: str
    mitigation_steps: str
    triggered_at: str
    resolved_at: str | None


class ClusterCapacityResponse(BaseModel):
    active_nodes: int
    total_cpu_cores: float
    used_cpu_cores: float
    total_memory_gb: float
    used_memory_gb: float
    active_pods_count: int
