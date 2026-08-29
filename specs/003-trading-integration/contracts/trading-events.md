# Event Contracts: Trading & Market Data

**Feature**: 003-trading-integration | Registered in `shared/atlas_events/catalog.py`
Envelope, versioning, and idempotency rules per Spec 00 (`atlas_events`); every event carries
`event_id`, `event_type`, `occurred_at`, `correlation_id`, `user_id` (where user-scoped), and
`environment` (`live｜demo｜paper`). **No event payload may contain credential material, raw venue
auth payloads, or venue API keys** — asserted by the same contract test as the API surface.

## Catalog — `atlas.trading.*`

| event_type | Producer | Payload (summary) | Primary consumers |
|---|---|---|---|
| `atlas.trading.venue.connected` | trading | connection_id, venue_code, environment, granted_capabilities | worker (initial sync), notifications (future), audit |
| `atlas.trading.venue.verified` | trading | connection_id, capability_version, verified_at | analytics, audit |
| `atlas.trading.venue.degraded` | trading | connection_id, venue_code, previous_health, health, reason_code | notifications (future), observability, audit |
| `atlas.trading.venue.quarantined` | trading | connection_id, cause (`credential_revoked｜verification_failed`) | worker (reconcile), notifications, audit |
| `atlas.trading.venue.disconnected` | trading | connection_id, actor_type | worker (stop streams), audit |
| `atlas.trading.account.synced` | trading | venue_account_id, balance, equity, margin_used, view_state, synced_at | risk cache, analytics (future), web realtime |
| `atlas.trading.order.intent_created` | trading | intent_id, instrument, side, order_type, quantity, prices, origin, verdict decision, expires_at | audit, analytics |
| `atlas.trading.order.intent_invalidated` | trading | intent_id, reason (`expired｜price_drift｜account_changed｜spec_changed｜kill_switch`) | web realtime, audit |
| `atlas.trading.order.rejected_by_risk` | trading | intent_id, breached_rules, decision, inputs_state | notifications, analytics, audit |
| `atlas.trading.order.confirmed` | trading | intent_id, order_id, client_order_id, confirmed_by_user_id | audit, analytics |
| `atlas.trading.order.submitted` | trading | order_id, client_order_id, connection_id, submitted_at | observability (latency), audit |
| `atlas.trading.order.accepted` | trading | order_id, venue_order_id, acked_at | web realtime, audit |
| `atlas.trading.order.partially_filled` | trading | order_id, fill (qty, price, fee), filled_quantity, remaining_quantity | positions projection, web realtime, analytics |
| `atlas.trading.order.filled` | trading | order_id, filled_quantity, average_fill_price, closed_at | positions projection, journal (future), analytics |
| `atlas.trading.order.amended` | trading | order_id, changes, accepted (bool), venue_reason | web realtime, audit |
| `atlas.trading.order.canceled` | trading | order_id, canceled_quantity, actor | web realtime, audit |
| `atlas.trading.order.rejected` | trading | order_id, sanitized venue reason, error_class | notifications, analytics, audit |
| `atlas.trading.order.expired` | trading | order_id, time_in_force | web realtime, audit |
| `atlas.trading.order.unresolved` | trading | order_id, client_order_id, unresolved_since, last_known_state | **worker (immediate targeted reconciliation)**, observability (page-worthy), notifications |
| `atlas.trading.order.resolved` | trading | order_id, resolved_state, reconciliation_run_id | web realtime, audit |
| `atlas.trading.position.opened` | trading | position_id, instrument, side, quantity, average_entry_price, opened_externally | analytics, journal (future), web realtime |
| `atlas.trading.position.updated` | trading | position_id, quantity, average_entry_price, unrealized_pnl, protective levels | risk cache, web realtime |
| `atlas.trading.position.closed` | trading | position_id, realized_pnl, closed_at | analytics, journal (future) |
| `atlas.trading.risk.limit_breached` | trading | user_id, rule, limit_value, actual_value, intent_id | notifications, observability, audit |
| `atlas.trading.risk.policy_changed` | trading | user_id, scope, version, effective_from | audit, analytics |
| `atlas.trading.risk.kill_switch_engaged` | trading | scope, user_id/venue_code, reason, actor_type, actor_id | **all order paths (cache invalidate)**, notifications, observability |
| `atlas.trading.risk.kill_switch_released` | trading | scope, target, actor_type, actor_id | same as above |
| `atlas.trading.mandate.granted` | trading | mandate_id, scope_instruments, caps, expires_at | audit, observability |
| `atlas.trading.mandate.consumed` | trading | mandate_id, committed_notional, orders_used | web realtime, observability |
| `atlas.trading.mandate.revoked` | trading | mandate_id, actor, reason (`user｜exhausted｜expired`) | agents (future — must stop), audit |
| `atlas.trading.reconciliation.completed` | trading | run_id, connection_id, trigger, counts, outcome | observability (drift metric), audit |
| `atlas.trading.reconciliation.discrepancy_found` | trading | run_id, entity_type, discrepancy_class, local_value, venue_value | notifications, observability, audit |
| `atlas.trading.reconciliation.escalated` | trading | run_id, discrepancy_id, routing_hold=true | **notifications (user + support)**, observability (page-worthy) |
| `atlas.trading.paper.reset` | trading | connection_id, starting_balance, reset_count | analytics (exclude prior data), audit |

## Catalog — `atlas.marketdata.*`

| event_type | Producer | Payload (summary) | Primary consumers |
|---|---|---|---|
| `atlas.marketdata.subscription.created` | marketdata | subscription_id, instrument, timeframes | worker (stream lease assignment) |
| `atlas.marketdata.subscription.removed` | marketdata | subscription_id | worker (release lease) |
| `atlas.marketdata.quote.stale` | marketdata | venue_code, instrument, last_observed_at, age_seconds | **risk gate (fail closed)**, web realtime, observability |
| `atlas.marketdata.feed.degraded` | marketdata | connection_id, venue_code, reason_code, since | web realtime, observability |
| `atlas.marketdata.feed.recovered` | marketdata | connection_id, gap_seconds, backfill_required | worker (snapshot reconcile + backfill) |
| `atlas.marketdata.candle.closed` | marketdata | instrument, timeframe, open_time, ohlcv, is_gap | analytics, strategy engine (future) |
| `atlas.marketdata.instrument.spec_changed` | marketdata | instrument_id, spec_version, changed_fields | **trading (re-validate working orders)**, web realtime |

## Consumed events (from other modules)

| event_type | Producer | Trading/marketdata obligation |
|---|---|---|
| `atlas.credentials.credential.revoked` | credentials (Spec 01) | Quarantine every connection using that credential, stop routing, trigger reconciliation of in-flight orders |
| `atlas.credentials.credential.rotated` | credentials (Spec 01) | Re-verify permissions; tear down and re-establish venue sessions (MT5/IBKR) without persisting secrets |
| `atlas.auth.user.deactivated` | auth (Spec 01) | Engage user-scope kill switch; disconnect live connections |
| `atlas.privacy.user_erasure.requested` | privacy (Spec 01) | **Mandatory** — delete subscriptions, intents, mandates, paper accounts, venue messages, quote keys; pseudonymize orders/fills/verdicts/positions/reconciliation under execution-record retention; emit `atlas.privacy.user_erasure.completed` ack naming both sets |

## Consumer obligations

- **Idempotency**: every handler wraps its work in `atlas_events.ledger.idempotent` keyed on
  `event_id`. Venue-sourced updates additionally dedupe on `venue_fill_ref` / `venue_order_id`,
  because venues redeliver.
- **Ordering**: consumers must tolerate out-of-order delivery. Order state is reconstructed from
  `order_event.sequence` and venue timestamps, never from event arrival order; a lower-sequence
  update never overwrites a higher one.
- **No self-healing side effects**: no consumer may resubmit, retry, or "fix" an order. Only
  reconciliation writes corrections, and it does so through the trading module's own service.
- **Erasure**: any module that stores data keyed to a user MUST subscribe to
  `atlas.privacy.user_erasure.requested` and emit an ack — a CI contract test fails modules that
  do not (Spec 01 obligation, carried forward).
- **Redaction**: consumers must not log payload bodies verbatim from `venue_message`-derived
  fields; sanitized reason codes only.

## Versioning

Additive fields only within a major version; renames or removals require a new event type with a
`.v2` suffix and a documented dual-publish window. `capability_version` and `spec_version` inside
payloads let consumers detect venue-side semantic changes without an event-schema change.
Event-schema compatibility is enforced by the contract test suite against the registered catalog.
