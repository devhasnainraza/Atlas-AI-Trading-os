# Data Model: Memory, Journal & Learning

**Feature**: 07-memory-learning | **Date**: 2026-09-21 | **Plan**: [plan.md](./plan.md)

Conventions per Spec 00: UUIDv7 `id` primary keys, `created_at` `timestamptz`, snake_case names, enums CHECK-constrained. High-precision numeric columns (`NUMERIC(28, 10)` and `NUMERIC(6, 2)`) mapped strictly to Python `Decimal`. Tables carry indexed `user_id` enforcing strict tenant and privacy isolation.

## journal_entries

Comprehensive automated and annotated trade journal records capturing execution, context, and post-mortem review.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| user_id | uuid | FK user; indexed |
| order_id | uuid | FK order; unique |
| account_id | uuid | FK venue_account; indexed |
| symbol | text | e.g. `EUR/USD`, `BTC/USDT` |
| side | text | `LONG | SHORT` |
| entry_price | numeric(28, 10) | Average fill price at entry |
| exit_price | numeric(28, 10) | Average fill price at close |
| entry_time | timestamptz | Timestamp position was opened |
| exit_time | timestamptz | Timestamp position was closed |
| net_pnl | numeric(28, 10) | Net realized profit/loss in account currency |
| r_multiple | numeric(6, 2) | Profit expressed as multiples of initial risk (e.g. `+2.40R`, `-1.00R`) |
| fees_usd | numeric(28, 10) | Total commissions, funding fees, and exchange costs |
| slippage_pips | numeric(8, 4) | Execution price deviation from intended price |
| chart_image_url | text | URL to WebP chart screenshot in MinIO/S3 |
| technical_indicators| jsonb | Indicator values (RSI, ATR, EMAs) at entry/exit |
| ai_post_mortem | text | Synthesis comparing thesis hypothesis vs. price reality |
| user_notes | text | Trader subjective journal notes |
| emotional_tags | text[] | Tags: `['CALM', 'FOMO', 'REVENGE', 'GREED', 'FEAR', 'DISCIPLINED']` |
| user_rating | int | Self-evaluation rating (1 to 5 stars) |
| created_at | timestamptz | Journal record creation timestamp; indexed |

## memory_user_embeddings

Long-term episodic and semantic memory store capturing trader preferences, established rules, and behavioral context.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| user_id | uuid | FK user; indexed |
| scope | text | `STRATEGY | BEHAVIOR | GOALS | RULES | LESSONS` |
| memory_text | text | Human-readable statement of rule or observation |
| embedding | vector(1536) | Text embedding vector; HNSW cosine indexed per user |
| importance_weight | numeric(3, 2) | Weight factor (0.10 to 1.00) influencing retrieval priority |
| last_retrieved_at | timestamptz | Timestamp memory was last injected into an agent prompt |
| created_at | timestamptz | Ingestion timestamp; indexed |

## learning_bias_profiles

Evolving psychological and behavioral diagnostic scores calculated for each active trader.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| user_id | uuid | FK user; unique per user |
| fomo_score | numeric(5, 2) | Score (0.00 to 1.00) measuring chasing momentum entries |
| revenge_trading_score| numeric(5, 2) | Score (0.00 to 1.00) measuring rapid loss-recovery attempts |
| loss_aversion_score | numeric(5, 2) | Score (0.00 to 1.00) measuring widening stops or holding losers |
| overtrading_score | numeric(5, 2) | Score (0.00 to 1.00) measuring volume above baseline |
| discipline_rating | numeric(5, 2) | Aggregate adherence to stated trading rules (0.00 to 100.00) |
| top_mistake_triggers| text[] | High-frequency error patterns (e.g. `['LATE_NY_SESSION', 'FRIDAY_CLOSE']`) |
| last_updated | timestamptz | Timestamp of latest diagnostic recalculation |

## learning_coaching_reports

Weekly performance reviews and prescriptive coaching recommendations compiled by the Learning Agent.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| user_id | uuid | FK user; indexed |
| period_start | date | Weekly evaluation start date |
| period_end | date | Weekly evaluation end date |
| net_pnl | numeric(28, 10) | Total net earnings for the period |
| profit_factor | numeric(6, 2) | Gross profits divided by gross losses |
| win_rate | numeric(5, 2) | Percentage of winning trades (0.00 to 100.00) |
| total_trades | int | Count of closed positions evaluated |
| disciplined_actions | jsonb | Array of positive reinforcement examples |
| cognitive_bias_warnings| jsonb | Identified behavioral traps with specific trade citations |
| recommendations | jsonb | Concrete rules recommended for the following week |
| created_at | timestamptz | Generation timestamp; indexed |
