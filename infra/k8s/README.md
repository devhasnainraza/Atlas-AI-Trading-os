# Kubernetes deployment scaffolds (Spec 00 §16)

Helm charts for the four deployable units. Populated chart-by-chart in M6 (cloud
deployment milestone); the structure and values contract are fixed now so CI can validate
`helm template` from the first cloud PR.

```text
infra/k8s/
├── atlas-api/        # Deployment, Service, HPA, probes → /v1/health/*
├── atlas-web/        # Deployment, Service
├── atlas-worker/     # Deployment (KEDA scaling on consumer lag later)
├── atlas-scheduler/  # Deployment, 1 replica + leader election
└── values/           # per-environment values (dev/staging/prod) — no secrets ever
```

Rules (plan §16): probes wired to health endpoints; resource requests/limits mandatory;
secrets via External Secrets Operator only — never in values files.
