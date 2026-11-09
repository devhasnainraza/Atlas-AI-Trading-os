# Tasks: Production Infrastructure

**Input**: Design documents from `/specs/spec-11-infrastructure/`
**Prerequisites**: [spec.md](./spec.md), Dockerfiles, Helm charts (`infra/k8s/`), Terraform (`infra/terraform/`)
**Tests**: INCLUDED — disaster recovery failover drill, Kubernetes HPA load tests, and zero-downtime canary deployment verification.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: `US1`–`US3`, or blank for setup/foundational/polish

---

## Phase 1: Setup

- [x] T001 [P] Structure Terraform AWS root module (`infra/terraform/main.tf`, `variables.tf`, `outputs.tf`)
- [x] T002 [P] Configure multi-stage production Dockerfiles with non-root security contexts in `infra/docker/`
- [x] T003 [P] Configure GitHub Actions CI/CD workflow (`.github/workflows/deploy-production.yaml`) with Trivy container scans

---

## Phase 2: Foundational (⚠️ CRITICAL — blocks every user story)

- [x] T004 Provision Amazon VPC with public, private, and database subnets across 3 Availability Zones via Terraform
- [x] T005 [P] Provision AWS Aurora PostgreSQL 16 cluster with `pgvector` and multi-AZ failover
- [x] T006 [P] Provision AWS MSK Kafka cluster (or self-hosted Redpanda) with 3 brokers and retention policies
- [x] T007 [P] Provision Amazon ElastiCache Redis 7 replication group with in-transit encryption

---

## Phase 3: User Story 1 — Self-Healing Kubernetes Topology & HPA (Priority: P1) 🎯 MVP

**Goal**: Amazon EKS cluster orchestrating API, web, worker, and ingestion pods with automatic pod rescheduling and horizontal scaling.

### Tests for User Story 1 ⚠️ write first, must fail

- [x] T008 [P] [US1] Chaos test: Simulated node failure reschedules pods on healthy nodes within 15 seconds
- [x] T009 [P] [US1] Load test: Simulated traffic spike scales API deployment from 4 to 12 replicas in < 45 seconds

### Implementation for User Story 1

- [x] T010 [US1] Provision Amazon EKS cluster with Karpenter node autoscaler via Terraform in `infra/terraform/modules/eks/`
- [x] T011 [US1] Author Helm chart for `atlas-api` with HPA (CPU 70%, Memory 75%) and Pod Disruption Budgets
- [x] T012 [US1] Author Helm chart for `atlas-ingestion` dedicated to persistent broker WebSocket streams
- [x] T013 [US1] Author Helm chart for `atlas-worker` scaling on Kafka consumer group lag

---

## Phase 4: User Story 2 — GitOps Zero-Downtime Canary Delivery (Priority: P1)

**Goal**: ArgoCD automates progressive canary rollouts to production with automated health and error-rate verification.

### Tests for User Story 2 ⚠️ write first, must fail

- [x] T014 [P] [US2] Deployment test: Canary release shifts 10% traffic, monitors `/health/ready`, and completes 100% rollout with zero 5xx errors
- [x] T015 [P] [US2] Rollback test: Simulated 5xx error spike during canary automatically aborts and rolls back within 30 seconds

### Implementation for User Story 2

- [x] T016 [US2] Configure ArgoCD application and Rollout CRD in `infra/k8s/gitops/argo-rollout.yaml`
- [x] T017 [US2] Configure Cloudflare WAF and AWS Application Load Balancer with TLS 1.3 termination
- [x] T018 [US2] Wire GitHub Actions automated image tagging and GitOps commit triggers

---

## Phase 5: User Story 3 — Full-Stack Observability & SRE Alerting (Priority: P1)

**Goal**: Prometheus and Grafana monitor sub-second latency across APIs and venues; PagerDuty pages on-call engineers on broker connection drops.

### Tests for User Story 3 ⚠️ write first, must fail

- [x] T019 [P] [US3] Unit test: Simulated broker latency > 2,000ms triggers Prometheus P0 alert rule
- [x] T020 [P] [US3] Integration test: OpenTelemetry traces propagate W3C headers across API, worker, and database

### Implementation for User Story 3

- [x] T021 [US3] Deploy Prometheus Operator and Grafana dashboards (Order Flow, Venue Health, Latency) in `infra/k8s/observability/`
- [x] T022 [US3] Configure Alertmanager routing rules with PagerDuty integration for P0 emergency alerts
- [x] T023 [US3] Publish SRE Runbooks for Database Failover and Venue Outages in `docs/runbooks/`

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T024 [P] Istio mutual TLS (mTLS) service mesh configuration enforcing strict pod-to-pod encryption
- [ ] T025 [P] Annual Disaster Recovery failover simulation verifying RTO < 15 minutes and RPO < 1 minute
