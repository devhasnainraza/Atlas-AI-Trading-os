# Tasks: Market Intelligence System

**Input**: Design documents from `/specs/spec-04-market-intelligence/`
**Prerequisites**: [spec.md](./spec.md), Spec 00 (event bus), Spec 02 (market data)
**Tests**: INCLUDED — vector similarity accuracy, liquidation calculation invariants, and throughput stress benchmarks.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: `US1`–`US3`, or blank for setup/foundational/polish

---

## Phase 1: Setup

- [ ] T001 [P] Scaffold market intelligence module skeleton in `apps/api/src/atlas_api/modules/intelligence/`
- [ ] T002 [P] Configure `IntelligenceSettings` (vector model configs, scraper API keys: Glassnode, CryptoQuant, ForexFactory, rate limits) in `shared/atlas_core/config.py`
- [ ] T003 [P] Register intelligence events in `shared/atlas_events/catalog.py`: `market.anomaly.detected`, `market.whale.transferred`, `market.liquidation.cascade`

---

## Phase 2: Foundational (⚠️ CRITICAL — blocks every user story)

- [ ] T004 [P] Enable `pgvector` extension and create migration for `intelligence_news_embeddings` and `intelligence_derivatives` tables
- [ ] T005 [P] Implement HNSW index creation and cosine similarity search helper in `apps/api/src/atlas_api/modules/intelligence/repository/embeddings.py`
- [ ] T006 [P] Implement Market Feature Normalization Engine mapping heterogeneous exchange depth and OI to uniform schemas

---

## Phase 3: User Story 1 — Multi-Asset Heatmap & Derivative Intelligence (Priority: P1) 🎯 MVP

**Goal**: Traders and agents inspect real-time market heatmaps, Open Interest, funding rates, and liquidation clusters.

### Tests for User Story 1 ⚠️ write first, must fail

- [ ] T007 [P] [US1] Unit test: Liquidation cluster calculator accurately aggregates leverage bands
- [ ] T008 [P] [US1] Integration test: Heatmap generation across 100 symbols completes in < 50ms
- [ ] T009 [P] [US1] Contract test: `/api/v1/intelligence/derivatives/{symbol}` vs OpenAPI schema

### Implementation for User Story 1

- [ ] T010 [US1] Implement Open Interest and Funding Rate aggregation service in `apps/api/src/atlas_api/modules/intelligence/service/derivatives.py`
- [ ] T011 [US1] Implement Liquidation Heatmap calculation engine in `apps/api/src/atlas_api/modules/intelligence/domain/liquidations.py`
- [ ] T012 [US1] Implement REST endpoints `GET /api/v1/intelligence/heatmap` and `/derivatives/{symbol}`
- [ ] T013 [P] [US1] Web: Interactive Treemap & Liquidation Heatmap visualizer in `apps/web/src/features/intelligence/`

---

## Phase 4: User Story 2 — Semantic News & Macro RAG (Priority: P1)

**Goal**: AI agents retrieve historical market analogues and real-time news context via vector similarity search.

### Tests for User Story 2 ⚠️ write first, must fail

- [ ] T014 [P] [US2] Benchmark test: Vector similarity search returns top 5 relevant financial news items in < 25ms
- [ ] T015 [P] [US2] Integration test: News headline ingestion -> embedding generation -> vector storage pipeline

### Implementation for User Story 2

- [ ] T016 [US2] Implement News Ingestion worker scraping RSS/financial APIs and generating embeddings via `shared/atlas_ai/providers.py`
- [ ] T017 [US2] Implement Economic Calendar parser and surprise factor calculator in `apps/api/src/atlas_api/modules/intelligence/service/macro.py`
- [ ] T018 [US2] Implement Agent Tool `tool_search_news_rag` for semantic search queries
- [ ] T019 [P] [US2] Web: Macro Calendar & Breaking News ticker widget with sentiment badges

---

## Phase 5: User Story 3 — On-Chain Whale & ETF Tracking (Priority: P2)

**Goal**: Surface high-value crypto transfers, exchange netflows, and institutional ETF creations/redemptions.

### Tests for User Story 3 ⚠️ write first, must fail

- [ ] T020 [P] [US3] Unit test: Whale transfer detector flags transactions > $1M and classifies exchange addresses
- [ ] T021 [P] [US3] Integration test: Inflow event emission triggers alert on WebSocket stream

### Implementation for User Story 3

- [ ] T022 [US3] Implement On-chain Exchange Netflow tracker in `apps/api/src/atlas_api/modules/intelligence/service/onchain.py`
- [ ] T023 [US3] Implement US Spot Bitcoin/Ethereum ETF daily flow parser in `services/worker/src/jobs/etf_flows.py`
- [ ] T024 [US3] Implement `GET /api/v1/intelligence/onchain/whales` endpoint and WebSocket broadcast
- [ ] T025 [P] [US3] Web: Whale Radar widget in `apps/web/src/features/intelligence/`

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T026 [P] Stress test intelligence WebSocket server under 50,000 messages/sec load
- [ ] T027 [P] Grafana dashboards: Scraper latency, vector search duration, and Kafka throughput
