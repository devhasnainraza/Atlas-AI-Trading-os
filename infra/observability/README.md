# Observability provisioning (Spec 00 §12, US3)

Dashboards and alert rules as code, shipped with kube-prometheus-stack in M6. Contract
fixed now so runbooks and alerts stay in lockstep:

| Dashboard | Panels |
|---|---|
| API overview | RED per route (rate, errors, duration p50/p95), readiness status |
| Event bus | publish throughput, consumer lag, retry rate, **DLQ depth** |
| Workers | outbox relay rate, task states, duration |
| Scheduler | last-run per job, missed runs |

| Alert | Threshold | Runbook |
|---|---|---|
| ApiErrorRateHigh | 5xx > 1% for 5m | docs/runbooks/platform-foundation.md#api-errors |
| ApiLatencyHigh | p95 > 1s for 10m | …#api-latency |
| ReadinessFailing | ready=false for 60s (SC-007) | …#dependency-outage |
| DlqDepthNonZero | DLQ > 0 for 10m | …#dead-letters |
| ConsumerLagGrowing | lag increasing 15m | …#consumer-lag |
| SchedulerJobMissed | missed run detected | …#scheduler |

Every alert names its runbook anchor — an alert without a runbook fails review.
