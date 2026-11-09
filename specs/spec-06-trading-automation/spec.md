# Spec 06 — Trading Automation

**Project**: Atlas AI Trading OS  
**Status**: Ratified | **Version**: 1.0.0 | **Date**: 2026-09-21  
**Target Path**: `specs/spec-06-trading-automation/`  
**Constitutional Compliance**: Core Principles I, II, VI, IX, X Verified  

---

## 1. Vision & Goals

### 1.1 System Vision
Spec 06 defines the trading automation engine of Atlas AI Trading OS. While human judgment remains paramount (Principle I), traders require automated guardrails and execution precision to navigate 24/7 global markets. Spec 06 provides three distinct operational tiers—Manual, Semi-Automatic, and Fully Autonomous Mandates—backed by smart position management, dynamic trailing stops, and uncompromised capital protection circuit breakers.

### 1.2 Core Business & Technical Goals
- **Three Tiered Automation Modes**:
  1. *Manual*: AI provides research and alerts; human creates and submits all orders.
  2. *Semi-Automatic (Default)*: AI formulates complete trade proposals; human must explicitly click to approve.
  3. *Fully Automatic (Scoped Mandates)*: AI executes autonomously strictly within user-defined capital, symbol, and daily drawdown constraints.
- **Smart Adaptive Exit Management**: Dynamic ATR-based Stop Losses, Multi-Target Take Profits, automatic Breakeven adjustment after reaching TP1, and volatility-adjusted Trailing Stops.
- **AI-Driven Trade Exit Monitoring**: Continuous surveillance of open positions by the Market and Technical Agents; if market conditions deteriorate or opposite signals emerge, AI issues an early exit or partial close alert.
- **Rigorous Capital Protection Circuit Breakers**: Non-negotiable protective gates that automatically suspend trading upon reaching daily max loss limits, consecutive losing streaks, or unexpected high-impact volatility.
- **Temporal & Event Embargoes**: Automated lockouts preventing trade entry during low-liquidity market rollouts, national banking holidays, and within specified time windows surrounding major economic news releases.

---

## 2. Functional Requirements

- **FR-001**: The platform MUST enforce three distinct execution modes selectable per account or trading pair: `MANUAL`, `SEMI_AUTOMATIC`, and `FULLY_AUTOMATIC`.
- **FR-002**: In `FULLY_AUTOMATIC` mode, trades MUST be governed by an explicit `AutomationMandate` defining:
  - Allowed symbols (e.g. `["EURUSD", "BTCUSDT"]`)
  - Maximum active positions (e.g. max 3 concurrent)
  - Maximum capital allocation per trade (e.g. max 1.5% equity risk)
  - Mandatory hard stop-loss requirement on every single entry
  - Mandate expiration date and maximum drawdown threshold.
- **FR-003**: The Smart Stop Loss engine MUST support structural stop placement (swing highs/lows, order blocks) and dynamic volatility-based stops (Average True Range multiples).
- **FR-004**: The Smart Take Profit engine MUST support multi-stage scaling:
  - `TP1`: Closes 50% position size; triggers automated adjustment of Stop Loss to Breakeven (entry price + spread).
  - `TP2`: Closes 25% position size; activates trailing stop.
  - `TP3`: Runner (remaining 25%) managed by dynamic trailing stop.
- **FR-005**: The Trailing Stop engine MUST adjust stops on the venue or via local synthetic orders based on price milestones, moving averages, or Chandelier Exits.
- **FR-006**: The Trade Exit AI MUST continuously evaluate open positions against real-time order flow and breaking news; upon detecting a thesis invalidation, it executes an immediate market exit or partial hedge.
- **FR-007**: The platform MUST implement multi-level Circuit Breakers:
  - `Daily Drawdown Breaker`: If realized + unrealized loss hits the daily limit (e.g. 3%), halt all automated trading until next daily session.
  - `Consecutive Loss Breaker`: If 3 consecutive losses occur, require mandatory 2-hour cooldown.
  - `Exchange Latency Breaker`: If venue roundtrip latency exceeds 1,500ms, pause order routing.
- **FR-008**: The platform MUST enforce Trading Hours schedules (e.g. London Session `08:00–16:30 UTC`, New York Session `13:30–20:00 UTC`), automatically barring entries outside authorized market hours.
- **FR-009**: The News Protection engine MUST enforce an automated blackout window (default 15 minutes before and 15 minutes after high-impact economic releases).

---

## 3. Non-Functional Requirements

- **NFR-001 (Automated Execution Latency)**: For `FULLY_AUTOMATIC` mandates, latency from signal generation to venue dispatch MUST NOT exceed 35ms at p95.
- **NFR-002 (Trailing Stop Recalculation)**: Trailing stop price updates MUST be evaluated within 100ms of each price tick.
- **NFR-003 (Circuit Breaker Reliability)**: Daily loss limit checks MUST be evaluated synchronously prior to every order intent; circuit breaker triggers MUST NEVER be skipped or delayed.
- **NFR-004 (Emergency Halt Propagation)**: Clicking "Emergency Stop" MUST trigger API cancellation requests to venues within 200ms.

---

## 4. User Stories

### US-001: Automatic Breakeven & Multi-Target Profit Taking (Priority: P1)
- **Given** an open long position on `BTC/USDT` entering in Semi-Automatic mode,
- **When** price advances to TP1 (+2.5%),
- **Then** the automation engine automatically closes 50% of the position, moves the Stop Loss to entry price, and reports the realized profit to the trader.

### US-002: News Protection Embargoes Pre-CPI Trading (Priority: P1)
- **Given** an automated strategy running on `EUR/USD` at 12:20 UTC,
- **When** the US CPI release is scheduled for 12:30 UTC,
- **Then** the automation engine rejects any new trade signals, issues an alert stating "Trading locked: US CPI Release in 10 minutes", and tightens stops on existing positions.

### US-003: Daily Drawdown Circuit Breaker Prevents Tilt (Priority: P1)
- **Given** an aggressive automated mandate sustaining two consecutive losses totaling 3.1% loss on the day,
- **When** the user's daily loss limit is configured at 3.0%,
- **Then** the platform trips the Daily Circuit Breaker, disarms all automated trading agents, cancels remaining pending orders, and locks automated execution until tomorrow's 00:00 UTC session reset.

---

## 5. Agent Architecture

Trading Automation operates through tight coordination between the **Execution Agent**, **Risk Agent**, and **Market Monitoring Daemon**:

```text
+-------------------------------------------------------------------------+
|                       Trading Automation Engine                         |
|                                                                         |
|  +--------------------+                    +-------------------------+  |
|  | Automation Mandates|                    |    Circuit Breaker Hub  |  |
|  | - Scoped symbol list|                    |    - Daily loss limit   |  |
|  | - Capital caps     |                    |    - News embargoes     |  |
|  +---------+----------+                    |    - Session hours      |  |
|            |                               +------------+------------+  |
|            v                                            |               |
|  +------------------------------------------------------+------------+  |
|  |                   Automation Supervisor Daemon                    |  |
|  |         (Evaluates Mandates -> Checks Breakers -> Routes Orders)  |  |
|  +--------------------------------------+----------------------------+  |
|                                         |                               |
|        +--------------------------------+-----------------------+       |
|        |                                |                       |       |
|  +-----v--------------+      +----------v-----------+    +------v-----+ |
|  | Smart SL/TP Engine |      | Trailing Stop Engine |    | Trade Exit | |
|  | - ATR Multiples    |      | - Chandelier / Step  |    | AI Monitor | |
|  +--------------------+      +----------------------+    +------------+ |
+-------------------------------------------------------------------------+
```

---

## 6. State Design

### 6.1 Automation Mandate Schema
```python
@dataclass(frozen=True)
class AutomationMandate:
    mandate_id: str
    user_id: str
    account_id: str
    mode: str  # MANUAL | SEMI_AUTOMATIC | FULLY_AUTOMATIC
    allowed_symbols: tuple[str, ...]
    max_capital_risk_pct: Decimal
    max_open_positions: int
    daily_loss_limit_usd: Decimal
    news_protection_enabled: bool
    session_restrictions: tuple[str, ...]  # e.g. ("LONDON", "NEW_YORK")
    is_active: bool
    expires_at: datetime
```

### 6.2 Active Position Guard State
```python
@dataclass
class PositionGuardState:
    position_id: str
    symbol: str
    entry_price: Decimal
    current_stop_loss: Decimal
    breakeven_reached: bool
    tp1_filled: bool
    tp2_filled: bool
    trailing_active: bool
    highest_price_seen: Decimal
```

---

## 7. LangGraph Workflow Integration

In automated execution workflows, the decision graph branches based on the active mandate mode:

```text
[High-Confidence Recommendation Synthesized]
                     |
                     v
+------------------------------------+
| Check Circuit Breakers & News Lock |
+--------------------+---------------+
                     |
         +-----------+-----------+
         |                       |
(Breaker Tripped / News Lock)  (Checks Clear)
         |                       |
         v                       v
  [Halt Execution &]  +--------------------+
  [Notify Trader   ]  | Mode Determination |
                      +---------+----------+
                                |
             +------------------+------------------+
             |                                     |
    (SEMI_AUTOMATIC)                       (FULLY_AUTOMATIC)
             |                                     |
             v                                     v
+--------------------------+             +--------------------+
| Human Approval Interrupt |             | Verify Mandate Caps|
+------------+-------------+             +---------+----------+
             |                                     |
       (User Clicks)                         (Caps Valid)
             |                                     |
             +------------------+------------------+
                                |
                                v
                     +--------------------+
                     |  Venue Dispatch &  |
                     |  Attach SL/TP/TS   |
                     +--------------------+
```

---

## 8. Tool Specifications

### 8.1 Configure Automation Mandate Tool (`tool_configure_mandate`)
- **Description**: Sets up or modifies a bounded autonomous trading mandate.
- **Input Schema**:
  ```json
  {
    "type": "object",
    "required": ["account_id", "mode", "allowed_symbols", "max_risk_pct", "daily_loss_limit"],
    "properties": {
      "account_id": { "type": "string" },
      "mode": { "type": "string", "enum": ["MANUAL", "SEMI_AUTOMATIC", "FULLY_AUTOMATIC"] },
      "allowed_symbols": { "type": "array", "items": { "type": "string" } },
      "max_risk_pct": { "type": "string", "default": "1.0" },
      "daily_loss_limit": { "type": "string" }
    }
  }
  ```

### 8.2 Emergency Flatten All Positions Tool (`tool_emergency_flatten`)
- **Description**: Immediately closes all active positions at market price and pauses trading.
- **Input Schema**:
  ```json
  {
    "type": "object",
    "required": ["confirmation_token"],
    "properties": {
      "confirmation_token": { "type": "string" },
      "reason": { "type": "string" }
    }
  }
  ```

---

## 9. API Specifications

### 9.1 Automation Endpoints
- **`GET /api/v1/automation/mandates`**: Lists active mandates and risk settings.
- **`POST /api/v1/automation/mandates`**: Provisions or updates an automation mandate.
- **`POST /api/v1/automation/circuit-breakers/reset`**: Manually resets a tripped circuit breaker (requires admin/owner role).
- **`POST /api/v1/automation/emergency-stop`**: Global emergency stop halting all trading.

---

## 10. Database Schema

### 10.1 Automation Mandates Table (`automation_mandates`)
```sql
CREATE TABLE automation_mandates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    account_id UUID NOT NULL,
    mode VARCHAR(32) NOT NULL DEFAULT 'SEMI_AUTOMATIC',
    allowed_symbols VARCHAR(32)[] NOT NULL,
    max_capital_risk_pct NUMERIC(5, 2) NOT NULL DEFAULT 1.00,
    daily_loss_limit_usd NUMERIC(28, 10) NOT NULL,
    max_open_positions INT NOT NULL DEFAULT 3,
    news_protection BOOLEAN NOT NULL DEFAULT TRUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_mandates_user ON automation_mandates (user_id);
```

### 10.2 Circuit Breaker Events Table (`automation_circuit_breaker_events`)
```sql
CREATE TABLE automation_circuit_breaker_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL,
    breaker_type VARCHAR(64) NOT NULL, -- DAILY_DRAWDOWN | CONSECUTIVE_LOSS | NEWS_LOCKOUT
    threshold_value NUMERIC(28, 10) NOT NULL,
    observed_value NUMERIC(28, 10) NOT NULL,
    actions_taken VARCHAR(64)[] NOT NULL,
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reset_at TIMESTAMPTZ
);
```

---

## 11. Frontend Screens & Components

### 11.1 Automation Command & Mandates Cockpit
- **Mode Selector Strip**: Segmented visual control (Manual / Semi-Auto / Fully Auto) with glowing state indicator and confirmation warning dialog.
- **Circuit Breaker Status Ring**: Gauge visualizing daily loss progress (e.g. "$120 lost of $300 max limit", turns Amber at 75%, Crimson at 100%).
- **Active Position Protection Matrix**: Real-time cards for open positions displaying current Breakeven status, Trailing Stop distance, and next TP trigger.
- **Big Red Panic Button**: Floating emergency stop with sliding confirmation gate to prevent accidental trigger.

---

## 12. Security Requirements

- **SEC-001 (Mandate Cryptographic Signing)**: Fully automatic mandates require secondary authorization signature before enablement.
- **SEC-002 (Inviolable Server Limits)**: Hard maximum limits (e.g. maximum 5% daily loss) are set in server configuration and cannot be overridden by user requests.
- **SEC-003 (Fail-Closed Default)**: If automation daemon disconnects from the database or venue, all pending mandates enter suspended state.

---

## 13. Testing Strategy

- **Circuit Breaker Trip Invariant Tests**: Synthetic simulations driving account balances below loss limits; verify 100% of order attempts are blocked.
- **News Lockout Chrono Tests**: Mock clock advancing into economic news window; confirm orders are rejected with `ATLAS-AUTO-NEWS-LOCK`.
- **Trailing Stop Slippage Benchmarks**: Measure trailing stop trigger accuracy across fast-moving tick datasets.

---

## 14. Deployment Plan

- **Low-Latency Supervision Service**: The automation engine runs as an independent daemon (`services/worker/src/automation/`) maintaining hot in-memory state in Redis for rapid execution.
- **High-Availability Heartbeat**: Health check pinging Redis and Postgres every 2 seconds; triggers automated failover to standby worker if primary halts.

---

## 15. Future Enhancements

- **Reinforcement Learning Dynamic Trailing**: Machine-learning model dynamically widening or tightening trailing stops based on real-time order book liquidity depth.
- **Cross-Venue Hedging Automation**: Automated synthetic delta-neutral hedging across correlated venues during unexpected market shocks.
