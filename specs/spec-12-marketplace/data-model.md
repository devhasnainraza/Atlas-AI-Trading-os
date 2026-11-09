# Data Model: AI Marketplace

**Feature**: 12-marketplace | **Date**: 2026-09-21 | **Plan**: [plan.md](./plan.md)

Conventions per Spec 00: UUIDv7 `id` primary keys, `created_at` / `updated_at` `timestamptz`, snake_case names, enums CHECK-constrained. High-precision numeric columns (`NUMERIC(12, 2)` and `NUMERIC(5, 2)`) mapped strictly to Python `Decimal`. Tables carry indexed `creator_id` and `user_id` for multi-tenant isolation.

## marketplace_plugins

Catalog of public and review-pending marketplace extensions, strategies, agents, and indicators.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| creator_id | uuid | FK user; creator reference, indexed |
| slug | text | Unique alphanumeric identifier for store URL |
| name | text | Display name of the plugin |
| plugin_type | text | `AGENT | STRATEGY | INDICATOR | PROMPT | WORKFLOW | DASHBOARD` |
| current_version | text | Semantic version string (e.g. `1.2.0`) |
| pricing_model | text | `FREE | ONE_TIME | SUBSCRIPTION` |
| price_usd | numeric(10, 2) | Price in USD (0.00 for free plugins) |
| status | text | `IN_REVIEW | APPROVED | REJECTED | SUSPENDED` |
| rating_avg | numeric(3, 2) | Rolling average star rating (1.00 to 5.00) |
| rating_count | int | Total number of published reviews |
| install_count | int | Active install counter |
| manifest | jsonb | Complete `AtlasPluginManifest` metadata |
| backtest_metrics | jsonb | Verified historical performance stats (Sharpe, Max DD, Win %) |
| created_at | timestamptz | Submission timestamp |
| updated_at | timestamptz | Last catalog update |

## marketplace_plugin_versions

Immutable historical release bundles and automated audit verification logs for each version.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| plugin_id | uuid | FK marketplace_plugins; indexed |
| version | text | Semantic version string |
| changelog | text | Markdown release notes |
| bundle_storage_url | text | Encrypted code package location in MinIO/S3 |
| verification_status| text | `PENDING | PASSED | FAILED` |
| verification_report| jsonb | AST scan, sandbox memory logs, backtest match details |
| package_signature | text | Creator cryptographic ECDSA signature |
| created_at | timestamptz | Version release timestamp |

## marketplace_installations

Active user subscriptions, installations, and sandbox execution configurations.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| user_id | uuid | FK user; indexed |
| plugin_id | uuid | FK marketplace_plugins; indexed |
| target_account_id | uuid | FK venue_account; account bound to this plugin |
| installed_version | text | Currently running plugin version |
| is_active | boolean | Toggles runtime execution |
| config | jsonb | User-configured runtime parameters and risk allocations |
| installed_at | timestamptz | Installation timestamp |
| updated_at | timestamptz | Last configuration change |

## marketplace_reviews

Verified user ratings and qualitative feedback on marketplace plugins.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| plugin_id | uuid | FK marketplace_plugins; indexed |
| user_id | uuid | FK user; indexed |
| rating | int | 1 to 5 stars |
| review_title | text | Brief headline |
| review_body | text | Detailed user review text |
| is_verified_purchaser| boolean | Confirms user holds active license or installation |
| created_at | timestamptz | Review timestamp; indexed |

## marketplace_creator_accounts

Stripe Connect creator account references and revenue accumulation ledgers.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| user_id | uuid | FK user; unique |
| stripe_connect_id | text | Stripe Connect custom account ID |
| payout_status | text | `ACTIVE | PENDING_KYC | RESTRICTED` |
| total_revenue_usd | numeric(12, 2) | Gross lifetime revenue generated |
| creator_earnings_usd| numeric(12, 2) | Net 70% share earned by creator |
| platform_fees_usd | numeric(12, 2) | Net 30% platform commission retained |
| created_at | timestamptz | Creator onboarding timestamp |
