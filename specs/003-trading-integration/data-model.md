# Data Model: Trading Integration (Venues, Market Data & Order Execution)

**Feature**: 003-trading-integration | **Date**: 2026-08-25 | **Plan**: [plan.md](./plan.md)

Conventions (Spec 00 standard): UUIDv7 `id` primary keys; `created_at` / `updated_at`
`timestamptz` on every table; snake_case names; enum-like columns CHECK-constrained; monetary and
quantity fields `NUMERIC` and handled as `Decimal` in code (floats banned in trading domain code);
all user-scoped tables carry `user_id` with an index; no SQL in this document. `environment` is
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

**Transitions**: `healthy → degraded` on probe/stream failure or sustained rate limiting;
`→ expired` on credential expiry; `→ quarantined` on credential revocation (Spec 01 event) —
quarantine stops order routing and triggers reconciliation; `→ failed` on repeated verification
failure. Creating or promoting a `live` connection requires step-up MFA. Unique
(user_id, venue_code, label) where `disconnected_at is null`.

## venue_account

An account exposed by a connection (a venue may expose several).

| Field | Type | Rules |
|---|---|---|
| connection_id | uuid | FK venue_connection; index |
| user_id | uuid | Denormalized for scoping |
| venue_account_ref | text | Venue's account identifier (not secret) |
| environment | text | Copied from connection |
| base_currency | text | ISO code |
| balance | numeric | Venue-reported |
| equity | numeric | Venue-reported |
| margin_used | numeric | Nullable where venue does not report |
| margin_available | numeric | Nullable |
| unrealized_pnl | numeric | Venue-reported where available |
| leverage | numeric | Nullable |
| view_state | text | `live｜stale｜unknown` — derived from `synced_at` vs freshness target (FR-019) |
| synced_at | timestamptz | Last successful snapshot; null ⇒ `unknown` |

Unique (connection_id, venue_account_ref).

## instrument

Canonical instrument plus per-venue specification.

| Field | Type | Rules |
|---|---|---|
| venue_code | text | FK venue |
| canonical_symbol | text | Atlas symbol, e.g. `EURUSD`, `BTCUSDT` |
| venue_symbol | text | Native symbol at that venue |
| asset_class | text | `forex｜crypto｜equity｜futures｜cfd` |
| base_currency / quote_currency | text | Nullable for non-pair instruments |
| settlement_currency | text | Nullable |
| price_precision | int | Decimal places |
| tick_size | numeric | Minimum price increment |
| quantity_min / quantity_max / quantity_step | numeric | Validated before transmission (FR-033) |
| contract_size | numeric | Nullable |
| margin_rate | numeric | Nullable; venue-declared |
| max_leverage | numeric | Nullable |
| session_schedule | jsonb | Venue-local windows + holidays; resolved to UTC at read |
| session_state | text | `open｜closed｜pre｜halted｜suspended` (materialized, refreshed) |
| tradable | boolean | False ⇒ compose-time rejection |
| spec_version | int | Incremented on change; working orders re-validated on bump |
| refreshed_at | timestamptz | Staleness of the spec itself |

Unique (venue_code, venue_symbol) and (venue_code, canonical_symbol).

## market_data_subscription

| Field | Type | Rules |
|---|---|---|
| user_id | uuid | Index |
| connection_id | uuid | Source connection |
| instrument_id | uuid | FK instrument |
| timeframes | text[] | Bar timeframes requested |
| active | boolean | Soft-off without losing configuration |
| lease_owner | text | Worker holding the stream lease (nullable) |
| lease_expires_at | timestamptz | Lease-based sharding (plan §4) |

Unique (user_id, connection_id, instrument_id). Per-user subscription cap enforced in service.

## quote (Redis, not a table)

Key `md:quote:{venue_code}:{venue_symbol}` → `{bid, ask, last, bid_size, ask_size, observed_at,
venue_code, environment}` with **TTL = asset-class freshness limit** — key absence *is* staleness
(FR-011/012). Never treated as durable; never blended across venues (FR-015).

## candle

Aggregated bars, monthly partitioned.

| Field | Type | Rules |
|---|---|---|
| instrument_id | uuid | FK instrument |
| timeframe | text | `1m｜5m｜15m｜1h｜4h｜1d` |
| open_time | timestamptz | Partition key (monthly); UTC |
| open / high / low / close | numeric | Decimal |
| volume | numeric | Nullable where venue does not report |
| is_gap | boolean | True for known-missing intervals (FR-014) — gaps are marked, never interpolated |
| source | text | `venue_stream｜venue_backfill｜aggregated` |

Unique (instrument_id, timeframe, open_time).

## order_intent

The reviewable artifact created before any transmission (FR-023).

| Field | Type | Rules |
|---|---|---|
| user_id | uuid | Index |
| connection_id / venue_account_id | uuid | Destination |
| instrument_id | uuid | FK instrument |
| environment | text | Stamped |
| side | text | `buy｜sell` |
| order_type | text | `market｜limit｜stop｜stop_limit` |
| quantity | numeric | Validated against instrument step/min/max |
| limit_price / stop_price | numeric | Required per type; precision-validated |
| time_in_force | text | `GTC｜IOC｜FOK｜DAY｜GTD` |
| good_till_date | timestamptz | Required iff `GTD` |
| stop_loss / take_profit | numeric | Optional protective levels (FR-023) |
| reduce_only | boolean | Marks a risk-reducing intent (plan §7) |
| origin | text | `manual｜agent｜strategy｜mandate` (FR-034) |
| origin_ref | text | Agent/strategy/mandate identifier when not manual |
| quote_snapshot | jsonb | Bid/ask/last + `observed_at` used for pricing |
| estimated_cost / estimated_fees / margin_impact | numeric | Shown at review (FR-023) |
| risk_verdict_id | uuid | FK risk_verdict |
| verdict_hash | text | Client must echo at confirm; mismatch ⇒ invalidated (FR-025) |
| state | text | `pending_confirmation｜confirmed｜expired｜invalidated｜rejected_by_risk` |
| expires_at | timestamptz | Default now + 30 s |
| confirmed_at | timestamptz | Null until confirmed |
| confirmed_by_user_id | uuid | Accountable human (FR-034) |

**Transitions**: `pending_confirmation → confirmed` (hash match + freshness + gate re-check pass)
| `→ expired` (clock) | `→ invalidated` (price/account/spec/kill-switch drift) |
`→ rejected_by_risk` (verdict `blocked`). Only a `confirmed` intent may produce an order, and at
most one (see `order_submission`).

## order

| Field | Type | Rules |
|---|---|---|
| user_id / connection_id / venue_account_id / instrument_id | uuid | Scoping + destination |
| intent_id | uuid | Unique — one order per intent |
| environment | text | Stamped |
| client_order_id | text | Atlas-generated, deterministic per intent; unique per connection |
| venue_order_id | text | Nullable until acked; may arrive via reconciliation |
| side / order_type / quantity / limit_price / stop_price / time_in_force | — | Copied from intent (immutable record of what was sent) |
| filled_quantity | numeric | Sum of fills |
| average_fill_price | numeric | Nullable until first fill |
| remaining_quantity | numeric | Derived, stored for query efficiency |
| state | text | `submitting｜working｜partially_filled｜filled｜canceled｜rejected｜expired｜unresolved｜amending｜canceling` |
| state_reason | text | Sanitized venue reason where applicable (FR-032) |
| origin / origin_ref | text | Carried from intent |
| submitted_at / acked_at / closed_at | timestamptz | Latency measurement points (SC-004) |
| unresolved_since | timestamptz | Set when state becomes `unresolved`; drives alerting |
| resolved_by_run_id | uuid | Reconciliation run that resolved it |
| correlation_id | text | Joins the whole chain (FR-055) |

**Transitions**: `submitting → working｜rejected｜unresolved`; `working → partially_filled →
filled`; `working｜partially_filled → canceling → canceled` (venue-confirmed only);
`working → amending → working` (amend accepted) or back with `state_reason` (amend refused —
FR-028); any → `expired` on venue expiry; `unresolved → <venue truth>` only via reconciliation,
**never auto-resubmitted** (FR-030). Terminal states are immutable except by reconciliation
correction, which is recorded as its own event.

## order_submission

Pre-call ledger enforcing at-most-once transmission (FR-026, SC-005).

| Field | Type | Rules |
|---|---|---|
| intent_id | uuid | **Unique** — the constraint that makes duplicates impossible |
| order_id | uuid | FK order |
| client_order_id | text | Mirrors order |
| attempted_at | timestamptz | Written **before** the adapter call, same transaction as the order row |
| outcome | text | `acked｜rejected｜timeout｜ambiguous｜pending` |
| venue_response_ref | uuid | FK venue_message (redacted payload), nullable |

Written first, updated after. A second confirm for the same intent hits the unique constraint and
returns the existing order — it never reaches the adapter.

## order_event

Append-only transition log (source of the order chain).

| Field | Type | Rules |
|---|---|---|
| order_id | uuid | Index |
| sequence | int | Monotonic per order |
| event_type | text | `created｜submitted｜acked｜partial_fill｜fill｜amend_requested｜amend_accepted｜amend_refused｜cancel_requested｜canceled｜cancel_refused｜rejected｜expired｜unresolved｜resolved｜corrected` |
| from_state / to_state | text | Nullable for informational events |
| actor | text | `user｜system｜venue｜reconciliation` |
| detail | jsonb | Sanitized; never credentials or raw venue auth payloads |
| occurred_at | timestamptz | Venue timestamp where known, else platform clock |

Immutable, no deletes (append-only, Spec 00 audit standard).

## fill

| Field | Type | Rules |
|---|---|---|
| order_id | uuid | Index |
| venue_fill_ref | text | Unique per order — dedupes repeated stream deliveries |
| quantity / price | numeric | Decimal |
| fee_amount / fee_currency | numeric / text | Nullable |
| liquidity | text | `maker｜taker｜unknown` |
| is_simulated | boolean | True for paper |
| fill_model_version | text | Paper only — which model produced it (FR-047) |
| filled_at | timestamptz | Venue timestamp |

Each fill stored individually (FR-027); average price is derived, never overwritten.

## position

Venue-authoritative projection (FR-020).

| Field | Type | Rules |
|---|---|---|
| user_id / connection_id / venue_account_id / instrument_id | uuid | Scoping |
| environment | text | Stamped |
| side | text | `long｜short` |
| quantity | numeric | Venue-reported |
| average_entry_price | numeric | Venue-reported |
| unrealized_pnl / realized_pnl | numeric | Venue-reported where available |
| stop_loss / take_profit | numeric | Nullable protective levels |
| venue_position_ref | text | Where the venue exposes one |
| opened_externally | boolean | True when discovered, not created by Atlas (FR-017) |
| state | text | `open｜closing｜closed` |
| synced_at | timestamptz | Freshness of the projection |
| closed_at | timestamptz | Nullable |

Unique (venue_account_id, instrument_id, side) for open positions in netting mode; hedging venues
additionally key on `venue_position_ref`.

## risk_policy

| Field | Type | Rules |
|---|---|---|
| user_id | uuid | Unique per (user, scope) |
| scope | text | `global｜connection` (+ `connection_id` when scoped) |
| max_order_quantity / max_order_notional | numeric | Nullable = unlimited only if explicitly set so |
| max_position_notional_per_instrument | numeric | — |
| max_total_exposure_notional | numeric | Per venue and aggregate variants |
| max_daily_loss | numeric | With `daily_window_reset_time` + timezone (FR-036) |
| max_open_positions | int | — |
| max_leverage | numeric | — |
| instrument_allowlist | text[] | Empty ⇒ all tradable instruments |
| session_guard | boolean | Block orders when session closed/halted |
| duplicate_window_seconds | int | Duplicate-order heuristic window |
| version | int | Incremented on change; changes apply only to future orders (FR-044) |
| effective_from | timestamptz | Audit of when the policy took effect |

## risk_verdict

Immutable evaluation record (FR-040).

| Field | Type | Rules |
|---|---|---|
| user_id | uuid | Index |
| intent_id | uuid | Nullable for `POST /risk/preview` |
| policy_version | int | Policy applied |
| decision | text | `allowed｜allowed_with_warnings｜blocked` |
| rules_evaluated | jsonb | Array of `{rule, limit_value, actual_value, passed}` — all rules, not just failures |
| breached_rules | text[] | Empty when allowed |
| inputs_state | jsonb | Quote freshness, account view state, reconciliation state — proves fail-closed behavior (FR-039) |
| verdict_hash | text | Hash of decision + terms; echoed at confirm |
| correlation_id | text | Chain join |
| evaluated_at | timestamptz | Injected clock |

No updates, no deletes; retained for the life of the order record.

## automation_mandate

| Field | Type | Rules |
|---|---|---|
| user_id | uuid | Index |
| label | text | User-chosen |
| scope_instruments | text[] | Required, non-empty (FR-041) |
| connection_ids | uuid[] | Required, non-empty |
| max_order_notional | numeric | Required |
| max_total_commitment_notional | numeric | Required; metered |
| committed_notional | numeric | Running consumption |
| max_orders_per_period / period_seconds | int | Optional |
| orders_used | int | Running count |
| expires_at | timestamptz | Required; ≤ 30 days from grant |
| state | text | `active｜exhausted｜expired｜revoked` |
| granted_at / revoked_at | timestamptz | Grant requires step-up MFA |
| revoked_by_user_id | uuid | Nullable |

**Transitions**: `active → exhausted` (commitment or order count reached) | `→ expired` (clock) |
`→ revoked` (single user action, immediate, FR-042). Mandates skip per-order confirmation only;
the risk gate always runs (FR-041).

## kill_switch

| Field | Type | Rules |
|---|---|---|
| scope | text | `user｜venue｜global` |
| user_id | uuid | Required iff scope `user` |
| venue_code | text | Required iff scope `venue` |
| engaged | boolean | Mirrored to a Redis flag for < 1 s effect (SC-008) |
| reason | text | Required on engage |
| actor_type | text | `user｜operator` |
| actor_id | uuid | Accountable identity |
| engaged_at / released_at | timestamptz | Full history retained (append a new row per change) |

While engaged: no new orders or position-increasing actions; cancels and position closes remain
permitted (FR-043).

## paper_account

| Field | Type | Rules |
|---|---|---|
| connection_id | uuid | Paper connection |
| user_id | uuid | Index |
| starting_balance / balance / equity | numeric | Decimal |
| currency | text | ISO |
| leverage_profile | text | Which venue's margin profile is mirrored (FR-046) |
| fill_model | jsonb | Spread widening, slippage, latency parameters (disclosed) |
| fill_model_version | text | Stamped onto simulated fills |
| reset_count | int | Incremented per reset |
| last_reset_at | timestamptz | Reset recorded (FR-049) |

## reconciliation_run

| Field | Type | Rules |
|---|---|---|
| connection_id | uuid | Index |
| user_id | uuid | Scoping |
| trigger | text | `scheduled｜unresolved_order｜stream_gap｜credential_revoked｜manual` |
| started_at / completed_at | timestamptz | Duration is a metric |
| orders_compared / positions_compared | int | Coverage |
| discrepancies_found / discrepancies_resolved | int | Drift metric inputs (SC-003) |
| outcome | text | `clean｜corrected｜unresolved｜failed` |
| report_ref | text | S3 key for the full report (1-year retention) |

## reconciliation_discrepancy

| Field | Type | Rules |
|---|---|---|
| run_id | uuid | FK reconciliation_run |
| entity_type | text | `order｜position｜balance` |
| entity_ref | text | Local id and/or venue ref |
| discrepancy_class | text | `missing_locally｜missing_at_venue｜quantity_mismatch｜price_mismatch｜state_mismatch｜unknown_order` |
| local_value / venue_value | jsonb | Both sides recorded (FR-052) |
| resolution | text | `applied_venue_state｜imported｜closed_locally｜escalated` |
| resolved_at | timestamptz | Null while escalated — holds routing (FR-053) |

## venue_message

Redacted record of venue interactions kept for the reconciliation window.

| Field | Type | Rules |
|---|---|---|
| connection_id | uuid | Index |
| direction | text | `outbound｜inbound` |
| operation | text | e.g. `submit_order`, `cancel_order`, `account_snapshot` |
| status_code | int | Nullable for stream messages |
| payload_redacted | jsonb | Secrets, headers, and auth material stripped before write (SC-011) |
| error_class | text | `retryable_transient｜rate_limited｜terminal_rejection｜permission_denied｜ambiguous` |
| correlation_id | text | Chain join |
| occurred_at | timestamptz | — |

Retention 30 days, then purge.

## Cross-cutting rules

- **Erasure**: the trading module registers a handler for
  `atlas.privacy.user_erasure.requested` and emits its ack. Deleted:
  `market_data_subscription`, `order_intent`, `paper_account`, `automation_mandate`, Redis quote
  keys, `venue_message`. **Pseudonymized, not deleted**: `order`, `order_event`, `fill`,
  `position`, `risk_verdict`, `reconciliation_*` — execution records under the 7-year retention
  assumption, with the carve-out documented in the export bundle (plan §14).
  `venue_connection` is deleted after credential references are severed.
- **Retention**: bars and instrument specs non-personal and retained independently;
  reconciliation reports 1 year; `venue_message` 30 days; audit entries ≥ 1 year (Spec 01).
- **Immutability**: `order_event`, `fill`, `risk_verdict`, and `order_submission.attempted_at`
  are append-only/write-once; corrections are new rows, never edits.
- **Environment safety**: every execution-bearing table carries `environment`; queries that mix
  environments in an aggregate are rejected at the repository layer (FR-050).
- **Decimal**: all `numeric` columns map to `Decimal`; a lint rule bans `float` in
  `trading`/`marketdata` domain code.

## Relationships

```text
venue ──< venue_connection ──< venue_account ──< position
                │                    │
                │                    └──< order ──< fill
                │                            │
                ├──< market_data_subscription├──< order_event
                ├──< reconciliation_run ──< reconciliation_discrepancy
                ├──< venue_message          │
                └──< paper_account          │
                                            │
order_intent ──1:1── order_submission ──1:1─┘
     │
     └──1:1── risk_verdict ──> risk_policy (version)

instrument ──< candle          automation_mandate ──> order (origin=mandate)
instrument ──< order_intent    kill_switch ──> (gate + confirm checks)
Redis: md:quote:{venue}:{symbol}  ·  rate buckets  ·  submit locks  ·  killswitch flag
Spec 01: credential (referenced by id only) · audit_log_entry · user
```
