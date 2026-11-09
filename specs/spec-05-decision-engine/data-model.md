# Data Model: Decision Engine & Risk Management

**Feature**: 05-decision-engine | **Date**: 2026-09-21 | **Plan**: [plan.md](./plan.md)

Conventions per Spec 00: UUIDv7 `id` primary keys, `created_at` / `resolved_at` `timestamptz`, snake_case names, enums CHECK-constrained. High-precision numeric columns (`NUMERIC(28, 10)`) mapped strictly to Python `Decimal`. Tables carry indexed `user_id` for multi-tenant isolation.

## decision_proposals

Durable ledger of structured trade recommendations produced by the multi-agent decision pipeline.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| user_id | uuid | FK user; indexed |
| symbol | text | e.g. `BTC/USDT`, `EUR/USD`; indexed |
| direction | text | `LONG | SHORT` |
| confidence_score | numeric(5, 2) | Range: 0.00 to 100.00 |
| entry_range_min | numeric(28, 10) | Minimum allowable entry price |
| entry_range_max | numeric(28, 10) | Maximum allowable entry price |
| stop_loss | numeric(28, 10) | Hard structural invalidation price |
| take_profit_levels | numeric(28, 10)[] | Array of ordered TP prices [TP1, TP2, TP3] |
| risk_reward_ratio | numeric(6, 2) | Minimum 1.50 |
| risk_amount_usd | numeric(28, 10) | Exact maximum loss in USD if SL hit |
| calculated_position_size| numeric(28, 10) | Exact calculated lot/contract quantity |
| proposal_hash | text | SHA-256 integrity hash of trade parameters |
| evidence | jsonb | Array of verified supporting signal strings |
| risks | jsonb | Array of counter-theses and volatility drivers |
| alternative_scenarios| jsonb | Invalidation scenarios ("What if trade fails") |
| debate_transcript | jsonb | Structured Bull, Bear, and Arbitrator logs |
| status | text | `pending_approval | approved | rejected | expired | executed | failed` |
| expires_at | timestamptz | Hard 10-minute expiration timestamp |
| created_at | timestamptz | Proposal creation timestamp; indexed |
| resolved_at | timestamptz | Timestamp of user sign-off or expiration |

**Transitions**: `pending_approval -> approved` (user confirmed); `pending_approval -> rejected` (user passed); `pending_approval -> expired` (TTL elapsed without action); `approved -> executed` (order filled by venue engine); `approved -> failed` (venue rejected).

## decision_risk_rules

User-specific and account-level risk governance parameters enforced by the Pre-Trade Risk Engine.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| user_id | uuid | FK user; unique per account configuration |
| account_id | uuid | FK venue_account |
| max_risk_per_trade_pct| numeric(5, 2) | e.g. 1.00% to 2.00% equity risk |
| max_daily_loss_pct | numeric(5, 2) | Account daily circuit breaker (e.g. 3.00%) |
| max_drawdown_pct | numeric(5, 2) | Peak-to-trough equity kill switch (e.g. 6.00%) |
| max_open_positions | int | Hard limit on concurrent open positions |
| max_leverage | numeric(6, 2) | Leverage ceiling (e.g. 10.00x) |
| max_correlation_threshold| numeric(4, 2) | e.g. 0.70 (blocks correlated directional exposure) |
| macro_embargo_minutes | int | Minutes to pause trading before/after high-impact CPI/NFP (default 30) |
| is_active | boolean | Toggles rule enforcement |

## decision_veto_logs

Immutable audit log of proposals blocked by the Pre-Trade Risk Engine.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| proposal_id | uuid | Reference to candidate proposal |
| user_id | uuid | FK user; indexed |
| symbol | text | Asset symbol under consideration |
| violated_rule | text | e.g. `DAILY_LOSS_LIMIT_REACHED`, `CORRELATION_TOO_HIGH`, `MACRO_EMBARGO_ACTIVE` |
| current_metric_value| text | Observed metric (e.g. `Current Daily Loss: 3.15%`) |
| allowed_threshold | text | Configured ceiling (e.g. `Max Daily Loss: 3.00%`) |
| metrics_snapshot | jsonb | Complete portfolio risk state at veto time |
| vetoed_at | timestamptz | Timestamp of programmatic rejection; indexed |

## decision_evaluations

Analytical records of ad-hoc market assessments and Bayesian confidence calibrations.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| symbol | text | Asset symbol; indexed |
| timeframe | text | Analysis timeframe |
| indicator_confluence_score | numeric(5, 2) | Confluence component (30% weight) |
| multi_agent_consensus_score | numeric(5, 2) | Consensus component (25% weight) |
| debate_outcome_score | numeric(5, 2) | Dialectic balance component (20% weight) |
| market_regime_stability | numeric(5, 2) | Regime stability component (15% weight) |
| onchain_sentiment_score | numeric(5, 2) | Sentiment component (10% weight) |
| calibrated_confidence | numeric(5, 2) | Final Bayesian score (0.00 to 100.00) |
| recommendation | text | `STRONG_BUY | BUY | WAIT | SELL | STRONG_SELL` |
| evaluated_at | timestamptz | Timestamp of evaluation; indexed |
