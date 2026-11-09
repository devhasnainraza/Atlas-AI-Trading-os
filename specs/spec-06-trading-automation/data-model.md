# Data Model: Trading Automation

**Feature**: 06-trading-automation | **Date**: 2026-09-21 | **Plan**: [plan.md](./plan.md)

Conventions per Spec 00: UUIDv7 `id` primary keys, `created_at` / `updated_at` `timestamptz`, snake_case names, enums CHECK-constrained. High-precision numeric fields (`NUMERIC(28, 10)`) mapped strictly to Python `Decimal`. Tables carry indexed `user_id` and `account_id` for multi-tenant isolation.

## automation_mandates

User-delegated policies authorizing bounded autonomous trading execution.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| user_id | uuid | FK user; indexed |
| account_id | uuid | FK venue_account; indexed |
| mode | text | `MANUAL | SEMI_AUTOMATIC | FULLY_AUTOMATIC` |
| allowed_symbols | text[] | Whitelisted symbols for execution |
| max_capital_risk_pct| numeric(5, 2) | Maximum risk per individual trade (default 1.00%) |
| daily_loss_limit_usd| numeric(28, 10) | Hard cumulative loss threshold triggering circuit breaker |
| max_open_positions | int | Maximum concurrent positions permitted |
| news_protection | boolean | If true, locks entries around high-impact macro releases |
| session_restrictions| text[] | Allowed sessions (e.g. `['LONDON', 'NEW_YORK']`) |
| mandate_signature | text | Cryptographic signature verifying human authorization |
| is_active | boolean | Toggles mandate execution |
| expires_at | timestamptz | Expiration timestamp; requires renewal |
| created_at | timestamptz | Creation timestamp |
| updated_at | timestamptz | Last configuration modification |

**Transitions**: `active -> suspended` (circuit breaker tripped or worker disconnect); `suspended -> active` (daily reset or manual clearance); `active -> expired` (TTL passed); `active -> revoked` (user terminated mandate).

## automation_circuit_breaker_events

Immutable audit ledger capturing all automated protective circuit breaker trips and trading halts.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| user_id | uuid | FK user; indexed |
| account_id | uuid | FK venue_account; indexed |
| breaker_type | text | `DAILY_DRAWDOWN | CONSECUTIVE_LOSS | NEWS_LOCKOUT | VENUE_LATENCY | EMERGENCY_PANIC` |
| threshold_value | numeric(28, 10) | Configured limit (e.g. `$300.00` daily loss) |
| observed_value | numeric(28, 10) | Breach observation (e.g. `$312.50` actual loss) |
| actions_taken | text[] | Array of actions taken (e.g. `['HALT_MANDATES', 'CANCEL_PENDING_ORDERS']`) |
| triggered_at | timestamptz | Timestamp of trip; indexed |
| reset_at | timestamptz | Timestamp of manual or scheduled daily reset |

## automation_position_guards

Tracking state for active position exit management (dynamic SL/TP, breakeven, and trailing stops).

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| position_id | text | Venue or local position identifier; indexed |
| account_id | uuid | FK venue_account; indexed |
| user_id | uuid | FK user; indexed |
| symbol | text | Asset symbol |
| side | text | `LONG | SHORT` |
| entry_price | numeric(28, 10) | Average entry fill price |
| current_stop_loss | numeric(28, 10) | Current effective stop loss price |
| initial_stop_loss | numeric(28, 10) | Invalidation stop at entry |
| tp1_price | numeric(28, 10) | First take-profit target |
| tp2_price | numeric(28, 10) | Second take-profit target |
| tp3_price | numeric(28, 10) | Final target / runner baseline |
| breakeven_offset | numeric(28, 10) | Buffer added to entry (spread + fee cushion) |
| breakeven_reached | boolean | True once stop moved to breakeven |
| tp1_filled | boolean | True once TP1 executed |
| tp2_filled | boolean | True once TP2 executed |
| trailing_active | boolean | True once trailing stop activated |
| trailing_step_type | text | `ATR | CHANDELIER | FIXED_PIPS` |
| trailing_distance | numeric(28, 10) | Trailing gap distance |
| highest_price_seen | numeric(28, 10) | Peak price recorded since entry |
| lowest_price_seen | numeric(28, 10) | Trough price recorded since entry |
| status | text | `active | closed | cancelled` |
| updated_at | timestamptz | Last tick evaluation timestamp |

## automation_execution_logs

Granular event trail of automated execution interventions.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| mandate_id | uuid | Reference to automation mandate |
| position_id | text | Affected position |
| action_type | text | `ENTRY_DISPATCH | TP_PARTIAL_CLOSE | BREAKEVEN_RATCHET | TRAIL_UPDATE | EMERGENCY_FLATTEN` |
| previous_state | jsonb | State snapshot prior to action |
| new_state | jsonb | State snapshot post action |
| latency_ms | int | Execution processing time in milliseconds |
| executed_at | timestamptz | Execution timestamp; indexed |
