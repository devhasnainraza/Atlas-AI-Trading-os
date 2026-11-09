# Data Model: Enterprise Features

**Feature**: 10-enterprise | **Date**: 2026-09-21 | **Plan**: [plan.md](./plan.md)

Conventions per Spec 00: UUIDv7 `id` primary keys, `created_at` / `updated_at` `timestamptz`, snake_case names, enums CHECK-constrained. High-precision numeric columns (`NUMERIC(28, 10)`) mapped strictly to Python `Decimal`. All tables enforce PostgreSQL Row-Level Security (RLS) filtering by `org_id`.

## enterprise_organizations

Top-level institutional customer entity representing a firm, fund, or trading desk.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| name | text | Organization legal name |
| slug | text | Unique alphanumeric identifier for vanity URLs |
| plan_tier | text | `TEAM | INSTITUTIONAL | ENTERPRISE` |
| custom_domain | text | White-label domain (e.g. `desk.hedgefund.com`) |
| white_label_settings| jsonb | Custom logo URL, favicon, brand palette overrides |
| stripe_customer_id| text | Stripe Billing customer reference |
| stripe_subscription_id| text | Active subscription reference |
| max_seats | int | Provisioned seat limit |
| created_at | timestamptz | Provisioning timestamp |
| updated_at | timestamptz | Modification timestamp |

## enterprise_teams

Sub-units within an organization managing specific strategies or trading books.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| org_id | uuid | FK enterprise_organizations; indexed, RLS boundary |
| name | text | Team name (e.g. `Crypto Momentum Desk`, `Macro FX Team`) |
| allocated_capital_usd| numeric(28, 10)| Total capital pooled for team use |
| risk_budget_pct | numeric(5, 2) | Maximum allowable daily loss for the team (e.g. 2.50%) |
| created_at | timestamptz | Creation timestamp |

## enterprise_memberships

User role assignments and operational boundaries within an organization and team.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| org_id | uuid | FK enterprise_organizations; indexed, RLS boundary |
| team_id | uuid | FK enterprise_teams; optional |
| user_id | uuid | FK user; unique per organization |
| role | text | `Org_Owner | Risk_Officer | Portfolio_Manager | Senior_Trader | Junior_Trader | Auditor` |
| max_lot_size | numeric(12, 4) | Maximum position size permitted without escalation |
| max_risk_per_trade_pct| numeric(5, 2)| Individual risk cap (default 0.50% for Junior) |
| requires_dual_approval| boolean | If true, orders above threshold require Senior sign-off |
| created_at | timestamptz | Membership assignment timestamp |

## enterprise_risk_policies

Top-down institutional risk governance rules enforced across all organizational activity.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| org_id | uuid | FK enterprise_organizations; unique, RLS boundary |
| max_org_daily_drawdown_pct| numeric(5, 2)| Desk-wide kill switch threshold (e.g. 4.00%) |
| max_portfolio_leverage| numeric(6, 2) | Hard institutional leverage cap (e.g. 5.00x) |
| allowed_venues | text[] | Whitelisted venue adapters (e.g. `['binance', 'ibkr']`) |
| dual_approval_threshold_usd| numeric(28, 10)| Order notional value requiring dual signatures |
| emergency_halt_active| boolean | Desk-wide panic stop state |
| updated_at | timestamptz | Timestamp of last policy adjustment |

## enterprise_webhooks

External developer webhook subscriptions for real-time algorithmic event delivery.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| org_id | uuid | FK enterprise_organizations; indexed, RLS boundary |
| target_url | text | HTTPS endpoint for payload delivery |
| secret_hash | text | SHA-256 hash of the HMAC signing secret |
| subscribed_events | text[] | Events: `['trade.executed', 'risk.limit_breached', 'mandate.halted']` |
| is_active | boolean | Delivery toggle |
| failure_count | int | Consecutive failed delivery count |
| created_at | timestamptz | Registration timestamp |

## enterprise_compliance_audit_logs

Cryptographically chained, tamper-evident audit ledger for institutional compliance and regulatory scrutiny.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| org_id | uuid | FK enterprise_organizations; indexed, RLS boundary |
| actor_user_id | uuid | User executing or approving the action |
| event_type | text | e.g. `ORDER_DISPATCH`, `RISK_POLICY_UPDATE`, `DUAL_APPROVAL_SIGN` |
| payload | jsonb | Complete structured snapshot of event parameters |
| previous_hash | text | SHA-256 hash of immediately preceding audit record |
| record_hash | text | SHA-256(previous_hash + id + event_type + payload + timestamp) |
| recorded_at | timestamptz | Immutable record timestamp; indexed |
