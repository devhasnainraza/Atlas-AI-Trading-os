# Data Model: Trading Integration (Venues, Market Data & Order Execution)

**Feature**: 02-trading-platform | **Date**: 2026-08-25 | **Plan**: [plan.md](./plan.md)

Conventions (Spec 00 standard): UUIDv7 `id` primary keys; `created_at` / `updated_at`
`timestamptz` on every table; snake_case names; enum-like columns CHECK-constrained; monetary and
quantity fields `NUMERIC` and handled as `Decimal` in code (floats banned in trading domain code);
all user-scoped tables carry `user_id` with an index. `environment` is
`live | demo | paper` and appears on every execution-bearing row so a record can never be
mistaken for a different environment.

## venue

Static catalog of supported venues (seeded, not user data).

| Field | Type | Rules |
|---|---|---|
| code | text | Unique, e.g. `mt5`, `oanda`, `binance`, `bybit`, `ibkr`, `paper` |
| display_name | text | Shown in UI |
| asset_classes | text[] | `forex｜crypto｜equity｜futures｜cfd` |
| capability_matrix | jsonb | Order types, TIF values, amend semantics, protective-level support, streaming support, supported environments — mirrors the adapter's declared matrix |
| capability_version | int | Bumped when the matrix changes; stored on connections for drift detection |
| rate_limit_model | jsonb | Declared limits (requests/window, weight model) used to configure buckets |
| supported_environments | text[] | Subset of `live｜demo｜paper` |
| status | text | `available｜beta｜disabled` — `disabled` blocks new connections, existing ones read-only |

## venue_connection

A user's authenticated link to one venue.

| Field | Type | Rules |
|---|---|---|
| user_id | uuid | FK user; index |
| venue_code | text | FK venue |
| label | text | User-chosen, unique per user |
| environment | text | `live｜demo｜paper`; immutable after creation |
| credential_id | uuid | Reference to Spec 01 vault credential; **no secret material stored here** |
| granted_capabilities | jsonb | Narrower of declared ∧ venue-verified permissions (FR-005) |
| capability_version | int | Snapshot at verification; mismatch triggers re-verification |
| health | text | `healthy｜degraded｜expired｜failed｜quarantined` |
| health_reason | text | Sanitized, user-readable; never venue raw payload |
| last_contact_at | timestamptz | Last successful venue interaction |
| last_verified_at | timestamptz | Last successful permission verification |
| routing_hold | boolean | True while an unresolved reconciliation discrepancy exists (FR-053) |
| disconnected_at | timestamptz | Set on disconnect; history retained |

## venue_account

An account exposed by a connection (a venue may expose several).

| Field | Type | Rules |
|---|---|---|
| connection_id | uuid | FK venue_connection; index |
| user_id | uuid | Denormalized for scoping |
| venue_account_id | text | The venue's own identifier (account number, sub-account) |
| currency | text | Account base currency (ISO-4217 or crypto symbol) |
| account_type | text | `spot｜margin｜futures｜cfd` |
| balance | numeric | Authoritative cash balance from venue |
| equity | numeric | Balance + unrealized PnL |
| free_margin | numeric | Margin available for new positions |
| used_margin | numeric | Margin held against open positions |
| leverage | numeric | Account leverage multiplier |
| last_synced_at | timestamptz | Last sync time |

## order_intent & order

- **order_intent**: intent_id (UUIDv7), user_id, connection_id, symbol, side, order_type, quantity, price, stop_loss, take_profit, verdict_hash, expires_at.
- **order**: order_id, intent_id UNIQUE, venue_order_id, status (`pending_risk｜submitting｜open｜filled｜partially_filled｜cancelled｜unresolved`), executed_quantity, average_fill_price.

## position

- **position**: position_id, account_id, venue_code, symbol, side (`LONG｜SHORT`), quantity (Decimal), entry_price (Decimal), current_price (Decimal), unrealized_pnl (Decimal), realized_pnl (Decimal), last_reconciled_at.

## risk_policy & risk_verdict

- **risk_policy**: user_id, max_position_size_usd, max_daily_loss_usd, max_leverage, allowed_symbols, is_active.
- **risk_verdict**: verdict_id, intent_id, allowed (boolean), violations (jsonb array), evaluated_at.
