"""Infrastructure & SRE Operations API router and endpoints (Spec 11 §2, §9)."""

from __future__ import annotations

from dataclasses import dataclass
from fastapi import APIRouter, Depends, Path, Query, Request

from atlas_api.modules.infrastructure.domain.models import (
    HealthProbe,
    ServiceDeployment,
    SreIncident,
)
from atlas_api.modules.infrastructure.schemas import (
    ClusterCapacityResponse,
    CreateIncidentRequest,
    HealthProbeResponse,
    RecordDeploymentRequest,
    RecordHealthProbeRequest,
    ResolveIncidentRequest,
    ServiceDeploymentResponse,
    SreIncidentResponse,
)
from atlas_api.modules.infrastructure.service import InfrastructureService
from atlas_core.errors import InternalError

router = APIRouter(prefix="/infrastructure", tags=["infrastructure"])

STATE_KEY = "infrastructure_context"


@dataclass(frozen=True)
class InfrastructureModuleContext:
    service: InfrastructureService


def get_infra_context(request: Request) -> InfrastructureModuleContext:
    context = getattr(request.app.state, STATE_KEY, None)
    if not isinstance(context, InfrastructureModuleContext):
        raise InternalError(
            internal_context={"detail": "infrastructure module accessed before composition"}
        )
    return context


def get_infra_service(
    context: InfrastructureModuleContext = Depends(get_infra_context),
) -> InfrastructureService:
    return context.service


def _format_deployment(d: ServiceDeployment) -> ServiceDeploymentResponse:
    return ServiceDeploymentResponse(
        id=d.id,
        service_name=d.service_name,
        environment=d.environment,
        git_commit_sha=d.git_commit_sha,
        image_tag=d.image_tag,
        replicas_count=d.replicas_count,
        rollout_strategy=d.rollout_strategy,
        status=d.status,
        canary_weight=d.canary_weight,
        deployed_by=d.deployed_by,
        deployed_at=d.deployed_at.isoformat(),
    )


def _format_probe(p: HealthProbe) -> HealthProbeResponse:
    return HealthProbeResponse(
        id=p.id,
        service_name=p.service_name,
        pod_id=p.pod_id,
        probe_type=p.probe_type,
        status=p.status,
        latency_ms=p.latency_ms,
        error_detail=p.error_detail,
        checked_at=p.checked_at.isoformat(),
    )


def _format_incident(i: SreIncident) -> SreIncidentResponse:
    return SreIncidentResponse(
        id=i.id,
        incident_number=i.incident_number,
        title=i.title,
        severity=i.severity,
        affected_component=i.affected_component,
        alert_source=i.alert_source,
        root_cause=i.root_cause,
        mitigation_steps=i.mitigation_steps,
        triggered_at=i.triggered_at.isoformat(),
        resolved_at=i.resolved_at.isoformat() if i.resolved_at else None,
    )


@router.post("/deployments", response_model=ServiceDeploymentResponse)
async def record_deployment(
    body: RecordDeploymentRequest,
    service: InfrastructureService = Depends(get_infra_service),
) -> ServiceDeploymentResponse:
    """Records a new CI/CD deployment or canary promotion event."""
    dep = service.record_deployment(
        service_name=body.service_name,
        environment=body.environment,
        git_commit_sha=body.git_commit_sha,
        image_tag=body.image_tag,
        replicas_count=body.replicas_count,
        rollout_strategy=body.rollout_strategy,
        canary_weight=body.canary_weight,
        deployed_by=body.deployed_by,
    )
    return _format_deployment(dep)


@router.get("/deployments", response_model=list[ServiceDeploymentResponse])
async def list_deployments(
    service: InfrastructureService = Depends(get_infra_service),
) -> list[ServiceDeploymentResponse]:
    """Lists recent service deployments across production and staging."""
    deployments = service.get_deployments()
    return [_format_deployment(d) for d in deployments]


@router.post("/deployments/{deployment_id}/rollback", response_model=ServiceDeploymentResponse)
async def rollback_deployment(
    deployment_id: str = Path(..., description="Deployment UUID"),
    service: InfrastructureService = Depends(get_infra_service),
) -> ServiceDeploymentResponse:
    """Executes immediate automated canary rollback upon anomaly detection."""
    dep = service.rollback_deployment(deployment_id=deployment_id)
    return _format_deployment(dep)


@router.post("/health/probes", response_model=HealthProbeResponse)
async def record_health_probe(
    body: RecordHealthProbeRequest,
    service: InfrastructureService = Depends(get_infra_service),
) -> HealthProbeResponse:
    """Ingests real-time SRE health telemetry from Kubernetes pod probes."""
    probe = service.record_probe(
        service_name=body.service_name,
        pod_id=body.pod_id,
        probe_type=body.probe_type,
        status=body.status,
        latency_ms=body.latency_ms,
        error_detail=body.error_detail,
    )
    return _format_probe(probe)


@router.get("/health/probes", response_model=list[HealthProbeResponse])
async def list_health_probes(
    limit: int = Query(default=50, ge=1, le=200),
    service: InfrastructureService = Depends(get_infra_service),
) -> list[HealthProbeResponse]:
    """Returns recent health telemetry across databases, caches, queues, and venues."""
    probes = service.get_recent_probes(limit=limit)
    return [_format_probe(p) for p in probes]


@router.post("/incidents", response_model=SreIncidentResponse)
async def create_incident(
    body: CreateIncidentRequest,
    service: InfrastructureService = Depends(get_infra_service),
) -> SreIncidentResponse:
    """Records an automated or manual SRE operational incident."""
    incident = service.create_incident(
        title=body.title,
        severity=body.severity,
        affected_component=body.affected_component,
        alert_source=body.alert_source,
    )
    return _format_incident(incident)


@router.get("/incidents", response_model=list[SreIncidentResponse])
async def list_incidents(
    service: InfrastructureService = Depends(get_infra_service),
) -> list[SreIncidentResponse]:
    """Lists tracked SRE operational incidents and outages."""
    incidents = service.get_incidents()
    return [_format_incident(i) for i in incidents]


@router.post("/incidents/{incident_id}/resolve", response_model=SreIncidentResponse)
async def resolve_incident(
    incident_id: str = Path(..., description="Incident UUID"),
    body: ResolveIncidentRequest = ...,
    service: InfrastructureService = Depends(get_infra_service),
) -> SreIncidentResponse:
    """Marks an operational incident resolved and attaches root-cause post-mortem."""
    incident = service.resolve_incident(
        incident_id=incident_id,
        root_cause=body.root_cause,
        mitigation_steps=body.mitigation_steps,
    )
    return _format_incident(incident)


@router.get("/capacity", response_model=ClusterCapacityResponse)
async def get_cluster_capacity(
    service: InfrastructureService = Depends(get_infra_service),
) -> ClusterCapacityResponse:
    """Returns Kubernetes cluster compute, memory, and pod capacity metrics."""
    metrics = service.get_cluster_capacity()
    return ClusterCapacityResponse(**metrics)
