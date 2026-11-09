# Implementation Plan: Market Intelligence System

**Branch**: `04-market-intelligence` | **Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/spec-04-market-intelligence/spec.md`

## Summary

Deliver Atlas's institutional-grade Market Intelligence System (the "Retail Bloomberg Terminal"): an ingestion, normalization, and analytics platform processing multi-asset price feeds (Forex, Crypto, Commodities, Indices), L2 order books, derivative metrics (aggregate Open Interest, funding rate predictions, liquidation heatmaps), on-chain whale activity and spot ETF flows, economic calendar events, and semantic vector news RAG powered by `pgvector`. Normalized intelligence feeds the LangGraph multi-agent cognitive cortex and streams real-time anomaly alerts to trader cockpits via WebSockets and Kafka within 50ms of detection.

## Technical Context

**Language/Version**: Python 3.12 (ingestion workers, analytics engines in `apps/api`), TypeScript 5.x / Next.js 15 (heatmap dials, liquidation maps, interactive charts in `apps/web`)  
**Primary Dependencies**: FastAPI + Pydantic v2, SQLAlchemy 2 (async) + pgvector, aiokafka, redis-py (Redis 7 pub/sub & stream caching), numpy / scipy (correlation matrices, statistical z-scores), fastembed / sentence-transformers (local vector embeddings), aiohttp / websockets (venue and on-chain streaming)  
**Storage**: PostgreSQL 16 + pgvector (news embeddings, economic releases, COT reports, derivative history), Redis 7 (real-time ticker cache, live heatmaps, whale radar dedup), TimescaleDB / partitioned Postgres (high-frequency bars & metric history), Kafka (`atlas.intelligence.*` topics)  
**Testing**: pytest-asyncio, testcontainers (PostgreSQL with pgvector, Redis, Kafka), synthetic orderbook and liquidation cluster generators, mock on-chain RPC nodes, Schemathesis (OpenAPI & WebSocket verification)  
**Target Platform**: Containerized Linux micro-workers (dedicated ingestion workers per data provider class + FastAPI intelligence router)  
**Performance Goals**: Anomaly detection & Kafka publication < 50ms; 50,000 events/sec sustained throughput; vector HNSW semantic similarity search < 25ms p95; historical candle queries (5,000 bars) < 50ms  
**Constraints**: Zero reliance on floating-point for financial quantities; data source and timestamp attributions required on all surfaced signals; rate-limit compliant ingestion across external news/on-chain APIs; fail-safe defaults when third-party feeds disconnect  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Compliance in this plan | Status |
|---|-----------|------------------------|--------|
| I | Human First | Intelligence data provides unhindered transparency; alerts never execute trades automatically without trader-defined policies. | ✅ |
| II | Security First | API credentials for third-party intelligence providers (Glassnode, NewsAPIs, Arkham) stored sealed in Spec 01 vault. | ✅ |
| III | Transparency | Every intelligence alert, heatmap cell, and derivative metric explicitly displays source origin, capture time, and confidence score. | ✅ |
| IV | Multi-Agent Collab | Normalized intelligence feeds all 13 specialized agents through standardized LangChain tools and Kafka event topics. | ✅ |
| V | Explainability | Vector RAG news returns exact source URLs, published timestamps, and semantic similarity cosine distance. | ✅ |
| VI | Risk Before Profit | Liquidation cascades and funding rate spikes trigger immediate warning flags to Risk and Portfolio agents. | ✅ |
| VII | Continuous Learning | Historical news embeddings and market reaction trajectories stored permanently for historical analogue backtesting. | ✅ |
| VIII | Privacy by Design | Intelligence streams are market-wide public data; user-created alerts and watchlists are strictly scoped to `user_id`. | ✅ |
| IX | Reliability | Multi-source feed aggregation: if Binance derivatives disconnect, Bybit and OKX data maintain aggregate OI calculations. | ✅ |
| X | Modular Architecture | Cleanly separated collectors (`collectors/`), feature calculators (`features/`), and API/streaming handlers (`router.py`). | ✅ |
| XI | Observability | Ingestion lag, message loss rate, parsing error counts, and vector search latencies exported to Prometheus and Grafana. | ✅ |
| XII | Scalability | Kafka topic partitioning by symbol/asset class; distributed Redis read-replicas handle thousands of concurrent dashboard viewers. | ✅ |

**Gate result**: PASS.

## 1. High-Level Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│ External Sources: Binance/Bybit/CME · On-Chain Nodes · Newsfeeds · COT │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Ingestion Workers (Asyncio Workers with Circuit Breakers)              │
│  - WebSocket Ticks, L2 Depth, Liquidations                            │
│  - Derivative Metrics (Open Interest, Funding Rates)                  │
│  - On-Chain Whale Radar (> $1M USD) & Spot ETF Flows                   │
│  - Macro Calendar Releases & RSS/News Feeds                            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Normalization, Embedding & Feature Engine                              │
│  - Decimal Precision Normalization                                    │
│  - Fear & Greed Index Aggregator (0-100)                               │
│  - fastembed / sentence-transformers Text Embedder (1536-dim)          │
│  - Liquidation Cluster & Volatility Expansion Detector                 │
└───────┬───────────────────────────┬────────────────────────────┬───────┘
        │                           │                            │
        ▼                           ▼                            ▼
┌───────────────┐           ┌───────────────┐            ┌───────────────┐
│ PostgreSQL 16 │           │ Redis 7 Cache │            │ Kafka Topics  │
│  + pgvector   │           │  - Heatmaps   │            │ atlas.intelli-│
│  - News RAG   │           │  - Real-time  │            │ gence.alerts  │
│  - Macro COT  │           │    Tickers    │            │ .liquidations │
│  - Deriv Hist │           │  - Whale Dedup│            │ .whales       │
└───────┬───────┘           └───────┬───────┘            └───────┬───────┘
        │                           │                            │
        └───────────────────────────┼────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Distribution Layer: FastAPI Router & Real-Time Engine                  │
│  - WebSocket Stream (/api/v1/intelligence/stream)                      │
│  - REST Endpoints for Heatmap, Derivatives, Whales, Macro              │
│  - LangChain / LangGraph Agent Tools (`tool_search_news_rag`, etc.)    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Consumers: Multi-Agent Platform (Spec 03) & Retail Cockpit (Spec 09)   │
└────────────────────────────────────────────────────────────────────────┘
```

## 2. Directory Structure

```text
specs/spec-04-market-intelligence/
├── spec.md              # Specification document
├── plan.md              # This architecture plan
├── data-model.md        # Data models (derivatives, news, whales, macro)
└── tasks.md             # Test-first task breakdown
```

## 3. Core Technical Decisions & Rationale

### ADR-04-01: pgvector HNSW Indexing for Semantic News & Macro Analogues
- **Context**: Agents require sub-second historical analogue retrieval during fast-moving economic announcements without deploying a separate vector database cluster (e.g. Pinecone or Milvus).
- **Decision**: Leverage PostgreSQL 16 `pgvector` with HNSW cosine similarity indexing (`m = 16, ef_construction = 64`).
- **Consequences**: Zero extra infrastructure complexity; allows transactional JOINs between semantic news embeddings and structured price candle tables.

### ADR-04-02: Multi-Venue Aggregation with Weight-Adjusted Normalization
- **Context**: Open Interest and funding rates reported on individual exchanges provide fragmented pictures that mislead algorithmic analysis.
- **Decision**: Aggregate derivative metrics across Binance, Bybit, OKX, and CME in real-time, computing aggregate OI in USD and volume-weighted funding rates.
- **Consequences**: Accurate systemic leverage overview; eliminates exchange-specific reporting biases.

### ADR-04-03: Reactive Anomaly Detection Pipeline via Kafka & Redis
- **Context**: Polling database tables for whale transfers or liquidation cascades produces unacceptable latency (>5s).
- **Decision**: Ingestion workers evaluate threshold conditions immediately in memory upon packet arrival, emitting to Kafka topics and broadcasting via Redis Pub/Sub directly to connected WebSockets.
- **Consequences**: Sub-50ms glass-to-glass latency from exchange event to trader screen.
