"""Service implementation for Infrastructure & SRE Operations (Spec 11 §2, §5)."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

from atlas_api.modules.infrastructure.domain.models import (
    CapacityMetric,
    HealthProbe,
    ServiceDeployment,
    SreIncident,
)
from atlas_core.errors import NotFoundError, ValidationError


class InfrastructureService:
    """Orchestrates deployment tracking, health probes, incident lifecycles, and cluster telemetry."""

    def __init__(self) -> None:
        self._deployments: dict[str, ServiceDeployment] = {}
        self._probes: list[HealthProbe] = []
        self._incidents: dict[str, SreIncident] = {}

        # Seed initial healthy deployment
        init_dep = ServiceDeployment(
            id=str(uuid.uuid4()),
            service_name="atlas-api",
            environment="production",
            git_commit_sha="a1b2c3d4e5f6789012345678901234567890abcd",
            image_tag="ghcr.io/atlas-org/atlas-api:v1.0.0",
            replicas_count=4,
            rollout_strategy="CANARY",
            status="HEALTHY",
            canary_weight=100,
            deployed_by="ArgoCD",
            deployed_at=datetime.now(timezone.utc),
        )
        self._deployments[init_dep.id] = init_dep

        # Seed initial healthy probes
        now = datetime.now(timezone.utc)
        self._probes.extend([
            HealthProbe(str(uuid.uuid4()), "atlas-api", "api-pod-7f98b", "DB_CONNECTION_POOL", "HEALTHY", 2, None, now),
            HealthProbe(str(uuid.uuid4()), "atlas-api", "api-pod-7f98b", "REDIS_PING", "HEALTHY", 1, None, now),
            HealthProbe(str(uuid.uuid4()), "atlas-worker", "worker-pod-2d88a", "KAFKA_LAG", "HEALTHY", 8, None, now),
            HealthProbe(str(uuid.uuid4()), "atlas-ingestion", "ingest-binance-01", "VENUE_LATENCY", "HEALTHY", 18, None, now),
        ])

    def record_deployment(
        self,
        service_name: str,
        environment: str,
        git_commit_sha: str,
        image_tag: str,
        replicas_count: int = 4,
        rollout_strategy: str = "CANARY",
        canary_weight: int = 10,
        deployed_by: str = "ArgoCD",
    ) -> ServiceDeployment:
        dep_id = str(uuid.uuid4())
        deployment = ServiceDeployment(
            id=dep_id,
            service_name=service_name,
            environment=environment,
            git_commit_sha=git_commit_sha,
            image_tag=image_tag,
            replicas_count=replicas_count,
            rollout_strategy=rollout_strategy.upper(),
            status="DEPLOYING",
            canary_weight=canary_weight,
            deployed_by=deployed_by,
            deployed_at=datetime.now(timezone.utc),
        )
        self._deployments[dep_id] = deployment
        return deployment

    def get_deployments(self) -> list[ServiceDeployment]:
        return sorted(self._deployments.values(), key=lambda d: d.deployed_at, reverse=True)

    def rollback_deployment(self, deployment_id: str) -> ServiceDeployment:
        dep = self._deployments.get(deployment_id)
        if not dep:
            raise NotFoundError(f"Deployment '{deployment_id}' not found")
        dep.status = "ROLLED_BACK"
        dep.canary_weight = 0
        return dep

    def record_probe(
        self,
        service_name: str,
        pod_id: str,
        probe_type: str,
        status: str,
        latency_ms: int,
        error_detail: str | None = None,
    ) -> HealthProbe:
        probe = HealthProbe(
            id=str(uuid.uuid4()),
            service_name=service_name,
            pod_id=pod_id,
            probe_type=probe_type.upper(),
            status=status.upper(),
            latency_ms=latency_ms,
            error_detail=error_detail,
            checked_at=datetime.now(timezone.utc),
        )
        self._probes.append(probe)
        return probe

    def get_recent_probes(self, limit: int = 50) -> list[HealthProbe]:
        return sorted(self._probes, key=lambda p: p.checked_at, reverse=True)[:limit]

    def create_incident(
        self,
        title: str,
        severity: str,
        affected_component: str,
        alert_source: str,
    ) -> SreIncident:
        inc_id = str(uuid.uuid4())
        num = f"INC-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{len(self._incidents) + 1:03d}"
        incident = SreIncident(
            id=inc_id,
            incident_number=num,
            title=title,
            severity=severity.upper(),
            affected_component=affected_component,
            alert_source=alert_source,
            root_cause="",
            mitigation_steps="",
            triggered_at=datetime.now(timezone.utc),
            resolved_at=None,
        )
        self._incidents[inc_id] = incident
        return incident

    def resolve_incident(
        self,
        incident_id: str,
        root_cause: str,
        mitigation_steps: str,
    ) -> SreIncident:
        incident = self._incidents.get(incident_id)
        if not incident:
            raise NotFoundError(f"Incident '{incident_id}' not found")
        incident.root_cause = root_cause
        incident.mitigation_steps = mitigation_steps
        incident.resolved_at = datetime.now(timezone.utc)
        return incident

    def get_incidents(self) -> list[SreIncident]:
        return sorted(self._incidents.values(), key=lambda i: i.triggered_at, reverse=True)

    def get_cluster_capacity(self) -> dict[str, Any]:
        return {
            "active_nodes": 6,
            "total_cpu_cores": 48.0,
            "used_cpu_cores": 18.5,
            "total_memory_gb": 192.0,
            "used_memory_gb": 74.2,
            "active_pods_count": 28,
        }
