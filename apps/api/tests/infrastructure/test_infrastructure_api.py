"""API contract tests for Infrastructure & SRE Operations module (Spec 11 §9)."""

import pytest
from atlas_api.testing import build_test_app, make_client


@pytest.mark.asyncio
async def test_deployments_and_rollback_api():
    app = build_test_app()
    async with make_client(app) as client:
        # 1. Record deployment
        dep_resp = await client.post(
            "/v1/infrastructure/deployments",
            json={
                "service_name": "atlas-api",
                "environment": "production",
                "git_commit_sha": "1234567890abcdef1234567890abcdef12345678",
                "image_tag": "ghcr.io/atlas-org/atlas-api:v1.2.0",
                "replicas_count": 6,
                "rollout_strategy": "CANARY",
                "canary_weight": 15,
            },
        )
        assert dep_resp.status_code == 200
        dep_data = dep_resp.json()
        assert dep_data["service_name"] == "atlas-api"
        assert dep_data["status"] == "DEPLOYING"
        dep_id = dep_data["id"]

        # 2. List deployments
        list_resp = await client.get("/v1/infrastructure/deployments")
        assert list_resp.status_code == 200
        assert any(d["id"] == dep_id for d in list_resp.json())

        # 3. Rollback deployment
        rb_resp = await client.post(f"/v1/infrastructure/deployments/{dep_id}/rollback")
        assert rb_resp.status_code == 200
        assert rb_resp.json()["status"] == "ROLLED_BACK"


@pytest.mark.asyncio
async def test_health_probes_and_capacity_api():
    app = build_test_app()
    async with make_client(app) as client:
        # Ingest health probe
        probe_resp = await client.post(
            "/v1/infrastructure/health/probes",
            json={
                "service_name": "atlas-worker",
                "pod_id": "worker-pool-88a",
                "probe_type": "KAFKA_LAG",
                "status": "HEALTHY",
                "latency_ms": 6,
            },
        )
        assert probe_resp.status_code == 200
        p_data = probe_resp.json()
        assert p_data["probe_type"] == "KAFKA_LAG"
        assert p_data["latency_ms"] == 6

        # List recent probes
        list_resp = await client.get("/v1/infrastructure/health/probes?limit=10")
        assert list_resp.status_code == 200
        assert len(list_resp.json()) >= 1

        # Get cluster capacity
        cap_resp = await client.get("/v1/infrastructure/capacity")
        assert cap_resp.status_code == 200
        cap_data = cap_resp.json()
        assert cap_data["active_nodes"] >= 1
        assert cap_data["total_cpu_cores"] > 0


@pytest.mark.asyncio
async def test_incidents_lifecycle_api():
    app = build_test_app()
    async with make_client(app) as client:
        # 1. Create incident
        inc_resp = await client.post(
            "/v1/infrastructure/incidents",
            json={
                "title": "PostgreSQL Replica Replication Delay",
                "severity": "P1_HIGH",
                "affected_component": "PostgreSQL-Standby",
                "alert_source": "Prometheus",
            },
        )
        assert inc_resp.status_code == 200
        inc_data = inc_resp.json()
        assert inc_data["severity"] == "P1_HIGH"
        inc_id = inc_data["id"]

        # 2. Resolve incident
        res_resp = await client.post(
            f"/v1/infrastructure/incidents/{inc_id}/resolve",
            json={
                "root_cause": "Network saturation on inter-AZ cross-connect",
                "mitigation_steps": "Increased provisioned network bandwidth on primary VPC peering",
            },
        )
        assert res_resp.status_code == 200
        assert res_resp.json()["resolved_at"] is not None
        assert "inter-AZ" in res_resp.json()["root_cause"]
