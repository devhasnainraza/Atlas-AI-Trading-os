"""Unit tests for InfrastructureService and SRE telemetry (Spec 11 §2, §5)."""

import pytest
from atlas_api.modules.infrastructure.service import InfrastructureService
from atlas_core.errors import NotFoundError


def test_deployment_lifecycle_and_rollback():
    service = InfrastructureService()

    # Record deployment
    dep = service.record_deployment(
        service_name="atlas-worker",
        environment="production",
        git_commit_sha="c0ffeec0ffeec0ffeec0ffeec0ffeec0ffeec0ff",
        image_tag="ghcr.io/atlas-org/atlas-worker:v1.1.0",
        replicas_count=8,
        rollout_strategy="CANARY",
        canary_weight=20,
    )
    assert dep.service_name == "atlas-worker"
    assert dep.status == "DEPLOYING"
    assert dep.canary_weight == 20

    # Execute rollback
    rolled_back = service.rollback_deployment(dep.id)
    assert rolled_back.status == "ROLLED_BACK"
    assert rolled_back.canary_weight == 0

    with pytest.raises(NotFoundError):
        service.rollback_deployment("non-existent-dep-id")


def test_health_probes_and_incidents():
    service = InfrastructureService()

    # Record probe
    probe = service.record_probe(
        service_name="atlas-ingestion",
        pod_id="ingest-binance-02",
        probe_type="VENUE_LATENCY",
        status="HEALTHY",
        latency_ms=14,
    )
    assert probe.status == "HEALTHY"
    assert probe.latency_ms == 14

    recent = service.get_recent_probes(limit=10)
    assert any(p.id == probe.id for p in recent)

    # Incident lifecycle
    inc = service.create_incident(
        title="Binance WebSocket Reconnect Loop",
        severity="P0_CRITICAL",
        affected_component="atlas-ingestion",
        alert_source="PagerDuty",
    )
    assert inc.severity == "P0_CRITICAL"
    assert inc.resolved_at is None

    resolved = service.resolve_incident(
        incident_id=inc.id,
        root_cause="Upstream IP rate limiting on public endpoint; rotated proxy pool",
        mitigation_steps="Configured secondary gateway tunnel with dedicated institutional IP",
    )
    assert resolved.resolved_at is not None
    assert "rotated proxy pool" in resolved.root_cause


def test_cluster_capacity():
    service = InfrastructureService()
    cap = service.get_cluster_capacity()
    assert cap["active_nodes"] >= 6
    assert cap["total_cpu_cores"] > cap["used_cpu_cores"]
    assert cap["active_pods_count"] >= 20
