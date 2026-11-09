# Implementation Plan: Enterprise Features

**Branch**: `10-enterprise` | **Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/spec-10-enterprise/spec.md`

## Summary

Deliver Atlas's institutional enterprise operating system: elevating the platform for hedge funds, prop trading desks, syndicates, and wealth managers. Features multi-tenant organizational hierarchies with strict PostgreSQL Row-Level Security (RLS), hierarchical Role-Based Access Control (`Org_Owner`, `Risk_Officer`, `Fund_Manager`, `Senior_Trader`, `Junior_Trader`, `Compliance_Auditor`), collaborative agent workspaces with pooled capital allocations, top-down risk policies with dual-approval execution gates, high-throughput developer APIs with HMAC-signed webhooks, white-label branding customization, and Stripe Billing with metered seat and token usage.

## Technical Context

**Language/Version**: Python 3.12 (enterprise IAM, risk policy enforcement, webhook dispatchers in `apps/api`), TypeScript 5.x / Next.js 15 (enterprise admin console, team management, compliance explorer in `apps/web`)  
**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2 (async) + Alembic, stripe (Stripe Billing & Metered Usage API), python-jose / PyJWT[crypto] (SAML 2.0 / Enterprise OIDC connectors), aiohttp (enterprise webhook dispatcher), Redis 7 (tenant rate limit buckets & RLS session cache), reportlab / pandas (regulatory compliance export packages)  
**Storage**: PostgreSQL 16 with Row-Level Security enabled (organizations, teams, memberships, enterprise risk policies, compliance audit chains, webhook registrations), Redis 7 (tenant-specific rate limit tokens, active session caches), Kafka (`atlas.enterprise.*` topics)  
**Testing**: pytest-asyncio, multi-tenant database leakage fuzzing, testcontainers (Postgres with active RLS policies), mock Stripe webhook listeners, Schemathesis (enterprise developer API contracts)  
**Target Platform**: Multi-tenant Kubernetes cluster with dedicated node pool routing for premium enterprise tenants  
**Performance Goals**: Enterprise API throughput 1,000 req/sec per tenant at < 20ms p95; outbound webhook delivery < 250ms of event; compliance export generation < 5s; RLS policy query overhead < 1ms  
**Constraints**: Zero cross-tenant data leakage under all failure modes; tamper-evident SHA-256 chained compliance audit trail; enterprise risk ceilings non-bypassable by junior staff; SAML/SSO compatibility  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Compliance in this plan | Status |
|---|-----------|------------------------|--------|
| I | Human First | Institutional dual-approval workflows mandate senior trader or risk officer sign-off on outsized orders. | ✅ |
| II | Security First | PostgreSQL Row-Level Security (RLS) guarantees cryptographic tenant isolation; SAML 2.0/Okta enterprise SSO supported. | ✅ |
| III | Transparency | Compliance audit logs record actor, timestamp, IP, full debate transcripts, and approval tokens for every trade. | ✅ |
| IV | Multi-Agent Collab | Teams share collaborative agent clusters with shared context and coordinated position limits. | ✅ |
| V | Explainability | Risk vetoes and dual-approval requirements surface explicit rule IDs and policy thresholds. | ✅ |
| VI | Risk Before Profit | Organization-wide daily drawdown caps override all team and individual strategies; desk-wide kill switch. | ✅ |
| VII | Continuous Learning | Aggregated team trading statistics feed institutional coaching models while maintaining individual privacy. | ✅ |
| VIII | Privacy by Design | Strict RLS and schema separation guarantee complete data isolation between corporate tenants. | ✅ |
| IX | Reliability | Webhook delivery utilizes exponential backoff retries and Dead-Letter Queue logging; high-availability compute pools. | ✅ |
| X | Modular Architecture | Enterprise layer builds upon foundation modules via standard public service interfaces and events. | ✅ |
| XI | Observability | Tenant-level API quotas, token consumption rates, and error frequencies exported to Prometheus. | ✅ |
| XII | Scalability | Horizontal scaling of tenant worker pools; partitioned audit tables handle millions of regulatory events. | ✅ |

**Gate result**: PASS.

## 1. High-Level Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│ Enterprise Ingress: CNAME White-Label / API Keys / OAuth 2.0 / SAML    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Enterprise Gateway & RBAC Layer (apps/api/enterprise)                  │
│  - Sets `app.current_org_id` context variable in PostgreSQL            │
│  - Enforces Role Permissions (Org_Owner -> Junior_Trader)              │
│  - Rate Limiter & Token Usage Meter (Stripe Billing Integration)       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ PostgreSQL 16 (Row-Level Security Active)                              │
│  - Tables: enterprise_organizations, teams, memberships, audit_chain   │
│  - RLS Policy: `USING (org_id = current_setting('app.current_org_id'))`│
└───────┬───────────────────────────────────────┬────────────────────────┘
        │                                       │
        ▼                                       ▼
┌───────────────────────────────┐       ┌────────────────────────────────┐
│ Hierarchical Risk Engine      │       │ Enterprise Webhook Engine      │
│  - Org Max Daily Drawdown     │       │  - Real-time event subscription│
│  - Team Capital Allocations   │       │  - HMAC-SHA256 signature sign  │
│  - Dual-Approval Routing Gate │       │  - Retries with Dead-Letter Q  │
└───────┬───────────────────────┘       └────────────────────────────────┘
        │
        ▼
┌────────────────────────────────────────────────────────────────────────┐
│ LangGraph Enterprise Workflow: Dual-Approval Interrupt Node           │
│  - Order > Junior Lot Limit -> Halts for Senior Trader Signature       │
└────────────────────────────────────────────────────────────────────────┘
```

## 2. Directory Structure

```text
specs/spec-10-enterprise/
├── spec.md              # Specification document
├── plan.md              # This architecture plan
├── data-model.md        # Data models (organizations, teams, webhooks, audit)
└── tasks.md             # Test-first task breakdown
```

## 3. Core Technical Decisions & Rationale

### ADR-10-01: PostgreSQL Row-Level Security (RLS) for Tenant Isolation
- **Context**: Enterprise clients require absolute isolation of trading strategies, journal entries, and broker credentials. A simple application-level `WHERE org_id = ...` is prone to developer oversight.
- **Decision**: Enforce PostgreSQL Row-Level Security (RLS) on all tenant-bearing tables, automatically keyed to `current_setting('app.current_org_id')`.
- **Consequences**: Impossible to query or mutate another organization's records even if application code omits an explicit filter.

### ADR-10-02: Cryptographic Tamper-Evident Audit Chain
- **Context**: Financial regulators and institutional auditors require proof that trade logs, agent debates, and risk approvals have not been manipulated retroactively.
- **Decision**: Maintain a cryptographically chained audit log (`previous_hash` + SHA-256 of current record) in `enterprise_compliance_audit_logs`.
- **Consequences**: Any manual database alteration immediately invalidates the cryptographic hash chain, providing verifiable compliance evidence.

### ADR-10-03: Dual-Approval Workflow via LangGraph Interrupts
- **Context**: Prop firms require senior oversight when junior traders or automated bots attempt unusually large positions.
- **Decision**: If proposed order size > trader tier authorization limit, LangGraph pauses at `senior_approval` node, generating an interactive ticket for Senior Traders and Risk Officers.
- **Consequences**: Full institutional risk governance without halting unrelated trades.
