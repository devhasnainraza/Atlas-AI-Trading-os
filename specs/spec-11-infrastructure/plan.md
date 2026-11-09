# Implementation Plan: Production Infrastructure

**Branch**: `11-infrastructure` | **Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/spec-11-infrastructure/spec.md`

## Summary

Deliver Atlas's enterprise production cloud architecture, continuous deployment pipelines, high-availability data topologies, and Site Reliability Engineering (SRE) operations. Implements an auto-scaling Amazon EKS / Kubernetes deployment (Karpenter, HPA, PDB), multi-AZ PostgreSQL 16 with Aurora/Patroni and `pgvector`, distributed Apache Kafka / Redpanda event mesh (replication factor 3), clustered Redis 7 (ElastiCache), Cloudflare WAF / AWS ALB ingress with TLS 1.3, GitOps CD via GitHub Actions & ArgoCD, and full-stack OpenTelemetry / Prometheus / Grafana observability with automated SRE disaster recovery runbooks.

## Technical Context

**Language/Version**: Terraform / OpenTofu (IaC in `infra/terraform`), YAML / Kustomize / Helm (Kubernetes manifests in `infra/k8s`), Bash / Python (SRE automation scripts), GitHub Actions Workflows  
**Primary Dependencies**: AWS EKS / Karpenter, AWS Aurora PostgreSQL 16 + pgvector, AWS ElastiCache Redis 7, AWS MSK / Redpanda Kafka, Cloudflare WAF, ArgoCD, Prometheus Operator, Grafana, OpenTelemetry Collector, cert-manager, Istio / Linkerd mTLS  
**Storage**: AWS Aurora Multi-AZ PostgreSQL 16 (system of record + vectors), S3 (backups, compliance archives, chart images), ElastiCache Redis 7 (hot cache & WebSocket fan-out), Kafka/MSK (durable event log)  
**Testing**: Terraform validate / tflint / tfsec, kube-linter / kubeval, k6 load & stress testing (10,000 req/sec), Chaos Mesh (AZ partition, pod kills, network latency injection), Trivy container vulnerability scanning  
**Target Platform**: AWS Cloud (Production) / Docker Compose (Local Dev Parity)  
**Performance Goals**: 99.95% availability SLA (< 21.9 min unplanned downtime/mo); RPO < 1 min, RTO < 15 min; cluster auto-scale out < 45s; API p95 < 100ms; zero packet drop during Kafka broker rebalances  
**Constraints**: Zero secrets in Git or container images (AWS Secrets Manager / Vault); mTLS enforced on all inter-pod traffic; all databases in isolated private subnets with no public IP routes; immutable audit logging  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Compliance in this plan | Status |
|---|-----------|------------------------|--------|
| I | Human First | SRE runbooks empower engineers with manual override capabilities, blue/green rollbacks, and kill switches. | ✅ |
| II | Security First | Private subnets, mTLS service mesh, Cloudflare WAF, automated secrets rotation, and strict Kubernetes network policies. | ✅ |
| III | Transparency | Comprehensive OpenTelemetry distributed tracing and Prometheus metrics provide 100% visibility into system performance. | ✅ |
| IV | Multi-Agent Collab | Dedicated Kafka topics and Kubernetes worker pools provide scalable compute substrate for 13-agent mesh. | ✅ |
| V | Explainability | Pod events, deployments, and cluster autoscaling actions are tracked with immutable audit trails. | ✅ |
| VI | Risk Before Profit | Broker latency spikes or venue disconnection automatically trigger Pre-Trade Risk Gate routing holds. | ✅ |
| VII | Continuous Learning | Performance metrics, crash dumps, and latency traces are stored for post-incident reviews and capacity modeling. | ✅ |
| VIII | Privacy by Design | Backup archives encrypted with AWS KMS; S3 buckets enforce default-deny public access and automated lifecycle policies. | ✅ |
| IX | Reliability | Core implementation of Principle IX: Multi-AZ database clustering, Patroni automated failover, and zero-downtime rolling updates. | ✅ |
| X | Modular Architecture | Decoupled workloads (`atlas-api`, `atlas-web`, `atlas-worker`, `atlas-ingestion`) scale independently. | ✅ |
| XI | Observability | End-to-end telemetry (metrics, structured logs, distributed traces) built-in from day one. | ✅ |
| XII | Scalability | Horizontal Pod Autoscaling (HPA) and Karpenter dynamic node provisioning scale compute from tens to thousands of users. | ✅ |

**Gate result**: PASS.

## 1. High-Level Architecture

```text
                                 [Internet Clients]
                                         │
                                         ▼
                            [Cloudflare CDN & WAF]
                                         │
                                         ▼ (TLS 1.3)
                        [AWS Application Load Balancer]
                                         │
+----------------------------------------v---------------------------------------+
|                       Amazon EKS Cluster (Kubernetes)                          |
|                                                                                |
|  +--------------------+   +---------------------+   +----------------------+   |
|  |     atlas-api      |   |      atlas-web      |   |   atlas-ingestion    |   |
|  |   (FastAPI Pods)   |   |   (Next.js SSR)     |   |   (WebSocket Pods)   |   |
|  +---------+----------+   +----------+----------+   +----------+-----------+   |
|            │                         │                         │               |
|            +-------------------------+-------------------------+               |
|                                      │                                         |
|                         +------------v------------+                            |
|                         |      atlas-worker       |                            |
|                         |  (Celery / LangGraph)   |                            |
|                         +------------+------------+                            |
+--------------------------------------|-----------------------------------------+
                                       │
        +------------------------------+------------------------------+
        │                              │                              │
        ▼                              ▼                              ▼
+------------------+          +------------------+          +-------------------+
|  AWS Aurora PG16 |          |  Redis 7 Cluster |          |  Kafka / Redpanda |
|  + pgvector (HA) |          |  (ElastiCache)   |          |  (Cluster MSK)    |
+------------------+          +------------------+          +-------------------+
```

## 2. Directory Structure

```text
specs/spec-11-infrastructure/
├── spec.md              # Specification document
├── plan.md              # This architecture plan
├── data-model.md        # Data models (deployments, alerts, runbooks)
└── tasks.md             # Test-first task breakdown
```

## 3. Core Technical Decisions & Rationale

### ADR-11-01: Karpenter Node Autoscaling over Standard Cluster Autoscaler
- **Context**: Trading workloads spike unpredictably during economic events (CPI, FOMO breakouts); standard Kubernetes Cluster Autoscaler takes 3-5 minutes to provision new nodes.
- **Decision**: Adopt Karpenter for dynamic, just-in-time EC2 instance provisioning directly launching right-sized compute in < 45 seconds.
- **Consequences**: Rapid elasticity under sudden volatility surges; optimizes infrastructure cloud costs by terminating idle compute.

### ADR-11-02: Isolated Ingestion Pods with Dedicated Network Interfaces
- **Context**: Ingestion workers streaming thousands of ticks/sec via WebSockets can saturate pod network bandwidth and degrade REST API response times if co-located.
- **Decision**: Deploy `atlas-ingestion` as a distinct Kubernetes deployment with dedicated node selectors, high-throughput network configurations, and isolated CPU cores.
- **Consequences**: Guarantees zero dropped ticks or socket starvation during extreme market volume.

### ADR-11-03: GitOps Zero-Downtime Canary Deployments via ArgoCD
- **Context**: Manual updates to trading execution software risk catastrophic outages or execution errors mid-session.
- **Decision**: Implement ArgoCD canary rollouts with automated metric analysis (error rate < 0.1%, latency < 100ms) before 100% traffic shift.
- **Consequences**: Automatic, instantaneous rollback if a new release exhibits errors; eliminates maintenance windows.
