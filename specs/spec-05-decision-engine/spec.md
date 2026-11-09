# Spec 05 — Decision Engine & Risk Management

**Project**: Atlas AI Trading OS  
**Status**: Ratified | **Version**: 1.0.0 | **Date**: 2026-09-21  
**Target Path**: `specs/spec-05-decision-engine/`  
**Constitutional Compliance**: Core Principles I, III, IV, V, VI, IX Verified  

---

## 1. Vision & Goals

### 1.1 System Vision
Spec 05 establishes the cognitive decision core of Atlas AI Trading OS. In financial markets, single-agent models or naive LLM trading prompts are susceptible to severe hallucination, emotional bias, and catastrophic overfitting. Spec 05 replaces uncalibrated generation with an adversarial dialectic decision pipeline: research is submitted to an adversarial AI Debate (Bull Agent vs. Bear Agent), scrutinized through rigorous risk checks, evaluated for calibrated Bayesian confidence, and formatted into an explainable, transparent proposal before human approval.

### 1.2 Core Business & Technical Goals
- **Adversarial AI Debate Pipeline**: Trade hypotheses are challenged through structured adversarial debate where dedicated Bull and Bear advocates cross-examine evidence, identify hidden tail risks, and present opposing thesis scenarios.
- **Calibrated Bayesian Confidence Scoring**: Output confidence scores (0.00% to 100.00%) derived from mathematical weighting of multi-agent agreement, signal convergence, volatility regime, and historical backtest hit rates.
- **Uncompromised Risk Primacy (Principle VI)**: Constitutional mandate: risk management rules strictly override profit opportunities. If a proposed trade violates position limits, drawdown caps, or correlation ceilings, the Risk Engine executes an unconditional hard veto.
- **Transparent 4-Part Output Contract (Principle III)**: Every recommendation delivered to the trader or execution gateway MUST contain:
  1. Confidence Score (%)
  2. Supporting Evidence Array
  3. Risk Assessment & Invalidation Level
  4. Alternative Scenarios (What happens if the hypothesis fails)
- **Deterministic Explainability**: Complete chain-of-custody recording every data point, technical indicator, debate argument, and risk calculation that informed the final decision.

---

## 2. Functional Requirements

- **FR-001**: The decision engine MUST execute the structured 8-stage decision pipeline:
  `Research` -> `Analyze` -> `Debate` -> `Risk Check` -> `Confidence Calibration` -> `Recommendation Synthesis` -> `Human Approval Gate` -> `Execution Hand-off`.
- **FR-002**: The Debate Stage MUST instantiate an adversarial peer review:
  - `Bull Advocate`: Maximizes upside thesis using technical breakouts, macro tailwinds, and bullish on-chain inflows.
  - `Bear Advocate`: Challenges the thesis using structural resistance, macro headwinds, liquidity traps, and historical failure analogues.
  - `Synthesis Arbitrator`: Evaluates the strength of both arguments, identifies logical fallacies, and produces a balanced thesis.
- **FR-003**: The Risk Engine MUST calculate real-time portfolio risk parameters prior to proposal formulation:
  - Maximum account risk per trade (default 1.0% to 2.0% equity).
  - Portfolio heat and total open risk margin.
  - Cross-asset correlation (blocking new trades that exacerbate directional concentration).
  - Proximity to high-impact economic releases (embargoing trades within 30 minutes of CPI/NFP).
- **FR-004**: Confidence scores MUST be calculated deterministically combining:
  - Indicator confluence (30% weight)
  - Multi-agent consensus (25% weight)
  - Debate outcome balance (20% weight)
  - Market regime stability (15% weight)
  - On-chain / sentiment confirmation (10% weight)
- **FR-005**: If the calibrated confidence score falls below the configurable threshold (default 65.00%), the decision engine MUST recommend a "NO_TRADE / WAIT" verdict rather than forcing action (Principle IX: Fail-Safe).
- **FR-006**: Every approved recommendation MUST explicitly calculate and state:
  - Exact Entry Range (Decimal)
  - Hard Stop-Loss Price (based on structural market invalidation)
  - Multi-Target Take-Profit levels (TP1, TP2, TP3) with risk-to-reward ratios (minimum 1:1.5)
  - Invalidation criteria ("If price breaks below $X before reaching $Y, thesis is void").
- **FR-007**: The decision engine MUST generate plain-language, jargon-free explanations suitable for retail traders, avoiding opaque black-box assertions.

---

## 3. Non-Functional Requirements

- **NFR-001 (Debate Execution Latency)**: The full adversarial debate and consensus synthesis pipeline MUST complete in < 6 seconds using streaming fast-reasoning LLMs.
- **NFR-002 (Risk Gate Evaluation Latency)**: Pre-trade mathematical risk check MUST execute in < 5ms in pure Python/C-extensions without external network dependencies.
- **NFR-003 (Zero Hallucination Tolerances)**: All prices, support/resistance levels, and indicator values cited in agent debates MUST be verified against active database state; hallucinated price levels fail the synthesis gate.
- **NFR-004 (Explainability Storage)**: Complete debate transcripts, confidence breakdowns, and risk matrices MUST be stored in JSONB format with immediate queryability.

---

## 4. User Stories

### US-001: Adversarial Debate Exposes Hidden Resistance Level (Priority: P1)
- **Given** the Technical Agent proposing an aggressive long breakout on `ETH/USDT`,
- **When** the proposal enters the Debate stage,
- **Then** the Bear Agent surfaces massive sell-side order book depth and CME futures open interest rollover scheduled in 2 hours, prompting the Synthesis Arbitrator to downgrade confidence from 82% to 54%, recommending waiting for post-rollover confirmation.

### US-002: Hard Risk Override Halts High-Confidence Trade (Priority: P1)
- **Given** an 88% confidence signal on `GBP/USD` during the London open,
- **When** the proposal reaches the Risk Check node and the engine detects that the user's account has already suffered 2.8% loss today (exceeding the 3.0% daily circuit breaker limit),
- **Then** the Risk Engine issues an absolute veto, halts the pipeline, and logs an explainable risk notification: "Trade rejected: Daily loss limit reached."

### US-003: Transparent Trade Proposal Delivery (Priority: P1)
- **Given** a validated trade opportunity passing all debate and risk filters,
- **When** the recommendation is published to the user,
- **Then** the UI displays an actionable card detailing Confidence (78%), Evidence bullets (ICT liquidity sweep + bullish RSI divergence), Risk score (1.2% equity risk, R:R 1:2.4), and Invalidation Level.

---

## 5. Agent Architecture

The Decision Engine coordinates the dialectic synthesis between specialized agents:

```text
+-------------------------------------------------------------------------+
|                         Decision & Debate Engine                        |
|                                                                         |
|  +--------------------+                    +-------------------------+  |
|  |    Bull Advocate   |                    |      Bear Advocate      |  |
|  | - Upside momentum  | <----------------> | - Downside vulnerability|  |
|  | - Support levels   |   Dialectic Debate | - Macro resistance      |  |
|  +---------+----------+                    +------------+------------+  |
|            |                                            |               |
|            +-------------------+------------------------+               |
|                                |                                        |
|                   +------------v------------+                           |
|                   |   Synthesis Arbitrator  |                           |
|                   |  - Fallacy check        |                           |
|                   |  - Thesis calibration   |                           |
|                   +------------+------------+                           |
|                                |                                        |
|                   +------------v------------+                           |
|                   |  Pre-Trade Risk Engine  |                           |
|                   | (Constitutional Hard Veto)|                         |
|                   +------------+------------+                           |
|                                |                                        |
|                   +------------v------------+                           |
|                   | Confidence Scoring Node |                           |
|                   | (Bayesian Model 0-100%) |                           |
|                   +-------------------------+                           |
+-------------------------------------------------------------------------+
```

---

## 6. State Design

### 6.1 Decision State Schema (`DecisionEngineState`)
```python
class DecisionEngineState(TypedDict):
    trade_id: str
    symbol: str
    proposed_side: str  # BUY | SELL
    timeframe: str
    
    # Input Evidence
    technical_signals: list[dict[str, Any]]
    macro_context: dict[str, Any]
    sentiment_metrics: dict[str, Any]
    
    # Debate Transcripts
    bull_arguments: list[str]
    bear_counter_arguments: list[str]
    arbitrator_synthesis: str
    
    # Risk Verdict
    risk_approved: bool
    risk_violations: list[str]
    calculated_position_size: Decimal
    stop_loss_price: Decimal
    take_profit_levels: list[Decimal]
    risk_reward_ratio: Decimal
    
    # Final Proposal
    confidence_score: Decimal
    recommendation_verdict: str  # STRONG_BUY | BUY | WAIT | SELL | STRONG_SELL
    evidence_summary: list[str]
    tail_risks: list[str]
    alternative_scenarios: list[str]
    human_approval_required: bool
```

---

## 7. LangGraph Workflow Integration

The complete Decision Graph with unbypassable risk and human validation:

```text
                  +-----------------------+
                  |  Candidate Signal In  |
                  +-----------+-----------+
                              |
                              v
                  +-----------------------+
                  |  Bull vs. Bear Debate |
                  |         Node          |
                  +-----------+-----------+
                              |
                              v
                  +-----------------------+
                  |  Synthesis Arbitrator |
                  +-----------+-----------+
                              |
                              v
                  +-----------------------+
                  | Pre-Trade Risk Engine |
                  +-----------+-----------+
                              |
               +--------------+--------------+
               |                             |
      (Fails Risk Rules)            (Passes Risk Rules)
               |                             |
               v                             v
        +--------------+           +--------------------+
        |  Log Veto &  |           | Calibrate Bayesian |
        |  Notify User |           |     Confidence     |
        +--------------+           +---------+----------+
                                             |
                              +--------------+--------------+
                              |                             |
                     (Confidence < 65%)            (Confidence >= 65%)
                              |                             |
                              v                             v
                       +--------------+           +--------------------+
                       | Output: WAIT |           | Human-in-the-Loop  | <-- interrupt_before
                       | / NO ACTION  |           | Approval Interrupt |
                       +--------------+           +---------+----------+
                                                            |
                                                   (Trader Approves)
                                                            |
                                                            v
                                                  +--------------------+
                                                  | Execution Pipeline |
                                                  +--------------------+
```

---

## 8. Tool Specifications

### 8.1 Pre-Trade Risk Calculator Tool (`tool_risk_calculate_exposure`)
- **Description**: Calculates exact position sizing based on risk percentage and stop-loss distance.
- **Input Schema**:
  ```json
  {
    "type": "object",
    "required": ["account_id", "entry_price", "stop_loss_price", "risk_percent"],
    "properties": {
      "account_id": { "type": "string" },
      "entry_price": { "type": "string" },
      "stop_loss_price": { "type": "string" },
      "risk_percent": { "type": "string", "default": "1.0" }
    }
  }
  ```
- **Output Schema**: Returns `{ "lot_size": "0.45", "risk_amount_usd": "250.00", "max_loss": "250.00", "is_within_limits": true }`.

### 8.2 Historical Setup Evaluator Tool (`tool_evaluate_setup_history`)
- **Description**: Evaluates win rate and expectancy of current technical pattern over past 5 years.
- **Input Schema**:
  ```json
  {
    "type": "object",
    "required": ["pattern_type", "symbol", "timeframe"],
    "properties": {
      "pattern_type": { "type": "string", "enum": ["FVG_RETEST", "LIQUIDITY_SWEEP", "BULL_FLAG", "WYCKOFF_SPRING"] },
      "symbol": { "type": "string" },
      "timeframe": { "type": "string" }
    }
  }
  ```

---

## 9. API Specifications

### 9.1 Decision Engine REST Endpoints
- **`POST /api/v1/decision/evaluate`**: Submits a market setup for ad-hoc multi-agent debate and evaluation.
- **`GET /api/v1/decision/proposals/pending`**: Returns all open trade proposals awaiting human approval.
- **`POST /api/v1/decision/proposals/{id}/approve`**: Submits human cryptographic approval to dispatch the trade.
- **`POST /api/v1/decision/proposals/{id}/reject`**: Rejects proposal and records user rationale for Learning Agent training.

---

## 10. Database Schema

### 10.1 Trade Proposals Table (`decision_proposals`)
```sql
CREATE TABLE decision_proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    direction VARCHAR(8) NOT NULL,
    confidence_score NUMERIC(5, 2) NOT NULL, -- e.g. 84.50
    entry_range_min NUMERIC(28, 10) NOT NULL,
    entry_range_max NUMERIC(28, 10) NOT NULL,
    stop_loss NUMERIC(28, 10) NOT NULL,
    take_profit_levels NUMERIC(28, 10)[] NOT NULL,
    risk_reward_ratio NUMERIC(6, 2) NOT NULL,
    risk_amount_usd NUMERIC(28, 10) NOT NULL,
    evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
    risks JSONB NOT NULL DEFAULT '[]'::jsonb,
    alternative_scenarios JSONB NOT NULL DEFAULT '[]'::jsonb,
    debate_transcript JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING_APPROVAL',
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_proposals_status ON decision_proposals (user_id, status);
```

---

## 11. Frontend Screens & Components

### 11.1 Dialectic Debate Visualizer
- Split-screen debate view: Bull case (Emerald card) vs. Bear case (Crimson card) showing key arguments and confidence weights.
- Center gauge displaying the Synthesis Arbitrator's consensus conviction rating.

### 11.2 Interactive Trade Proposal Card
- **Primary Metrics Header**: Direction badge (LONG / SHORT), Symbol, Confidence Meter (e.g. 79%), Risk-to-Reward (1:2.8).
- **Execution Blueprint**: Clearly formatted Entry, SL, and TP targets on a mini TradingView chart preview.
- **Explainability Accordion**: Expandable sections for "Why this trade?", "Critical Failure Conditions", and "Risk Profile".
- **Action Buttons**: Large high-contrast "Confirm Execution" (with countdown timer) and "Pass / Ignore".

---

## 12. Security Requirements

- **SEC-001 (Immutable Proposal Ledger)**: Every generated proposal is assigned a cryptographic SHA-256 hash preventing modification between generation and execution.
- **SEC-002 (TTL Expiration Guard)**: Trade proposals expire automatically after 10 minutes; expired proposals cannot be executed even if approved by user.
- **SEC-003 (Strict Risk Independence)**: Risk calculation logic is decoupled from LLM inference; prompts cannot alter risk limit rules.

---

## 13. Testing Strategy

- **Debate Consistency Fuzzing**: Verify that the debate synthesizer never approves a trade where the Bear Advocate identified a breach of an explicit invalidation level.
- **Risk Override Invariant Testing**: 100% test coverage ensuring that any risk violation immediately returns a hard veto, regardless of confidence score.
- **Bayesian Confidence Calibration Test**: Backtest calibration across 10,000 synthetic market setups, verifying that high-confidence bins correlate with positive expectancy.

---

## 14. Deployment Plan

- **Inference Optimization**: Multi-threaded async worker pools calling batched LLM APIs with timeout cutoffs at 4 seconds.
- **Postgres Partitioning**: Proposals table partitioned monthly to maintain sub-millisecond query performance over millions of historical evaluations.

---

## 15. Future Enhancements

- **Reinforcement Learning from Trader Feedback (RLTF)**: Continuously adjust agent debate weights based on user decisions and final trade profitability.
- **Multi-Model Consensus Ensembles**: Run debate models across differing foundation models (e.g. Claude 3.5 Sonnet vs. GPT-4o vs. DeepSeek R1) to eliminate single-vendor architectural bias.
