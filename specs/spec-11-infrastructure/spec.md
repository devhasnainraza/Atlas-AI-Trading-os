# Spec 11 — Production Infrastructure

**Project**: Atlas AI Trading OS  
**Status**: Ratified | **Version**: 1.0.0 | **Date**: 2026-09-21  
**Target Path**: `specs/spec-11-infrastructure/`  
**Constitutional Compliance**: Core Principles II, IX, XI, XII Verified  

---

## 1. Vision & Goals

### 1.1 System Vision
Spec 11 specifies the production infrastructure, DevOps deployment automation, high-availability data topologies, and Site Reliability Engineering (SRE) architecture for Atlas AI Trading OS. Trading platforms operate under zero-tolerance conditions: a single minute of unexpected downtime during a market breakout or an unobserved consumer lag spike can result in severe financial damage. Spec 11 guarantees a highly available, auto-scaling, fault-tolerant cloud architecture built to support thousands of concurrent traders with sub-second resilience.

### 1.2 Core Business & Technical Goals
- **High-Availability Data Core**: Multi-AZ PostgreSQL 16 cluster with `pgvector` managed via Patroni/RDS Aurora with automated read replicas and sub-second failover.
- **Distributed Event Streaming Mesh**: Multi-broker Apache Kafka / Redpanda cluster with replication factor 3, handling market data feeds and asynchronous agent events with zero data loss.
- **In-Memory Telemetry & State Cache**: High-availability Redis 7 cluster providing sub-millisecond session caching, rate limiting, and real-time WebSocket pub/sub fan-out.
- **Elastic Cloud-Native Orchestration**: Amazon Elastic Kubernetes Service (EKS) / GKE with automated node provisioning (Karpenter), Horizontal Pod Autoscaling (HPA), and Pod Disruption Budgets (PDB).
- **GitOps Continuous Delivery**: Automated CI/CD pipelines via GitHub Actions and ArgoCD ensuring that every pull request passes linting, unit, contract, and security scans before zero-downtime canary deployment.
- **Comprehensive Observability & SRE Runbooks**: Full-stack telemetry powered by OpenTelemetry, Prometheus, Grafana, and Jaeger, paired with concrete automated runbooks for disaster recovery and network partition mitigation.

---

## 2. Functional Requirements

- **FR-001**: The production topology MUST support independent scaling of core workloads:
  - `atlas-api`: Stateless FastAPI web application pods (HPA scale on CPU/Request count).
  - `atlas-web`: Next.js 15 App Router SSR & static frontends.
  - `atlas-worker`: Distributed Celery/Kafka worker pods executing agent workflows and event relays.
  - `atlas-scheduler`: Redundant Celery Beat leader-elected pods executing scheduled recurring tasks.
  - `atlas-ingestion`: Dedicated high-network pods maintaining persistent broker WebSockets and market data streams.
- **FR-002**: Database architecture MUST provide automated daily snapshots, point-in-time recovery (PITR) with a 35-day retention window, and read/write connection splitting.
- **FR-003**: Kafka event streaming MUST configure partitioned topics (`atlas.market.*`, `atlas.trading.*`, `atlas.agents.*`) with retention policies tuned for low-latency streaming and historical replay.
- **FR-004**: Infrastructure as Code (IaC) MUST be defined using modular Terraform scripts managing VPC, subnets, EKS clusters, RDS instances, ElastiCache, S3 buckets, and IAM roles.
- **FR-005**: All ingress traffic MUST pass through Cloudflare / AWS CloudFront with WAF (Web Application Firewall), DDoS protection, and TLS 1.3 termination.
- **FR-006**: Secret management MUST use AWS Secrets Manager / HashiCorp Vault with automated rotation and zero secret exposure in Kubernetes manifests or environment logs.
- **FR-007**: SRE monitoring MUST enforce automated alert thresholds for:
  - API p95 latency > 100ms for 2 minutes (P1 Alert).
  - Kafka consumer group lag > 500 messages (P1 Alert).
  - Venue adapter connection drop (P0 Emergency Alert).
  - Pod crash looping or memory pressure > 85% (P1 Alert).

---

## 3. Non-Functional Requirements

- **NFR-001 (High Availability SLA)**: The production infrastructure MUST achieve 99.95% system uptime (< 21.9 minutes unplanned downtime per month).
- **NFR-002 (Disaster Recovery RPO & RTO)**:
  - Recovery Point Objective (RPO) < 1 minute (minimal transactional loss via WAL streaming).
  - Recovery Time Objective (RTO) < 15 minutes (automated failover to standby replica/region).
- **NFR-003 (Auto-Scaling Speed)**: The Kubernetes cluster MUST scale out additional worker and API replicas within 45 seconds of traffic spike detection.
- **NFR-004 (Log Retention & Auditing)**: Operational logs MUST be retained for 90 days in hot storage and 365 days in cold S3 storage for compliance auditing.

---

## 4. User Stories

### US-001: Automated Self-Healing During Node Failure (Priority: P1)
- **Given** a physical hardware failure in an AWS availability zone hosting active trading workers,
- **When** the node becomes unreachable,
- **Then** Kubernetes Pod Disruption Budgets and Patroni failover immediately reschedule pods on healthy nodes, Kafka consumer groups rebalance, and order routing resumes within 12 seconds with zero dropped orders.

### US-002: Seamless Zero-Downtime Deployment (Priority: P1)
- **Given** a new release of `atlas-api` containing updated agent prompts,
- **When** ArgoCD synchronizes the new container image,
- **Then** a rolling update initializes new pods, passes `/health/ready` readiness checks, shifts traffic incrementally, and terminates old pods with zero dropped connections.

### US-003: Automated Alert Pagers During Broker Latency Spike (Priority: P1)
- **Given** Binance or MetaTrader broker API roundtrip latency spiking to 2,500ms,
- **When** Prometheus detects the threshold breach for 3 consecutive scrapes,
- **Then** PagerDuty immediately pages the on-call SRE engineer while the Pre-Trade Risk Gate automatically enters degraded latency mode.

---

## 5. Infrastructure Architecture

```text
                                [Internet Clients]
                                        |
                                        v
                            [Cloudflare CDN & WAF]
                                        |
                                        v (TLS 1.3)
                       [AWS Application Load Balancer]
                                        |
+---------------------------------------v---------------------------------------+
|                       Amazon EKS Cluster (Kubernetes)                         |
|                                                                               |
|  +--------------------+   +---------------------+   +----------------------+  |
|  |     atlas-api      |   |      atlas-web      |   |   atlas-ingestion    |  |
|  |   (FastAPI Pods)   |   |   (Next.js SSR)     |   |   (WebSocket Pods)   |  |
|  +---------+----------+   +----------+----------+   +----------+-----------+  |
|            |                         |                         |              |
|            +-------------------------+-------------------------+              |
|                                      |                                        |
|                         +------------v------------+                           |
|                         |      atlas-worker       |                           |
|                         |  (Celery / LangGraph)   |                           |
|                         +------------+------------+                           |
+--------------------------------------|----------------------------------------+
                                       |
        +------------------------------+------------------------------+
        |                              |                              |
        v                              v                              v
+------------------+          +------------------+          +-------------------+
|  AWS Aurora PG16 |          |  Redis 7 Cluster |          |  Kafka / Redpanda |
|  + pgvector (HA) |          |  (ElastiCache)   |          |  (Cluster MSK)    |
+------------------+          +------------------+          +-------------------+
```

---

## 6. Kubernetes Topology & Specifications

### 6.1 Core API Deployment Manifest (`infra/k8s/api-deployment.yaml`)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: atlas-api
  namespace: production
  labels:
    app: atlas-api
spec:
  replicas: 4
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 25%
      maxUnavailable: 0
  selector:
    matchLabels:
      app: atlas-api
  template:
    metadata:
      labels:
        app: atlas-api
    spec:
      containers:
      - name: api
        image: ghcr.io/atlas-trading/api:v1.0.0
        ports:
        - containerPort: 8000
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "2000m"
            memory: "2048Mi"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

---

## 7. Observability & SRE Metrics

### 7.1 Key SRE Prometheus Metrics
- `atlas_http_requests_total{status, route}`: Request counter.
- `atlas_http_request_duration_seconds_bucket`: API latency histogram.
- `atlas_trading_order_execution_latency_ms`: Time from intent receipt to venue ack.
- `atlas_kafka_consumer_lag_records{topic, consumergroup}`: Consumer lag monitor.
- `atlas_agent_node_execution_seconds`: LangGraph node duration.

---

## 8. Disaster Recovery & Runbooks

### Runbook 01: Database Primary Failover
1. Automated: Patroni elects new primary within 10 seconds.
2. Manual (if auto fails): Run `patronictl -c /etc/patroni/db.yml failover`.
3. Verify connection pool reconnection in `atlas-api` logs.
4. Execute `scripts/db/check-integrity` to confirm zero sequence corruption.

### Runbook 02: Venue Adapter Disconnection
1. Pre-Trade Risk Gate automatically places degraded hold on affected venue.
2. Check external venue status page via `scripts/venues/probe-status <venue>`.
3. If venue is healthy, restart ingestion pod: `kubectl rollout restart deployment/atlas-ingestion`.
4. Trigger continuous reconciliation run to verify active position state.

---

## 9. Security & Network Hardening

- **SEC-001 (Private VPC Isolation)**: Database, Redis, and Kafka clusters are deployed in strictly isolated private VPC subnets with zero public internet gateways.
- **SEC-002 (mTLS Internal Service Mesh)**: Inter-pod communication is secured using Istio / Linkerd mutual TLS encryption.
- **SEC-003 (Kubernetes RBAC & Network Policies)**: Pods run under dedicated Kubernetes ServiceAccounts with least-privilege IAM roles (IRSA). Default-deny network policies restrict ingress to authorized ports.

---

## 10. CI/CD Pipeline

```text
[Git Push to Main]
        |
        v
+-----------------------------+
| GitHub Actions: Lint & Test |  (Ruff, mypy, import-linter, pytest, Schemathesis)
+--------------+--------------+
               |
               v
+-----------------------------+
| Security Vulnerability Scan |  (Trivy container scan, Gitleaks secret detection)
+--------------+--------------+
               |
               v
+-----------------------------+
| Multi-Arch Docker Image Build| (Buildx, pushes signed image to GHCR)
+--------------+--------------+
               |
               v
+-----------------------------+
| ArgoCD Canary Deployment    |  (Automated rollouts to EKS with health verification)
+-----------------------------+
```

---

## 11. Deployment Plan

- **Phase 1: Foundation Provisioning**: Terraform provision of VPC, Subnets, EKS, RDS Aurora, ElastiCache Redis, and MSK Kafka.
- **Phase 2: Base Services Bootstrap**: Deploy cert-manager, ExternalDNS, Istio service mesh, and Prometheus/Grafana operator.
- **Phase 3: Workload Rollout**: Deploy `atlas-api`, `atlas-web`, `atlas-worker`, `atlas-scheduler`, and `atlas-ingestion`.

---

## 12. Future Enhancements

- **Multi-Region Disaster Recovery**: Active-Passive warm standby deployed in secondary AWS region with automated DNS route failover.
- **Dedicated Co-Located Bare Metal Nodes**: Ultra-low latency bare-metal instances positioned inside Equinix NY4 / LD4 financial data centers for sub-millisecond execution.
