# Terraform scaffolds (Spec 00 §17)

Environment infrastructure as code. Populated in M6 (cloud milestone); layout fixed now:

```text
infra/terraform/
├── modules/
│   ├── cluster/      # managed K8s cluster + node pools
│   ├── database/     # managed Postgres 16 + pgvector, PITR backups
│   ├── redis/        # managed Redis 7
│   ├── kafka/        # managed Kafka (or Redpanda cloud) + topic provisioning
│   ├── storage/      # S3 buckets (uploads, artifacts, observability chunks)
│   └── secrets/      # secret-manager entries + External Secrets wiring
└── envs/
    ├── development/
    ├── staging/
    └── production/   # each: backend.tf (remote state + locking), main.tf composing modules
```

Rules: remote state with locking; `terraform validate` + `plan` run in CI on infra PRs;
no cloud-vendor-proprietary services on the critical path (cloud-agnostic requirement).
