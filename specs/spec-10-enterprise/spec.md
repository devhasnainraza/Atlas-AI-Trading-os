# Spec 10 — Enterprise Features

**Project**: Atlas AI Trading OS  
**Status**: Ratified | **Version**: 1.0.0 | **Date**: 2026-09-21  
**Target Path**: `specs/spec-10-enterprise/`  
**Constitutional Compliance**: Core Principles I, II, VIII, X, XII Verified  

---

## 1. Vision & Goals

### 1.1 System Vision
Spec 10 elevates Atlas AI Trading OS from an individual trader workstation to an institutional enterprise operating system. Hedge funds, proprietary trading firms, trading syndicates, and wealth management desks require multi-tenant organizational hierarchies, collaborative multi-agent execution, pooled risk budgets, white-label branding, enterprise webhooks, and granular compliance audits. Spec 10 provides these institutional capabilities while ensuring absolute tenant isolation and auditability.

### 1.2 Core Business & Technical Goals
- **Multi-Tenant Organization & Team Hierarchy**: Granular organization model supporting Teams, Workspaces, and hierarchical Role-Based Access Control (`Org_Owner`, `Risk_Officer`, `Fund_Manager`, `Senior_Trader`, `Junior_Trader`, `Auditor`).
- **Collaborative Multi-Agent Workspaces**: Team-shared AI trading agents, proprietary team-curated strategies, and pooled capital allocations with unified pre-trade risk controls.
- **Pooled Capital & Multi-Tier Risk Governance**: Centralized Risk Officer controls setting top-down portfolio risk policies (e.g. "Total desk drawdown cannot exceed 4.0%", "Junior traders capped at 0.5% risk per trade").
- **Institutional API & Webhook Infrastructure**: High-throughput authenticated REST/WebSocket endpoints and HMAC-signed outbound webhooks for algorithmic integration into existing fund infrastructure.
- **White-Label Custom Branding**: Complete customization enabling institutional clients and brokerages to deploy Atlas with custom domain names, corporate logos, localized languages, and bespoke color palettes.
- **Subscription Billing & Metered Usage**: Robust billing engine integrated with Stripe Billing, managing tiered subscriptions and metering agent token consumption and venue connection seats.

---

## 2. Functional Requirements

- **FR-001**: The platform MUST support multi-tenant Organizations with distinct isolation boundaries across databases, caches, and memory vector stores.
- **FR-002**: Organization owners MUST be able to create Teams and Workspaces, invite members via email, and assign institutional roles (`Org_Owner`, `Risk_Officer`, `Portfolio_Manager`, `Trader`, `Compliance_Auditor`).
- **FR-003**: The platform MUST allow teams to create Shared Trading Agents and Shared Strategy Graphs with collaborative access policies.
- **FR-004**: The Risk Engine MUST enforce Hierarchical Risk Policies:
  - Organization-wide daily drawdown caps.
  - Team-level capital allocation limits.
  - Individual trader lot and risk ceilings.
  - Mandatory dual-approval workflows (e.g. Junior trader order exceeding 2 lots requires Senior Trader sign-off).
- **FR-005**: The platform MUST expose an **Enterprise Developer API** authenticated via scoped API Keys or OAuth 2.0 Client Credentials with dedicated rate-limiting tiers.
- **FR-006**: Outbound webhooks MUST deliver real-time system events (`trade.executed`, `risk.limit_breached`, `mandate.halted`) with HMAC-SHA256 signature verification and automatic retry policies.
- **FR-007**: The platform MUST support White-Label tenant configurations:
  - Custom domain CNAME mapping with automatic SSL certificate provisioning.
  - Custom logo, favicon, theme palette overrides, and custom email notification templates.
- **FR-008**: The platform MUST integrate with Stripe Billing for:
  - Tiered plan management (`Pro`, `Team`, `Enterprise Hedge Fund`).
  - Seat-based licensing for active team members.
  - Metered usage billing for LLM token consumption and external market data feeds.
- **FR-009**: The platform MUST generate comprehensive **Compliance Audit Logs** exportable in CSV and JSON formats, recording all trader actions, agent proposals, and executive approvals.

---

## 3. Non-Functional Requirements

- **NFR-001 (Tenant Data Isolation)**: Strict row-level security (RLS) and schema isolation preventing any cross-tenant data access under all circumstances.
- **NFR-002 (Enterprise API Throughput)**: Enterprise API endpoints MUST sustain 1,000 requests/sec per tenant with p95 latency < 20ms.
- **NFR-003 (Webhook Delivery SLA)**: Outbound event webhooks MUST be dispatched within 250ms of the triggering event.
- **NFR-004 (Audit Immutability)**: Compliance audit logs MUST be cryptographically hashed (SHA-256 chain) ensuring tamper-evidence for regulatory inspections.

---

## 4. User Stories

### US-001: Risk Officer Sets Organization-Wide Exposure Limits (Priority: P1)
- **Given** a Risk Officer at a prop trading firm,
- **When** they configure a desk-wide 4.0% daily maximum drawdown and a 5-lot ceiling on Junior Traders,
- **Then** the Pre-Trade Risk Gate automatically blocks any junior trader attempt exceeding 5 lots and locks the entire organization's automated strategies if desk losses hit 4.0%.

### US-002: White-Label Brokerage Deploys Branded AI Trading Portal (Priority: P1)
- **Given** a partner broker provisioning white-label Atlas AI Trading OS,
- **When** they configure their domain `trading.broker.com`, upload their brand assets, and map custom theme tokens,
- **Then** clients access the portal under the broker's identity with zero visible Atlas branding.

### US-003: Algorithmic Fund Ingests Real-Time Trade Webhooks (Priority: P2)
- **Given** a quantitative fund integrating Atlas signals into their risk database,
- **When** an AI agent executes a trade,
- **Then** the Enterprise Webhook service dispatches an HMAC-signed payload containing the trade details, entry prices, and agent debate transcript to the fund's internal endpoint within 150ms.

---

## 5. Enterprise Architecture

```text
+-------------------------------------------------------------------------+
|                        Enterprise Platform Layer                        |
|                                                                         |
|  +--------------------+                    +-------------------------+  |
|  | Tenant & Org Hub   |                    | Hierarchical Risk Engine|  |
|  | - Teams & Seats    |                    | - Org max drawdown      |  |
|  | - White-label specs|                    | - Dual-approval gates   |  |
|  +---------+----------+                    +------------+------------+  |
|            |                                            |               |
|            v                                            v               |
|  +------------------------------------------------------+------------+  |
|  |                     Enterprise Gateway & Auth                     |  |
|  |         (Row-Level Security -> API Keys -> Metering Engine)       |  |
|  +--------------------------------------+----------------------------+  |
|                                         |                               |
|        +--------------------------------+-----------------------+       |
|        |                                |                       |       |
|  +-----v--------------+      +----------v-----------+    +------v-----+ |
|  | Enterprise Webhooks|      | Stripe Billing Meter |    | Compliance | |
|  | - HMAC Delivery    |      | - Token & Seat usage |    | Audit Chain| |
|  +--------------------+      +----------------------+    +------------+ |
+-------------------------------------------------------------------------+
```

---

## 6. State Design

### 6.1 Organization & Team State Schema
```python
@dataclass(frozen=True)
class OrganizationState:
    org_id: str
    name: str
    plan_tier: str  # TEAM | INSTITUTIONAL | ENTERPRISE
    max_seats: int
    active_seats: int
    custom_domain: str | None
    white_label_config: dict[str, Any]
    risk_policy: dict[str, Any]
    is_active: bool
```

---

## 7. LangGraph Workflow Integration

In enterprise workspaces, LangGraph incorporates institutional dual-approval routing:

```text
[Junior Trader / Agent Formulates Proposal]
                     |
                     v
+------------------------------------+
| Check Trader Authorization Ceiling |
+--------------------+---------------+
                     |
         +-----------+-----------+
         |                       |
  (Exceeds Limit)         (Within Limit)
         |                       |
         v                       v
+--------------------------+  +--------------------+
| Senior Trader Approval   |  | Standard Human Gate|
| Interrupt Node           |  | Approval Node      |
+------------+-------------+  +--------------------+
             |
   (Senior Trader Signs)
             |
             v
+--------------------------+
| Dispatch to Venue        |
+--------------------------+
```

---

## 8. Tool Specifications

### 8.1 Provision Team Workspace Tool (`tool_enterprise_create_workspace`)
- **Description**: Creates a collaborative team workspace with shared risk limits.
- **Input Schema**:
  ```json
  {
    "type": "object",
    "required": ["org_id", "workspace_name", "max_capital_allocation"],
    "properties": {
      "org_id": { "type": "string" },
      "workspace_name": { "type": "string" },
      "max_capital_allocation": { "type": "string" }
    }
  }
  ```

---

## 9. API Specifications

### 9.1 Enterprise Endpoints
- **`GET /api/v1/enterprise/organizations/current`**: Returns current organization profile, teams, and active usage metrics.
- **`POST /api/v1/enterprise/members/invite`**: Invites new member with designated team and role.
- **`POST /api/v1/enterprise/webhooks`**: Registers external webhook subscription endpoint and generates signing secret.
- **`GET /api/v1/enterprise/audit-logs/export`**: Generates signed compliance export package (CSV/JSON).

---

## 10. Database Schema

### 10.1 Organizations Table (`enterprise_organizations`)
```sql
CREATE TABLE enterprise_organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(128) NOT NULL,
    slug VARCHAR(64) NOT NULL UNIQUE,
    plan_tier VARCHAR(32) NOT NULL DEFAULT 'TEAM',
    custom_domain VARCHAR(255),
    white_label_settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    stripe_customer_id VARCHAR(128),
    stripe_subscription_id VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_org_slug ON enterprise_organizations (slug);
```

### 10.2 Organization Memberships Table (`enterprise_memberships`)
```sql
CREATE TABLE enterprise_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES enterprise_organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'Trader',
    allocated_risk_pct NUMERIC(5, 2) NOT NULL DEFAULT 1.00,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_org_user UNIQUE (org_id, user_id)
);
```

---

## 11. Frontend Screens & Components

### 11.1 Enterprise Admin & Risk Control Console
- **Organization Hierarchy Tree**: Visual tree showing Teams, Portfolios, and assigned Traders with live PnL and risk utilization bars.
- **Desk Risk Policy Editor**: Centralized rule manager configuring daily loss limits, permitted venue adapters, and dual-approval thresholds.
- **Audit & Compliance Explorer**: Searchable log table with filters by actor, action type, and date, featuring a "Export Regulatory Report" button.

---

## 12. Security Requirements

- **SEC-001 (PostgreSQL Row-Level Security)**: All enterprise tables enforce PostgreSQL Row-Level Security (RLS) filtering data by `org_id` context variable.
- **SEC-002 (Signed Webhook Delivery)**: Every webhook dispatch includes `X-Atlas-Signature` header calculated using HMAC-SHA256 over timestamp + payload.
- **SEC-003 (Single Sign-On SAML 2.0 / Okta)**: Enterprise plans support enterprise SSO federation via Okta, Azure AD, and Google Workspace.

---

## 13. Testing Strategy

- **Multi-Tenant Leakage Test**: Concurrently execute cross-tenant queries to verify RLS policies unconditionally block unauthorized data access.
- **Dual-Approval Workflow Verification**: Verify an order exceeding tier limits cannot execute without senior approval token.
- **Stripe Webhook Conformance**: Test subscription upgrading, downgrading, and usage metering reconciliations.

---

## 14. Deployment Plan

- **Dedicated Enterprise Compute Pools**: Premium enterprise tenants routed to dedicated Kubernetes node pools to isolate resource consumption and guarantee compute availability.

---

## 15. Future Enhancements

- **SOCI-2 Type II Compliance Automation**: Built-in automated continuous evidence collection for institutional SOC 2 audits.
- **Multi-Party Computation (MPC) Key Management**: Institutional threshold signatures (TSS) for crypto custody and execution authorization.
