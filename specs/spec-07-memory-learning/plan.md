# Implementation Plan: Memory, Journal & Learning

**Branch**: `07-memory-learning` | **Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/spec-07-memory-learning/spec.md`

## Summary

Deliver Atlas's cognitive memory, automated trade journaling, and behavioral learning subsystem: an integrated framework that captures trade executions with zero human effort (generating WebP chart snapshots, technical indicator context, and AI post-mortems within 3 seconds), maintains secure per-user episodic Long-Term Memory (LTM) indexed via `pgvector`, detects cognitive trading biases (FOMO, revenge trading, loss aversion, overtrading), and delivers personalized weekly AI coaching diagnostics. All user memory is strictly isolated and subject to instant cryptographic erasure under Principle VIII.

## Technical Context

**Language/Version**: Python 3.12 (journal ingestion, behavioral analytics, memory vector search in `apps/api`), TypeScript 5.x / Next.js 15 (trade journal timeline, emotion tagger, coaching cards in `apps/web`)  
**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2 (async) + pgvector, Playwright / headless Chromium (chart screenshot capture), Pillow / webp (image compression), fastembed / sentence-transformers (1536-dim memory embeddings), Celery Beat (weekly coaching report generation)  
**Storage**: PostgreSQL 16 + pgvector (journal entries, user memory embeddings, coaching reports, cognitive bias profiles), MinIO / S3 (compressed chart screenshot artifacts), Redis 7 (recent memory cache, rapid loss sequence counters)  
**Testing**: pytest-asyncio, testcontainers (Postgres with pgvector), synthetic trade sequence generators (simulating revenge trading bursts and emotional tags), image generation mocks, Schemathesis (API contracts)  
**Target Platform**: Distributed container workers (dedicated chart rendering worker pool + journal processing service)  
**Performance Goals**: Auto-journal entry generation < 3s from venue position close; semantic memory lookup < 20ms p95; chart image WebP compression < 250KB; sub-second paginated queries over millions of historical journal rows  
**Constraints**: Absolute ban on floating-point arithmetic for financial figures (`Decimal` / `NUMERIC(28,10)`); user memory vectors strictly isolated by `user_id` with zero cross-tenant leak; full crypto-shredding / deletion within 24 hours of GDPR erasure request  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Compliance in this plan | Status |
|---|-----------|------------------------|--------|
| I | Human First | Coaching insights are supportive and advisory; emotional self-tagging is optional; user retains complete ownership of journal data. | ✅ |
| II | Security First | Chart images and journal notes stored in access-controlled object storage; presigned URLs with 15-minute expiration used for display. | ✅ |
| III | Transparency | Every post-mortem, R-multiple calculation, and bias score displays exact mathematical formulas and underlying trade timestamps. | ✅ |
| IV | Multi-Agent Collab | Journal, Memory, and Learning agents collaborate to feed user context into Manager Agent's planning loop. | ✅ |
| V | Explainability | Bias warnings cite specific historical trades, elapsed minutes between orders, and realized win rates to justify coaching advice. | ✅ |
| VI | Risk Before Profit | Learning Agent actively detects revenge trading streaks and alerts the Risk Engine to enforce cooling-off periods. | ✅ |
| VII | Continuous Learning | Core implementation of Principle VII: transforms raw trade executions into institutional knowledge and improved discipline. | ✅ |
| VIII | Privacy by Design | Memory embeddings never pooled for global training; hard deletion cascading ensures complete erasure upon account closure. | ✅ |
| IX | Reliability | Asynchronous decoupled journaling: failure of chart rendering service never impedes trade closure or venue execution. | ✅ |
| X | Modular Architecture | Memory and journaling module cleanly separated from trading execution adapters, interacting via Kafka `atlas.trading.position_closed`. | ✅ |
| XI | Observability | Journal processing latencies, chart capture durations, and vector lookup performance exported to Prometheus. | ✅ |
| XII | Scalability | `journal_entries` table partitioned by year/month; pgvector HNSW index configured with per-user filter clauses. | ✅ |

**Gate result**: PASS.

## 1. High-Level Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│ Venue Event: Position Closed (`atlas.trading.position_closed`)         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Journal Ingestion Worker (services/worker/src/journal/)                │
│  - Captures entry/exit prices, timestamps, realized PnL, R-multiple   │
│  - Pulls snapshot of Technical Indicators at entry/exit                │
│  - Dispatches Headless Browser to capture chart WebP (< 250KB)         │
│  - Invokes Journal Agent for AI Post-Mortem Synthesis                  │
└───────┬───────────────────────────┬────────────────────────────┬───────┘
        │                           │                            │
        ▼                           ▼                            ▼
┌───────────────┐           ┌───────────────┐            ┌───────────────┐
│ PostgreSQL 16 │           │ MinIO / S3    │            │ Behavioral    │
│  journal_     │           │  - Chart WebP │            │ Analytics     │
│  entries      │           │    Artifacts  │            │ Daemon        │
└───────┬───────┘           └───────────────┘            └───────┬───────┘
        │                                                        │
        │                                                        ▼
        │                                           ┌────────────────────┐
        │                                           │ Learning Agent     │
        │                                           │  - Revenge Trading │
        │                                           │  - Overtrading     │
        │                                           │  - Weekly Coaching │
        │                                           └────────────┬───────┘
        │                                                        │
        └───────────────────────────┬────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ User Memory & RAG Subsystem (`memory_user_embeddings`)                 │
│  - Embeds trading rules, preferred symbols, and identified blind spots │
│  - Sub-20ms semantic search provides context to active LangGraph agents│
└────────────────────────────────────────────────────────────────────────┘
```

## 2. Directory Structure

```text
specs/spec-07-memory-learning/
├── spec.md              # Specification document
├── plan.md              # This architecture plan
├── data-model.md        # Data models (journal, memory, biases, coaching)
└── tasks.md             # Test-first task breakdown
```

## 3. Core Technical Decisions & Rationale

### ADR-07-01: Headless Chart Snapshot via Headless Browser Worker Pool
- **Context**: Visual chart context with exact entry, exit, and stop levels is essential for trade post-mortems, but rendering complex TradingView lightweight charts on the server is non-trivial.
- **Decision**: Deploy a dedicated lightweight worker pool running headless Chromium via Playwright, rendering a localized HTML/JS chart template with trade markers, and exporting compressed WebP (<250KB) to S3/MinIO.
- **Consequences**: Deterministic, zero-effort visual trade capture in <3 seconds without taxing the main API server.

### ADR-07-02: Isolated Per-User Vector Space for Cognitive Memory
- **Context**: Mixing user memories in a shared vector space risks accidental privacy leakage or cross-contamination of trading styles.
- **Decision**: All vector search queries against `memory_user_embeddings` enforce a strict `WHERE user_id = :user_id` SQL filter clause alongside HNSW vector index lookups.
- **Consequences**: Guarantees zero cross-tenant contamination while maintaining sub-20ms query latency.

### ADR-07-03: Asynchronous Behavioral Diagnostics & Cooldown Recommendations
- **Context**: Checking for psychological tilt (e.g. revenge trading) must not block order processing, but timely intervention is necessary.
- **Decision**: On position close with loss, evaluate recent order timestamps in Redis. If a new trade is submitted within 5 minutes with higher risk, emit a non-blocking advisory notification and surface an optional cooldown dialog.
- **Consequences**: Respects human autonomy while providing a psychological safety net.
