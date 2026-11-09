# Data Model: Market Intelligence System

**Feature**: 04-market-intelligence | **Date**: 2026-09-21 | **Plan**: [plan.md](./plan.md)

Conventions per Spec 00: UUIDv7 `id` primary keys, `created_at` `timestamptz`, snake_case names, enums CHECK-constrained. High-precision numeric columns (`NUMERIC(28, 10)` and `NUMERIC(24, 8)`) strictly mapped to Python `Decimal`. Vector columns utilize `pgvector` extension.

## intelligence_news_embeddings

Semantic vector-indexed financial news, regulatory filings, and macroeconomic headlines.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| source | text | e.g. `reuters`, `bloomberg`, `coindesk`, `sec_edgar` |
| title | text | Headline title |
| content_summary | text | LLM or extractive summary of content |
| url | text | Canonical source URL |
| sentiment_score | numeric(5, 4) | Range: -1.0000 (extreme bear) to +1.0000 (extreme bull) |
| impact_level | text | `LOW | MEDIUM | HIGH | CRITICAL` |
| entities | text[] | Extracted ticker tags (e.g. `['BTC', 'ETH', 'FED']`) |
| embedding | vector(1536) | Text embedding vector; HNSW cosine indexed |
| published_at | timestamptz | Source publication timestamp; indexed |
| created_at | timestamptz | Ingestion timestamp |

## intelligence_derivatives

Granular periodic snapshots of Open Interest, funding rates, and liquidation metrics across exchanges.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| symbol | text | e.g. `BTC/USDT`, `ETH/USDT`, `SOL/USDT`; indexed |
| venue | text | `binance | bybit | okx | aggregate` |
| open_interest | numeric(28, 10) | Total contracts or coin units open |
| open_interest_usd | numeric(28, 10) | USD notional value of open interest |
| funding_rate | numeric(10, 8) | 8-hour funding rate (e.g. `0.00010000` = 0.01%) |
| predicted_funding_rate | numeric(10, 8) | Estimated next-interval funding rate |
| long_short_ratio | numeric(6, 4) | Top trader account long/short ratio |
| estimated_liquidations_long | numeric(28, 10) | Volume at risk on next 2% drop (USD) |
| estimated_liquidations_short| numeric(28, 10) | Volume at risk on next 2% rise (USD) |
| recorded_at | timestamptz | Observation timestamp; indexed |

## intelligence_whale_transfers

Large on-chain transactions and exchange netflows exceeding institutional materiality thresholds.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| blockchain | text | `bitcoin | ethereum | solana | tron` |
| tx_hash | text | Unique blockchain transaction hash |
| from_address | text | Originating wallet address |
| to_address | text | Destination wallet address |
| from_entity | text | Known entity label (e.g. `Coinbase Custody`, `Binance Hot Wallet`) |
| to_entity | text | Known entity label |
| asset | text | `BTC | ETH | USDT | USDC` |
| amount | numeric(28, 10) | Token quantity transferred |
| amount_usd | numeric(24, 2) | USD notional equivalent at transaction time |
| transfer_type | text | `exchange_inflow | exchange_outflow | wallet_to_wallet | internal_transfer` |
| detected_at | timestamptz | Ingestion timestamp; indexed |

## intelligence_etf_flows

Daily institutional net creations and redemptions for spot Bitcoin and Ethereum exchange-traded funds.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| ticker | text | e.g. `IBIT`, `FBTC`, `ARKB`, `BITB`, `ETHA` |
| fund_issuer | text | `BlackRock | Fidelity | ArkInvest | Bitwise` |
| asset | text | `BTC | ETH` |
| net_flow_usd | numeric(24, 2) | Net daily inflow (+USD) or outflow (-USD) |
| shares_change | numeric(20, 2) | Change in outstanding fund shares |
| total_holdings_coin | numeric(28, 10) | Total underlying coin held in custody |
| report_date | date | Official fund reporting date; indexed |

## intelligence_macro_events

Scheduled global economic announcements, consensus estimates, and reported metrics.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| country | text | ISO 2-letter country code (e.g. `US`, `EU`, `UK`, `JP`) |
| event_name | text | e.g. `CPI YoY`, `Federal Funds Rate`, `Non-Farm Payrolls` |
| impact_level | text | `LOW | MEDIUM | HIGH` |
| previous_value | text | Formatted previous release value |
| forecast_value | text | Consensus estimate value |
| actual_value | text | Official reported value; NULL until released |
| surprise_pct | numeric(6, 2) | Deviation from forecast percentage |
| release_date | timestamptz | Scheduled announcement time; indexed |

## intelligence_cot_reports

Weekly institutional futures positioning data from CFTC Commitment of Traders releases.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| contract_name | text | e.g. `Euro FX`, `Japanese Yen`, `Bitcoin`, `Gold` |
| report_date | date | CFTC Tuesday snapshot date; indexed |
| commercial_long | bigint | Commercial hedging long open contracts |
| commercial_short| bigint | Commercial hedging short open contracts |
| non_commercial_long | bigint | Speculative institutional long open contracts |
| non_commercial_short| bigint | Speculative institutional short open contracts |
| open_interest | bigint | Total open interest in contract |
| net_speculative_position | bigint | `non_commercial_long - non_commercial_short` |
