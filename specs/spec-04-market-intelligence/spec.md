# Spec 04 — Market Intelligence System

**Project**: Atlas AI Trading OS  
**Status**: Ratified | **Version**: 1.0.0 | **Date**: 2026-09-21  
**Target Path**: `specs/spec-04-market-intelligence/`  
**Constitutional Compliance**: Core Principles III, V, IX, X, XI, XII Verified  

---

## 1. Vision & Goals

### 1.1 System Vision
Spec 04 builds the "Retail Bloomberg Terminal" inside Atlas AI Trading OS. Retail traders historically face an insurmountable information asymmetry against institutional algorithmic funds. Spec 04 levels the playing field by aggregating, synthesizing, and streaming institutional-grade market data, order flow analytics, on-chain whale activity, derivative positioning metrics, and macroeconomic signals into real-time visual cockpits and AI agent memory streams.

### 1.2 Core Business & Technical Goals
- **Holistic Market Synthesis**: Unify disparate data silos—price action, order book depth, liquidation clusters, on-chain flows, social sentiment, and macro fundamentals—into a single normalized intelligence graph.
- **Institutional Derivative Analytics**: Surface hidden liquidity and leverage risks through real-time Open Interest (OI) tracking, perpetual funding rates, and volume delta profiles.
- **On-Chain Whale & Smart Money Surveillance**: Continuously monitor major crypto exchange inflows/outflows, high-net-worth wallet transfers, and Bitcoin/Ethereum spot ETF net creations/redemptions.
- **Semantic Financial Knowledge Retrieval**: Real-time vector-indexed news and macroeconomic events powered by `pgvector`, providing sub-second semantic retrieval of historical analogues for current market setups.
- **Zero-Latency Reactive Signal Pipeline**: High-performance Kafka pipelines distributing anomaly alerts (e.g. whale buy wall, funding squeeze, volume spike) to agents and traders within 50ms of detection.

---

## 2. Functional Requirements

- **FR-001**: The platform MUST ingest, normalize, and stream live price ticks and candle intervals across Forex majors/minors, Crypto top 100, Commodities (Gold, Oil), and Indices (S&P 500, DXY).
- **FR-002**: The platform MUST compute and render multi-asset Market Heatmaps color-coded by percentage change, relative volume (RVOL), and implied volatility.
- **FR-003**: The platform MUST calculate cross-asset correlation matrices (e.g. BTC vs. DXY, Gold vs. Real Yields) updated dynamically on rolling 30-day and 90-day windows.
- **FR-004**: Derivative intelligence MUST ingest and process:
  - Aggregate Open Interest across major exchanges (Binance, Bybit, OKX, CME).
  - Perpetual funding rate heatmaps and predicted next-funding rates.
  - Estimated liquidation price clusters and liquidation cascade alerts.
- **FR-005**: On-chain intelligence MUST track and surface:
  - Exchange Netflow (inflow/outflow of BTC, ETH, USDT/USDC).
  - Whale wallet tracking (transactions exceeding $1,000,000 equivalent).
  - Daily US Spot Bitcoin and Ethereum ETF net inflows and outflows.
- **FR-006**: Sentiment intelligence MUST compute a normalized Fear & Greed Index (0–100) combining volatility, market momentum, social volume, survey data, and search interest.
- **FR-007**: Macro intelligence MUST parse and maintain:
  - Global economic calendars with consensus, previous, and actual metrics.
  - Institutional positioning data from weekly CFTC Commitment of Traders (COT) reports.
  - Central bank policy rate paths and balance sheet trajectories.
- **FR-008**: The news intelligence engine MUST scrape verified financial news feeds, extract financial entities, and index contextual embeddings in `pgvector` for semantic RAG lookups.

---

## 3. Non-Functional Requirements

- **NFR-001 (Market Data Throughput)**: The intelligence pipeline MUST process up to 50,000 external market events/sec during high-volatility sessions without packet dropping.
- **NFR-002 (Anomaly Detection Latency)**: Liquidation clusters and whale wallet alerts MUST be calculated and published to the event bus within 100ms of on-chain or exchange confirmation.
- **NFR-003 (Historical Query Response)**: Historical multi-timeframe candle queries (up to 5,000 bars) MUST return in < 50ms from optimized Timescale/PostgreSQL partitions.
- **NFR-004 (Vector Semantic Search Latency)**: Similarity lookups against news embeddings using HNSW indexing in `pgvector` MUST complete in < 25ms at p95.
- **NFR-005 (Data Accuracy & Attributions)**: Every intelligence widget and agent signal MUST display its underlying data source, timestamp, and confidence rating.

---

## 4. User Stories

### US-001: Trader Spots Liquidation Squeeze via Heatmap (Priority: P1)
- **Given** an active crypto trader monitoring `BTC/USDT`,
- **When** open interest surges while price approaches a dense short-liquidation cluster at $68,500,
- **Then** the Market Intelligence system surfaces a "Liquidation Squeeze Alert", displaying the volume at risk and probability of an explosive breakout.

### US-002: AI Agent Queries Historical Analogues via Vector Search (Priority: P1)
- **Given** the Technical Agent identifying an unusual ICT Fair Value Gap (FVG) on EUR/USD preceding an FOMC rate decision,
- **When** the agent queries the market intelligence vector store for similar setups,
- **Then** the system returns the top 3 historical instances with their post-announcement price trajectories and volatility distributions.

### US-003: Whale Movement Alerts Trader to Imminent Sell Pressure (Priority: P2)
- **Given** a dormant whale wallet transferring 5,000 BTC to a Binance deposit address,
- **When** the transaction confirms on-chain,
- **Then** the Whale Tracking engine emits an event that updates the trader's dashboard widget and alerts the Risk Agent to re-evaluate open long exposure.

---

## 5. Agent Architecture

The Market Intelligence system serves as the sensory cortex for all analytical agents:

```text
+-------------------------------------------------------------------------+
|                        Market Intelligence Layer                        |
|                                                                         |
|  +--------------------+   +---------------------+   +----------------+  |
|  | Price & Order Flow |   | Derivative Analytics|   | On-Chain Whale |  |
|  | - Ticks & L2/L3    |   | - Open Interest     |   | - Netflows     |  |
|  | - CVD & Footprint  |   | - Funding Rates     |   | - ETF flows    |  |
|  +---------+----------+   +----------+----------+   +--------+-------+  |
|            |                         |                       |          |
|            +-------------------------+-----------------------+          |
|                                      |                                  |
|                         +------------v------------+                     |
|                         | Normalization & Feature |                     |
|                         |      Signal Engine      |                     |
|                         +------------+------------+                     |
|                                      |                                  |
|           +--------------------------+-------------------------+        |
|           |                                                    |        |
|  +--------v---------+                                 +--------v-----+  |
|  | pgvector Semantic|                                 | Kafka Signal |  |
|  | News & Macro RAG |                                 | Distribution |  |
|  +------------------+                                 +--------------+  |
+-------------------------------------------------------------------------+
```

---

## 6. State Design

### 6.1 Market Anomaly Event Schema
```python
@dataclass(frozen=True)
class MarketAnomalyEvent:
    anomaly_id: str
    symbol: str
    anomaly_type: str  # LIQUIDATION_CASCADE | FUNDING_SPIKE | WHALE_INFLOW | VOLATILITY_EXPANSION
    severity: str      # LOW | MEDIUM | HIGH | CRITICAL
    detected_at: datetime
    metrics: dict[str, Any]
    source_venue: str
    confidence: Decimal
```

### 6.2 Heatmap State Model
```python
@dataclass(frozen=True)
class AssetHeatmapNode:
    symbol: str
    category: str      # FOREX | CRYPTO | COMMODITY
    price: Decimal
    change_24h_pct: Decimal
    relative_volume: Decimal
    funding_rate: Decimal | None
    sentiment_score: Decimal  # -1.00 to +1.00
```

---

## 7. LangGraph Workflow Integration

Intelligence data feeds directly into the initial research phase of LangGraph pipelines:

```text
[LangGraph Workflow: Market Analysis]
                 |
                 v
+--------------------------------+
| Market Intelligence Gathering  |  Parallel fetches:
|             Node               |  - Live Ticks & Order Flow
+----------------+---------------+  - On-Chain Inflows & Whale Alerts
                 |                  - Macro Calendar & Vector News RAG
                 v
+--------------------------------+
| Feature Vector Synthesis Node  |  Calculates sentiment score, momentum,
+----------------+---------------+  and structural market regime
                 |
                 v
+--------------------------------+
| Dispatched to Analytical Agents|  (Technical, Economic, Social Agents)
+--------------------------------+
```

---

## 8. Tool Specifications

### 8.1 On-Chain Netflow Query Tool (`tool_query_onchain_flows`)
- **Description**: Retrieves net exchange inflows and outflows for major crypto assets.
- **Input Schema**:
  ```json
  {
    "type": "object",
    "required": ["asset", "window_hours"],
    "properties": {
      "asset": { "type": "string", "enum": ["BTC", "ETH", "USDT"] },
      "window_hours": { "type": "integer", "default": 24 }
    }
  }
  ```
- **Output Schema**: Returns `{ "netflow_units": "1420.5", "netflow_usd": "95000000", "bias": "OUTFLOW_BULLISH" }`.

### 8.2 Semantic News RAG Search Tool (`tool_search_news_rag`)
- **Description**: Performs vector similarity search over historical news and macro releases.
- **Input Schema**:
  ```json
  {
    "type": "object",
    "required": ["query_text", "limit"],
    "properties": {
      "query_text": { "type": "string" },
      "limit": { "type": "integer", "default": 5 },
      "filter_tags": { "type": "array", "items": { "type": "string" } }
    }
  }
  ```

---

## 9. API Specifications

### 9.1 Intelligence REST Endpoints
- **`GET /api/v1/intelligence/heatmap`**: Returns live multi-asset heatmap status.
- **`GET /api/v1/intelligence/derivatives/{symbol}`**: Returns Open Interest, predicted funding rate, and liquidation clusters.
- **`GET /api/v1/intelligence/onchain/whales`**: Returns recent whale transactions (> $1M).
- **`GET /api/v1/intelligence/macro/calendar`**: Returns scheduled high-impact economic events with historical surprise factors.
- **`GET /api/v1/intelligence/sentiment/fear-greed`**: Returns current and historical Fear & Greed index values.

### 9.2 Real-Time WebSocket Channel
- **`WS /api/v1/intelligence/stream`**:
  - Emits real-time anomaly alerts (`liquidation_spike`, `whale_transfer`, `breaking_news`).

---

## 10. Database Schema

### 10.1 Market News Embeddings Table (`intelligence_news_embeddings`)
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE intelligence_news_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(64) NOT NULL,
    title TEXT NOT NULL,
    content_summary TEXT NOT NULL,
    url VARCHAR(512),
    sentiment_score NUMERIC(5, 4) NOT NULL, -- -1.0000 to +1.0000
    impact_level VARCHAR(16) NOT NULL,      -- LOW | MEDIUM | HIGH
    entities VARCHAR(64)[] NOT NULL,
    embedding vector(1536) NOT NULL,        -- OpenAI / fast-embed model vector
    published_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_news_embedding_hnsw 
ON intelligence_news_embeddings 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_news_published ON intelligence_news_embeddings (published_at DESC);
```

### 10.2 Derivative Metrics Table (`intelligence_derivatives`)
```sql
CREATE TABLE intelligence_derivatives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(32) NOT NULL,
    venue VARCHAR(32) NOT NULL,
    open_interest NUMERIC(28, 10) NOT NULL,
    open_interest_usd NUMERIC(28, 10) NOT NULL,
    funding_rate NUMERIC(10, 8) NOT NULL,
    long_short_ratio NUMERIC(6, 4) NOT NULL,
    estimated_liquidations_long NUMERIC(28, 10) NOT NULL,
    estimated_liquidations_short NUMERIC(28, 10) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_derivatives_symbol_time ON intelligence_derivatives (symbol, recorded_at DESC);
```

---

## 11. Frontend Screens & Components

### 11.1 Retail Bloomberg Market Cockpit
- **Interactive Multi-Asset Treemap**: Responsive grid displaying asset tiles sized by market cap and colored by 24h change, featuring real-time hover sparklines.
- **Liquidation Heatmap Visualizer**: Depth chart overlay showing concentrated clusters of liquidation leverage bands above and below current price.
- **Whale Radar Feed**: Live ticker displaying high-value transfers with source and destination tags (e.g. `Coinbase Pro -> Unknown Wallet`).
- **Macro Radar Gauge**: Compact card tracking next major economic release with countdown timer and consensus estimate.

---

## 12. Security Requirements

- **SEC-001 (Source Verification)**: News feeds and on-chain scrapers run signature verification where applicable to prevent spoofed news attacks.
- **SEC-002 (Rate Limit Compliance)**: External API aggregators employ token bucket rate limiters to avoid provider bans or service degradation.
- **SEC-003 (Vector Injection Defense)**: Text embeddings sanitization removes prompt injection directives before storing news summaries in RAG databases.

---

## 13. Testing Strategy

- **On-Chain Netflow Parser Conformance**: Replay historical blockchain blocks to confirm exact whale transfer detection and balance updates.
- **Vector Search Accuracy Benchmark**: Evaluate precision and recall of RAG queries using ground-truth financial news datasets.
- **High-Throughput Load Simulation**: Stress test market intelligence WebSocket servers at 50,000 messages/sec with zero memory leaks.

---

## 14. Deployment Plan

- **Dedicated Scraping & Ingestion Pods**: Independent worker deployment handling external WebSocket connections (CoinGecko, CryptoQuant, Glassnode, SEC EDGAR, ForexFactory).
- **PostgreSQL pgvector Optimization**: Memory allocation tuned for HNSW index caching (`shared_buffers` and `work_mem` configured for vector operations).

---

## 15. Future Enhancements

- **Machine Learning Regime Classification**: Hidden Markov Models (HMM) and Gaussian Mixture Models dynamically classifying market regimes (Trending, Ranging, High Volatility, Liquidity Vacuum).
- **Satellite & Alternative Data Ingestion**: Satellite imagery supply chain tracking and maritime oil tanker transponder data ingestion for macro commodities intelligence.
