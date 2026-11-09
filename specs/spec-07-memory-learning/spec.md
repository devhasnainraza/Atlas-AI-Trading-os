# Spec 07 — Memory, Journal & Learning

**Project**: Atlas AI Trading OS  
**Status**: Ratified | **Version**: 1.0.0 | **Date**: 2026-09-21  
**Target Path**: `specs/spec-07-memory-learning/`  
**Constitutional Compliance**: Core Principles VII, VIII, X, XI Verified  

---

## 1. Vision & Goals

### 1.1 System Vision
Spec 07 establishes the cognitive memory and developmental intelligence of Atlas AI Trading OS. Trading mastery is rarely limited by market knowledge; it is almost universally destroyed by human psychological pitfalls, lack of discipline, and failure to learn from past errors. Spec 07 endows the AI OS with continuous episodic memory, an automated multi-media Trade Journal, and a personalized AI Trading Coach that diagnoses user cognitive biases (FOMO, revenge trading, loss aversion) and guides the trader toward disciplined profitability.

### 1.2 Core Business & Technical Goals
- **Personalized Long-Term Memory (LTM)**: Secure, per-user partitioned memory store capturing trading style, preferred currency/crypto pairs, risk tolerance thresholds, active time zones, and personal trading rules.
- **Automated Multimedia Trade Journaling**: Zero-effort logging: the moment a trade closes, the Journal Agent captures chart screenshots, market context, entry/exit ticks, technical indicators, and tags the trade with initial hypotheses.
- **Psychological & Emotional State Tracking**: Capture trader emotional sentiment (e.g. "Overconfident", "Frustrated", "Disciplined", "FOMO") at trade entry and exit to detect negative psychological loops.
- **Proactive Weekly AI Coaching Diagnostics**: Analytical synthesis generated weekly highlighting behavioral patterns (e.g. "Your win rate drops from 68% to 22% when trading after 20:00 UTC", or "You tend to widen stop-losses on losing EUR/USD trades").
- **Strict Privacy by Design (Principle VIII)**: All memory embeddings and journal notes belong exclusively to the user. User data is never used to train cross-user public models and can be permanently deleted upon request.

---

## 2. Functional Requirements

- **FR-001**: The platform MUST maintain a per-user `MemoryStore` partitioned by `(user_id, scope, memory_type)` with semantic search powered by `pgvector`.
- **FR-002**: The Memory Agent MUST maintain an evolving `UserProfileMemory` containing:
  - Preferred assets and asset classes
  - Average risk tolerance and position hold times
  - Identified psychological blind spots
  - Historical win/loss distributions by market session (Asian, London, New York).
- **FR-003**: The Journal Agent MUST automatically generate a comprehensive `TradeJournalEntry` whenever a position is closed at a venue:
  - Entry and exit timestamps, prices, and net PnL (in currency and R-multiples).
  - Snapshot of the TradingView chart with plotted entry, exit, SL, and TP markers.
  - Multi-timeframe indicator values at time of entry (RSI, ATR, Trend).
  - AI thesis summary vs. actual price development post-mortem.
- **FR-004**: The journal MUST provide an interactive interface for the trader to log subjective notes, emotional tags (`CALM`, `FOMO`, `REVENGE`, `GREED`, `FEAR`), and self-rating (1–5 stars).
- **FR-005**: The Learning Agent MUST run background behavioral diagnostics analyzing trade sequences:
  - `Revenge Trading Detector`: Flags rapid order submission (< 5 minutes) following a stop-out loss with increased position sizing.
  - `Overtrading Detector`: Flags when daily trade frequency exceeds 2 standard deviations above user average.
  - `Holding Losers / Cutting Winners`: Compares average hold time of winning trades vs. losing trades.
- **FR-006**: The platform MUST generate a **Weekly AI Coaching Report** delivered every Sunday evening, summarizing:
  - Weekly Net PnL, Profit Factor, Win Rate, and Total Fees/Slippage.
  - Top 3 disciplined decisions made during the week.
  - Key cognitive bias warning with actionable behavioral corrective steps.
- **FR-007**: Privacy erasure MUST support the complete deletion of a user's memory vector partition and journal history within 24 hours of request (`atlas.privacy.user_deleted`).

---

## 3. Non-Functional Requirements

- **NFR-001 (Automated Journaling Speed)**: Trade journal entries and chart snapshot captures MUST be generated and available in the UI within 3 seconds of position close.
- **NFR-002 (Semantic Memory Retrieval)**: Contextual memory lookups by agents during active analysis MUST complete in < 20ms at p95.
- **NFR-003 (Storage Scalability)**: The trade journal database MUST scale to millions of historical entries with sub-second paginated queries.
- **NFR-004 (Chart Image Optimization)**: Trade entry chart snapshots MUST be stored in WebP format with image sizes capped at 250KB.

---

## 4. User Stories

### US-001: Automatic Trade Journal Capture (Priority: P1)
- **Given** a trader closing an open short position on `EUR/USD` with a +$420 profit,
- **When** the fill confirmation arrives from MetaTrader 5,
- **Then** the Journal Agent creates a complete journal card with the chart snapshot, calculated R-multiple (2.1R), indicator context, and opens a prompt for optional emotion tagging.

### US-002: Learning Agent Detects Revenge Trading Pattern (Priority: P1)
- **Given** a trader taking a loss and immediately opening an oversized position within 90 seconds,
- **When** the order is initiated,
- **Then** the Learning Agent alerts the Manager Agent, which surfaces an advisory modal: "Coaching Warning: This matches your historical Revenge Trading pattern, which has a 24% win rate. Would you like a 15-minute cooldown?"

### US-003: Weekly AI Coaching Review Unveils Optimal Trading Hours (Priority: P2)
- **Given** a trader reviewing their Sunday coaching report,
- **When** they inspect the session breakdown widget,
- **Then** the AI Coach shows data proving they are profitable during the London Open (+14.2% over 30 days) but consistently lose money during the late NY session (-8.4%), recommending restricting automated trading to London hours.

---

## 5. Agent Architecture

Spec 07 coordinates the **Memory Agent**, **Journal Agent**, and **Learning Agent**:

```text
+-------------------------------------------------------------------------+
|                       Memory & Learning Subsystem                       |
|                                                                         |
|  +--------------------+   +---------------------+   +----------------+  |
|  |    Memory Agent    |   |    Journal Agent    |   | Learning Agent |  |
|  | - Episodic RAG     |   | - Auto-capture      |   | - Bias detector|  |
|  | - Profile store    |   | - Chart snapshot    |   | - Weekly coach |  |
|  +---------+----------+   +----------+----------+   +--------+-------+  |
|            |                         |                       |          |
|            +-------------------------+-----------------------+          |
|                                      |                                  |
|                         +------------v------------+                     |
|                         |    Behavioral Pattern   |                     |
|                         |      Analysis Engine    |                     |
|                         +------------+------------+                     |
|                                      |                                  |
|           +--------------------------+-------------------------+        |
|           |                                                    |        |
|  +--------v---------+                                 +--------v-----+  |
|  | User-Scoped      |                                 | Trade        |  |
|  | pgvector Memory  |                                 | Journal DB   |  |
|  +------------------+                                 +--------------+  |
+-------------------------------------------------------------------------+
```

---

## 6. State Design

### 6.1 Trade Journal Entry Schema
```python
@dataclass(frozen=True)
class TradeJournalRecord:
    journal_id: str
    user_id: str
    order_id: str
    symbol: str
    side: str
    entry_price: Decimal
    exit_price: Decimal
    entry_time: datetime
    exit_time: datetime
    net_pnl: Decimal
    r_multiple: Decimal
    chart_image_url: str
    market_regime: str
    user_notes: str | None
    emotional_tags: tuple[str, ...]
    ai_post_mortem: str
```

### 6.2 Cognitive Bias Profile Schema
```python
@dataclass
class CognitiveBiasProfile:
    user_id: str
    fomo_score: Decimal          # 0.00 to 1.00
    revenge_trading_score: Decimal
    loss_aversion_score: Decimal
    discipline_rating: Decimal
    top_mistake_triggers: list[str]
    last_updated: datetime
```

---

## 7. LangGraph Workflow Integration

Memory and coaching context are injected dynamically during graph initialization:

```text
[User Initiates Analysis Session]
                 |
                 v
+--------------------------------+
| Memory Agent Retrieval Node    |  Fetches user's:
+----------------+---------------+  - Preferred risk tolerance
                 |                  - Active behavioral warnings
                 v                  - Relevant past trade outcomes
+--------------------------------+
| Context-Enriched Planning Node |  Manager Agent tailors strategy recommendations
+--------------------------------+  to user's documented strengths
```

---

## 8. Tool Specifications

### 8.1 Query User Memory Tool (`tool_memory_retrieve`)
- **Description**: Performs semantic search across the trader's historical memories and trading rules.
- **Input Schema**:
  ```json
  {
    "type": "object",
    "required": ["user_id", "query"],
    "properties": {
      "user_id": { "type": "string" },
      "query": { "type": "string" },
      "limit": { "type": "integer", "default": 3 }
    }
  }
  ```

### 8.2 Generate Coaching Diagnostic Tool (`tool_generate_coaching_report`)
- **Description**: Compiles statistical performance and behavioral metrics for a specified date range.
- **Input Schema**:
  ```json
  {
    "type": "object",
    "required": ["user_id", "start_date", "end_date"],
    "properties": {
      "user_id": { "type": "string" },
      "start_date": { "type": "string", "format": "date" },
      "end_date": { "type": "string", "format": "date" }
    }
  }
  ```

---

## 9. API Specifications

### 9.1 Journal & Learning Endpoints
- **`GET /api/v1/journal/entries`**: Returns paginated list of trade journal records with filters (`symbol`, `emotion`, `outcome`).
- **`POST /api/v1/journal/entries/{id}/annotate`**: Adds user emotional tags, self-review notes, and ratings.
- **`GET /api/v1/journal/analytics/biases`**: Returns trader psychological scores and detected blind spots.
- **`GET /api/v1/learning/coaching-reports/latest`**: Retrieves the latest Weekly AI Coaching diagnostic.

---

## 10. Database Schema

### 10.1 Trade Journal Table (`journal_entries`)
```sql
CREATE TABLE journal_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    order_id UUID NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    side VARCHAR(16) NOT NULL,
    entry_price NUMERIC(28, 10) NOT NULL,
    exit_price NUMERIC(28, 10) NOT NULL,
    net_pnl NUMERIC(28, 10) NOT NULL,
    r_multiple NUMERIC(6, 2) NOT NULL,
    chart_image_url VARCHAR(512),
    technical_indicators JSONB NOT NULL DEFAULT '{}'::jsonb,
    ai_post_mortem TEXT NOT NULL,
    user_notes TEXT,
    emotional_tags VARCHAR(32)[] NOT NULL DEFAULT '{}',
    user_rating INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_journal_user_time ON journal_entries (user_id, created_at DESC);
```

### 10.2 User Cognitive Memory Table (`memory_user_embeddings`)
```sql
CREATE TABLE memory_user_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    scope VARCHAR(64) NOT NULL,        -- STRATEGY | BEHAVIOR | GOALS | RULES
    memory_text TEXT NOT NULL,
    embedding vector(1536) NOT NULL,
    importance_weight NUMERIC(3, 2) NOT NULL DEFAULT 1.00,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_user_memory_hnsw 
ON memory_user_embeddings 
USING hnsw (embedding vector_cosine_ops);
```

---

## 11. Frontend Screens & Components

### 11.1 Multimedia Trade Journal
- Grid and table view of all historical trades with thumbnail chart previews, R-multiple badges (e.g. `+2.4R` Green, `-1.0R` Red), and emotion tags.
- Detailed Drawer: Full-size interactive chart, entry/exit price ladder, AI post-mortem debrief, and emotion selector pills.

### 11.2 Weekly AI Coach Dossier
- High-level executive score card: "Discipline Score: 86/100", "Profit Factor: 1.92".
- Behavioral Heatmap: Win rate by hour of day and day of week.
- Coaching Advice Card: Actionable conversational advice with concrete steps to eliminate detected leaks.

---

## 12. Security Requirements

- **SEC-001 (Strict User Partitioning)**: Memory queries MUST always include `WHERE user_id = :current_user` in both SQL and vector distance filters; cross-user leakage is prevented at database layer.
- **SEC-002 (Presigned Image Uploads)**: Chart snapshots are uploaded to private S3/MinIO buckets using short-lived (15-min) presigned URLs.
- **SEC-003 (GDPR Right to Be Forgotten)**: User deletion immediately triggers cascade drop of journal entries and vector embeddings.

---

## 13. Testing Strategy

- **Revenge Trading Detector Unit Tests**: Provide mock trade histories with varied timing and lot sizes to verify accurate detection threshold triggering.
- **Memory Vector Search Isolation Test**: Verify that a vector query issued under User A cannot return memories belonging to User B even with 100% semantic similarity.
- **Chart Snapshot Generator Integration Test**: Verify headless browser captures chart canvas and saves valid WebP image in < 2 seconds.

---

## 14. Deployment Plan

- **Object Storage**: S3-compatible storage (MinIO locally, AWS S3 in production) configured with lifecycle policies archiving images older than 1 year to Glacier.
- **Coaching Job Scheduler**: Celery Beat scheduled task executing weekly coaching synthesis on Sundays at 21:00 UTC.

---

## 15. Future Enhancements

- **Biometric Emotion Sync**: Integration with smartwatches (Apple Watch, Whoop) to correlate heart rate variability (HRV) and physiological stress with trade execution errors.
- **Voice Journaling**: Voice note transcription allowing traders to dictate their thoughts immediately after exiting a trade.
