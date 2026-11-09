# Spec 02 — Trading Integrations & Broker Layer

**Project**: Atlas AI Trading OS  
**Status**: Ratified | **Version**: 1.0.0 | **Date**: 2026-09-21  
**Target Path**: `specs/spec-02-trading-platform/`  
**Constitutional Compliance**: Core Principles I, II, III, VI, IX, X Verified  

---

## 1. Vision & Goals

### 1.1 System Vision
Spec 02 connects Atlas AI Trading OS to the global financial ecosystem. It provides a unified, normalized trading and market data abstraction layer spanning traditional Forex brokers and modern Cryptocurrency exchanges. The broker layer empowers traders and AI agents to stream live market data, inspect account equity and margin in real time, and execute orders through an unbypassable pre-trade risk gate with zero exposure of broker credentials to client surfaces.

### 1.2 Core Business & Technical Goals
- **Universal Venue Normalization**: Standardized `VenueAdapter` protocol mapping heterogeneous APIs (MetaTrader 5, cTrader, Interactive Brokers, Binance, Bybit, OKX, Kraken, Coinbase, Alpaca) and an internal high-fidelity Paper Trading engine into identical domain models.
- **Unbypassable Pre-Trade Risk Gate**: Every order submission—whether initiated by a human trader or an AI agent—must pass algorithmic risk checks (drawdown limit, leverage check, max position size, daily loss limit) before reaching venue adapters.
- **Float Ban & Mathematical Precision**: All prices, lots, contract sizes, margin requirements, account balances, and PnL values are strictly typed as arbitrary-precision `Decimal`. Floating-point operations (`float`) are completely forbidden.
- **Continuous Automated Reconciliation**: High-frequency background reconciliation compares internal platform position state against external broker snapshots, identifying and alarming on out-of-band trades or fill discrepancies.
- **Fail-Safe Circuit Breakers & Emergency Kill Switches**: Instantaneous capability to halt order routing, cancel open orders, and flatten active exposures across all connected venues in single-click or programmatic emergency conditions.

---

## 2. Functional Requirements

- **FR-001**: The platform MUST implement the `VenueAdapter` protocol supporting:
  - Forex/CFD: MetaTrader 5 (MT5 Gateway), cTrader Open API, Interactive Brokers (TWS / Client Portal API), Alpaca.
  - Crypto Spot & Derivatives: Binance, Bybit, OKX, Kraken, Coinbase Advanced.
  - Simulation: Built-in deterministic Paper Trading engine with customizable slippage and latency simulation.
- **FR-002**: Market data ingestion MUST normalize order book depth (L1/L2), live trade ticks, and OHLCV bars across all venues into immutable `QuoteTick` and `Bar` models.
- **FR-003**: The platform MUST stream real-time account balances, free margin, used margin, unrealized PnL, and current equity from connected venues.
- **FR-004**: Order execution MUST support order types: `MARKET`, `LIMIT`, `STOP_LOSS`, `STOP_LIMIT`, `TRAILING_STOP`, with time-in-force parameters `GTC`, `IOC`, `FOK`.
- **FR-005**: Order management MUST support order modification (price, quantity), cancellation, and partial position closures.
- **FR-006**: Every order request MUST generate a unique `order_intent_id` ensuring strict idempotency; duplicate order submissions with identical intents MUST be rejected without hitting venues.
- **FR-007**: The pre-trade risk gate MUST evaluate account-level and portfolio-level risk policies (max position size, account margin headroom, max daily loss, prohibited symbol checks) before order dispatch.
- **FR-008**: Continuous reconciliation workers MUST run at scheduled cadences (default every 15 seconds) comparing venue-reported positions against local state and emitting discrepancy events if variances occur.
- **FR-009**: The platform MUST support global and venue-specific Kill Switches that immediately pause order submission and optionally issue batch-cancel instructions.
- **FR-010**: All financial calculations MUST use `Decimal` with venue-defined lot steps and tick sizes; floating-point money is barred via AST linters in CI.

---

## 3. Non-Functional Requirements

- **NFR-001 (Execution Pipeline Overhead)**: Internal processing latency (from API order receipt through pre-trade risk check to venue adapter dispatch) MUST NOT exceed 15ms at p95 and 25ms at p99.
- **NFR-002 (Market Tick Ingestion)**: Ingestion pipeline MUST sustain 25,000 ticks/sec across 100 simultaneous market subscriptions without backpressure or buffer overflow.
- **NFR-003 (Reconciliation Freshness)**: Venue state discrepancies MUST be detected and surfaced within 5 seconds of occurrence.
- **NFR-004 (Idempotency Window)**: Order intent idempotency guarantees MUST persist for a minimum of 7 days in distributed storage.
- **NFR-005 (Fault Isolation)**: A slow or disconnected venue adapter MUST NOT degrade market data streaming or order routing on independent healthy venues.

---

## 4. User Stories

### US-001: Trader Connects Forex & Crypto Accounts (Priority: P1)
- **Given** a trader with live accounts on MetaTrader 5 and Binance,
- **When** they link credentials via the secure vault,
- **Then** Atlas verifies connectivity, syncs balances and margin, discovers all open positions, and displays the connection status as healthy.

### US-002: Real-Time Normalized Market Ingestion (Priority: P1)
- **Given** an active subscription to `EUR/USD` (MT5) and `BTC/USDT` (Binance),
- **When** market quotes update at the venues,
- **Then** Atlas normalizes ticks into uniform models and broadcasts them over WebSockets to client UI widgets and agent listeners with sub-10ms distribution latency.

### US-003: Human-Approved Order Submission with Pre-Trade Risk Gate (Priority: P1)
- **Given** an AI agent or trader submitting a Buy Limit order for 0.5 BTC,
- **When** the order enters the execution pipeline,
- **Then** the risk gate verifies that account free margin is sufficient and max leverage is respected; once approved, the order dispatches to the venue, and fill events update local position tables.

### US-004: Emergency Kill Switch Halts Trading (Priority: P1)
- **Given** extreme market volatility or an errant automated strategy,
- **When** the trader or risk supervisor clicks "Emergency Kill Switch",
- **Then** all pending limit orders are cancelled across venues within 500ms, new order submissions are rejected, and open positions are displayed with an emergency flatten option.

---

## 5. Agent Architecture

Spec 02 provides the primary interfaces for the **Execution Agent** and the **Risk Agent**:

```text
+-------------------------------------------------------------------------+
|                        Trading Platform Subsystem                       |
|                                                                         |
|  +--------------------+                    +-------------------------+  |
|  |   Execution Agent  |                    |    Pre-Trade Risk Gate  |  |
|  |   - Smart routing  |                    |    - Margin headroom    |  |
|  |   - Multi-leg SL/TP|                    |    - Max daily loss     |  |
|  +---------+----------+                    |    - Position caps      |  |
|            |                               +------------+------------+  |
|            v                                            |               |
|  +------------------------------------------------------+------------+  |
|  |                          Execution Router                         |  |
|  |              (Idempotency -> Risk Check -> Venue Adapter)         |  |
|  +--------------------------------------+----------------------------+  |
|                                         |                               |
|        +--------------------------------+-----------------------+       |
|        |                                |                       |       |
|  +-----v--------------+      +----------v-----------+    +------v-----+ |
|  | MetaTrader 5       |      | Binance / Bybit      |    | Paper      | |
|  | Adapter (IPC/gRPC) |      | Adapter (REST/WS)    |    | Engine     | |
|  +--------------------+      +----------------------+    +------------+ |
+-------------------------------------------------------------------------+
```

---

## 6. State Design

### 6.1 Order Lifecycle State Machine
```text
[INTENT_CREATED]
       |
       v
[RISK_EVALUATING] ---> (Risk Rejection) ---> [REJECTED]
       |
       v (Risk Approved)
[SUBMITTING_TO_VENUE]
       |
       +---> (Network / Broker Error) ------> [SUBMISSION_FAILED]
       |
       v (Acknowledged by Venue)
[OPEN / ACCEPTED]
       |
       +---> [PARTIALLY_FILLED] ---> [FILLED]
       |
       +---> [CANCEL_PENDING] -----> [CANCELLED]
       |
       +---> [EXPIRED]
```

### 6.2 Position State Model
```python
@dataclass(frozen=True)
class PositionState:
    position_id: str
    account_id: str
    venue_id: str
    symbol: str
    side: str  # LONG | SHORT
    quantity: Decimal
    entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    margin_allocated: Decimal
    stop_loss: Decimal | None
    take_profit: Decimal | None
    updated_at: datetime
```

---

## 7. LangGraph Workflow Integration

Order routing is integrated into LangGraph as a strict two-stage verified transaction:

```text
[Strategy Recommendation Formulated]
                 |
                 v
+--------------------------------+
| Pre-Trade Risk Evaluation Node |
+----------------+---------------+
                 |
                 +--- (Risk Fails) ---------> [Graph Route: Log Rejection & Exit]
                 |
                 v (Risk Passes)
+--------------------------------+
| Human Confirmation Interrupt   |  (Pauses graph; yields to UI confirmation ticket)
+----------------+---------------+
                 |
                 v (User Confirms via API)
+--------------------------------+
| Venue Order Dispatch Node      |
+----------------+---------------+
                 |
                 v
+--------------------------------+
| Fill Reconciliation Node       |
+--------------------------------+
```

---

## 8. Tool Specifications

### 8.1 Submit Order Tool (`tool_trading_submit_order`)
- **Description**: Places an order through the pre-trade risk engine to the targeted venue.
- **Input Schema**:
  ```json
  {
    "type": "object",
    "required": ["account_id", "symbol", "side", "order_type", "quantity"],
    "properties": {
      "account_id": { "type": "string" },
      "symbol": { "type": "string" },
      "side": { "type": "string", "enum": ["BUY", "SELL"] },
      "order_type": { "type": "string", "enum": ["MARKET", "LIMIT", "STOP"] },
      "quantity": { "type": "string", "description": "Decimal string quantity" },
      "price": { "type": "string", "description": "Decimal string price for LIMIT" },
      "stop_loss": { "type": "string", "description": "Optional Decimal stop loss" },
      "take_profit": { "type": "string", "description": "Optional Decimal take profit" },
      "time_in_force": { "type": "string", "enum": ["GTC", "IOC", "FOK"], "default": "GTC" }
    }
  }
  ```
- **Security**: Requires `trading:execute` permission. Subject to pre-trade risk policy validation.

### 8.2 Cancel Order Tool (`tool_trading_cancel_order`)
- **Description**: Cancels an open order at the target broker or exchange.
- **Input Schema**:
  ```json
  {
    "type": "object",
    "required": ["order_id"],
    "properties": {
      "order_id": { "type": "string" }
    }
  }
  ```

### 8.3 Emergency Kill Switch Tool (`tool_trading_emergency_kill_switch`)
- **Description**: Activates immediate trading halt across all connected venues.
- **Input Schema**:
  ```json
  {
    "type": "object",
    "required": ["cancel_all_orders", "flatten_positions"],
    "properties": {
      "cancel_all_orders": { "type": "boolean", "default": true },
      "flatten_positions": { "type": "boolean", "default": false },
      "venue_id": { "type": "string", "description": "Optional venue filter" }
    }
  }
  ```

---

## 9. API Specifications

### 9.1 Account & Position Queries
- **`GET /api/v1/trading/accounts`**: Returns connected trading accounts with balance, equity, and margin details.
- **`GET /api/v1/trading/positions`**: Returns all open positions across venues with live unrealized PnL.
- **`GET /api/v1/trading/orders`**: Lists active and historical orders with status, fills, and timestamps.

### 9.2 Order Operations
- **`POST /api/v1/trading/orders`**: Submits a new order intent through the risk gate.
- **`DELETE /api/v1/trading/orders/{id}`**: Cancels an open order.
- **`POST /api/v1/trading/kill-switch`**: Triggers system-wide or venue-scoped emergency shutdown.

### 9.3 Real-Time WebSockets
- **`WS /api/v1/marketdata/stream`**: Real-time tick and orderbook streaming.
  - Subscription: `{"action": "subscribe", "channels": ["ticks:EURUSD", "l2:BTCUSDT"]}`.
- **`WS /api/v1/trading/stream`**: Real-time order status, execution reports, and position updates.

---

## 10. Database Schema

### 10.1 Orders Table (`trading_orders`)
```sql
CREATE TABLE trading_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    intent_id UUID NOT NULL UNIQUE,
    account_id UUID NOT NULL,
    venue_id VARCHAR(64) NOT NULL,
    venue_order_id VARCHAR(128),
    symbol VARCHAR(32) NOT NULL,
    side VARCHAR(16) NOT NULL,
    order_type VARCHAR(32) NOT NULL,
    quantity NUMERIC(28, 10) NOT NULL,
    price NUMERIC(28, 10),
    stop_loss NUMERIC(28, 10),
    take_profit NUMERIC(28, 10),
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING_RISK',
    executed_quantity NUMERIC(28, 10) NOT NULL DEFAULT 0,
    cumulative_quote_qty NUMERIC(28, 10) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_orders_account ON trading_orders (account_id, created_at DESC);
CREATE INDEX idx_orders_status ON trading_orders (status);
```

### 10.2 Positions Table (`trading_positions`)
```sql
CREATE TABLE trading_positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL,
    venue_id VARCHAR(64) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    side VARCHAR(16) NOT NULL,
    quantity NUMERIC(28, 10) NOT NULL,
    entry_price NUMERIC(28, 10) NOT NULL,
    current_price NUMERIC(28, 10) NOT NULL,
    unrealized_pnl NUMERIC(28, 10) NOT NULL,
    realized_pnl NUMERIC(28, 10) NOT NULL DEFAULT 0,
    stop_loss NUMERIC(28, 10),
    take_profit NUMERIC(28, 10),
    last_reconciled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_position_account_symbol UNIQUE (account_id, venue_id, symbol)
);
```

---

## 11. Frontend Screens & Components

### 11.1 Fast Order Ticket & Risk Guard Screen
- Responsive side-drawer ticket featuring symbol selector, quick lot/quantity buttons, and dual BUY/SELL action cards with real-time bid/ask prices.
- **Dynamic Risk Gauge**: Visual bar displaying margin utilization % before and after order submission. Flags warnings if proposed trade exceeds 2% account equity risk.

### 11.2 Real-Time Positions & Execution Terminal
- Live reactive table displaying Symbol, Side, Size, Entry, Mark Price, Liquidation Price, Margin, TP/SL, and Unrealized PnL (in currency and percentage with green/red badges).
- Quick action buttons: "Market Close", "Close 50%", "Edit SL/TP".
- Floating red **Emergency Kill Switch** button in the global toolbar with safety confirmation guard.

---

## 12. Security Requirements

- **SEC-001 (Zero Broker Key Disclosure)**: Venue API secrets and private keys are never transmitted to client browsers or exposed in API responses.
- **SEC-002 (Pre-Trade Risk Primacy)**: Risk rules are compiled and enforced server-side; client manipulation of risk parameters cannot bypass server policy validation.
- **SEC-003 (Idempotency Enforcement)**: Unique intent tokens protect against double-submission caused by network retries.
- **SEC-004 (Float Prohibition)**: Float values in order parameters are rejected by Pydantic serializers with explicit validation errors.

---

## 13. Testing Strategy

- **Adapter Conformance Test Suite**: Standardized mock test suite verifying every `VenueAdapter` handles rate limits, network disconnects, partial fills, and error mapping identically.
- **Pre-Trade Risk Gate Unit Tests**: Comprehensive matrix testing position limits, margin breaches, max loss cutoffs, and forbidden symbol rejections.
- **Continuous Reconciliation Invariant Tests**: Synthetic test injecting out-of-band trade into paper engine to confirm reconciliation job detects and reports variance within 1 second.
- **Float Ban AST Linter**: CI check confirming zero float usage in `modules/trading`, `modules/marketdata`, and `shared/atlas_venues`.

---

## 14. Deployment Plan

- **High-Performance Ingestion Pods**: Dedicated worker pods configured with high memory and network limits to process WebSockets ticks and maintain in-memory order books.
- **Network Routing & Colocation**: Deployed in cloud regions nearest to major exchange nodes (e.g. AWS `us-east-1` for US equities/Forex, `ap-northeast-1` / `eu-central-1` for major crypto venues).
- **Graceful Shutdown Procedures**: Workers drain pending order queues and unbind WebSocket subscriptions before pod termination.

---

## 15. Future Enhancements

- **FIX Protocol Engine**: High-speed Financial Information eXchange (FIX 4.4 / 5.0) gateway for direct institutional prime brokerage connectivity.
- **Smart Order Routing (SOR)**: Algorithmic order splitting across multiple venues to minimize price impact and slippage.
- **Algorithmic Execution Slicers**: Built-in TWAP (Time-Weighted Average Price) and VWAP (Volume-Weighted Average Price) execution algorithms.
