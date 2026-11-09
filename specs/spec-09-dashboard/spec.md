# Spec 09 — Dashboard & Analytics

**Project**: Atlas AI Trading OS  
**Status**: Ratified | **Version**: 1.0.0 | **Date**: 2026-09-21  
**Target Path**: `specs/spec-09-dashboard/`  
**Constitutional Compliance**: Core Principles I, III, V, IX, XI, XII Verified  

---

## 1. Vision & Goals

### 1.1 System Vision
Spec 09 creates the mission-control cockpit for Atlas AI Trading OS. Built with Next.js 15 App Router, Tailwind CSS, shadcn/ui, and TradingView Lightweight Charts, the dashboard delivers an immersive, state-of-the-art visual trading environment. It brings the multi-agent cognitive architecture to life, rendering real-time market data, agent reasoning flows, confidence meters, risk matrices, and order execution controls in a rich dark-mode glassmorphic interface designed for elite operational focus.

### 1.2 Core Business & Technical Goals
- **Elite Visual Aesthetics**: Tailored obsidian color palette (`#080A10`), deep translucent glass surfaces, dynamic glowing borders, and subtle micro-animations that instill confidence and clarity without visual clutter.
- **Sub-Second Real-Time Telemetry**: Seamless live data binding via WebSockets and Server-Sent Events (SSE) updating chart ticks, orderbook depth, active positions, and agent thought streams with zero page refreshing.
- **Integrated AI Co-Pilot Drawer**: Persistent, collapsible conversational AI drawer allowing continuous natural language interaction, strategy queries, and rapid trade approvals from any view.
- **Modular Widget Architecture**: Fully customizable grid layout enabling traders to configure, resize, and persist personal dashboard widget arrangements.
- **High-Assurance Execution UI**: Error-resilient interactive components featuring clear state feedback, dual-confirmation execution gates, and instantaneous emergency stop controls.

---

## 2. Functional Requirements

- **FR-001**: The dashboard MUST be built on `Next.js 15` (App Router) using `React 19`, `TypeScript 5.x`, `Tailwind CSS`, `shadcn/ui`, and `TanStack Query v5`.
- **FR-002**: The UI MUST provide the comprehensive core widget suite:
  1. `Portfolio Widget`: Total balance, equity curve, free margin, used margin, 24h PnL ($ and %).
  2. `Open Positions Widget`: Live table with real-time unrealized PnL, lot size, SL/TP, and 1-click market close / breakeven triggers.
  3. `TradingView Lightweight Chart`: Interactive candlestick chart supporting multi-timeframe toggles, technical indicators, and visual trade execution overlays.
  4. `Market Scanner Widget`: Real-time screener filtering assets by relative volume, RSI divergence, and volatility breakouts.
  5. `Agent Status & Activity Stream`: Live visual indicators for all 13 agents showing real-time cognitive activity (`IDLE`, `THINKING`, `DEBATING`, `WAITING_APPROVAL`).
  6. `Confidence Radial Meter`: Interactive gauge reflecting current consensus trade conviction (0–100%).
  7. `Risk Monitor Widget`: Real-time margin heat gauge, daily drawdown progress bar, and correlation matrix.
  8. `Economic Calendar Widget`: Scheduled macro releases with live countdowns and actual vs. consensus indicators.
  9. `Trade Journal Preview Widget`: Cards of recent closed trades with R-multiples and emotion badges.
  10. `AI Co-Pilot Drawer`: Conversational chat panel with token streaming, code syntax highlighting, and inline approval cards.
- **FR-003**: The UI MUST maintain persistent WebSocket connections with automated exponential backoff reconnection and visual offline status pills.
- **FR-004**: Chart components MUST render active orders and open positions directly on the price axis with draggable Stop Loss and Take Profit lines.
- **FR-005**: All financial values MUST be formatted using fixed decimal precision rules matching venue specifications, avoiding floating-point rounding artifacts.
- **FR-006**: The platform MUST provide responsive support across desktop displays, ultra-wide monitors, tablets, and mobile layouts.

---

## 3. Non-Functional Requirements

- **NFR-001 (First Contentful Paint)**: Initial dashboard load (FCP) MUST occur in < 800ms on broadband connections; Time to Interactive (TTI) < 1.2s.
- **NFR-002 (Real-Time Render Performance)**: WebSocket state updates MUST achieve 60fps rendering without UI stuttering or layout thrashing during heavy tick bursts.
- **NFR-003 (Memory Optimization)**: Client browser memory consumption MUST remain stable (< 200MB) during continuous 24-hour monitoring sessions without memory leaks.
- **NFR-004 (Accessibility & Contrast)**: UI color contrast ratios MUST meet WCAG 2.1 AA standards for high readability in low-light trading environments.

---

## 4. User Stories

### US-001: Trader Monitors 24/7 Multi-Agent Reasoning (Priority: P1)
- **Given** an active trader watching the dashboard during London open,
- **When** the Market Agent flags a volume breakout and the Technical Agent calculates an ICT sweep,
- **Then** the Agent Activity Stream pulses with blue thought rings, displaying live rationale tokens and updating the Confidence Meter to 82% in real time.

### US-002: Draggable Stop Loss Adjustment on Chart (Priority: P1)
- **Given** an open long position rendered on the TradingView chart widget,
- **When** the trader drags the Stop Loss line upward to lock in profits,
- **Then** the UI prompts a fast confirmation pill and dispatches a modify-order request to the broker, updating the SL marker immediately upon venue acknowledgment.

### US-003: Instant Emergency Kill Switch from Global Navbar (Priority: P1)
- **Given** sudden unexpected market crash conditions,
- **When** the trader clicks the red "Kill Switch" button in the persistent navbar,
- **Then** an emergency modal slides in with one-click confirmation, immediately cancelling all open orders and presenting a position flatten toggle.

---

## 5. UI Component Architecture

```text
+-------------------------------------------------------------------------+
|                          Atlas Dashboard Shell                          |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  | Persistent Header (Status | Tickers | Quick Actions | Kill Switch)|  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  +---------------------+   +---------------------+   +---------------+  |
|  | Portfolio & Equity  |   | TradingView Chart   |   | Agent Mesh    |  |
|  | - Live Balance      |   | - Candlesticks      |   | - Status pills|  |
|  | - Margin heat       |   | - Interactive SL/TP |   | - Thought feed|  |
|  +---------------------+   +---------------------+   +---------------+  |
|                                                                         |
|  +-----------------------------------------------+   +---------------+  |
|  | Live Positions & Open Orders Table            |   | Confidence &  |  |
|  | - Real-time PnL | 1-Click Breakeven | Close   |   | Risk Gauges   |  |
|  +-----------------------------------------------+   +---------------+  |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  | Slide-In AI Co-Pilot Chat Drawer (Full agent conversational state)|  |
|  +-------------------------------------------------------------------+  |
+-------------------------------------------------------------------------+
```

---

## 6. State Design

### 6.1 Client Dashboard State Store (Zustand)
```typescript
interface DashboardState {
  selectedSymbol: string;
  selectedTimeframe: string;
  activeAccounts: AccountSummary[];
  positions: Position[];
  orders: Order[];
  agentStatuses: Record<string, 'IDLE' | 'THINKING' | 'DEBATING' | 'WAITING_APPROVAL'>;
  confidenceScore: number;
  isCoPilotOpen: boolean;
  isKillSwitchModalOpen: boolean;
  wsConnected: boolean;
  
  // Actions
  setSelectedSymbol: (symbol: string) => void;
  updatePositionTick: (update: PositionUpdate) => void;
  toggleCoPilot: () => void;
  triggerEmergencyHalt: () => Promise<void>;
}
```

---

## 7. LangGraph Workflow Integration

The dashboard directly binds to LangGraph streaming events using Server-Sent Events (SSE):

```text
[LangGraph Server Execution]
             |
             v (SSE Stream: /api/v1/agents/chat/stream)
+------------------------------------+
| Next.js SSE Reader Hook            |
+--------------------+---------------+
                     |
         +-----------+-----------+
         |                       |
   (Thought Token)       (Interrupt Signal)
         |                       |
         v                       v
  [Append to CoPilot]    [Open Interactive]
  [Chat Stream View ]    [Approval Drawer ]
```

---

## 8. Tool Specifications

### 8.1 Chart Screenshot Export Tool (`tool_export_chart_state`)
- **Description**: Captures high-resolution canvas snapshot of the active chart layout.
- **Input Schema**:
  ```json
  {
    "type": "object",
    "required": ["symbol", "timeframe"],
    "properties": {
      "symbol": { "type": "string" },
      "timeframe": { "type": "string" },
      "include_indicators": { "type": "boolean", "default": true }
    }
  }
  ```

---

## 9. API Specifications

### 9.1 Dashboard Data Ingestion
- **`GET /api/v1/dashboard/overview`**: Aggregated initial load payload (portfolio balances, active positions, top news, and agent states).
- **`GET /api/v1/dashboard/scanner`**: Filtered list of market opportunities matching technical presets.
- **`WS /api/v1/dashboard/realtime`**: Consolidated multi-channel WebSocket streaming price ticks, position PnL, and agent activity tokens.

---

## 10. Database Schema

### 10.1 User Dashboard Layout Preferences (`dashboard_user_layouts`)
```sql
CREATE TABLE dashboard_user_layouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE,
    layout_config JSONB NOT NULL DEFAULT '{"grid": "default", "widgets": []}'::jsonb,
    theme_preference VARCHAR(32) NOT NULL DEFAULT 'DARK_OBSIDIAN',
    default_symbol VARCHAR(32) NOT NULL DEFAULT 'EURUSD',
    default_timeframe VARCHAR(16) NOT NULL DEFAULT '15m',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## 11. Frontend Screens & Components

### 11.1 Master Dashboard Layout
- **Global Navbar**: Brand mark, active venue pills (e.g. `Binance: 24ms`, `MT5: 18ms`), Market Session badges (`London Open`), User Profile, and glowing Red Emergency Kill Switch.
- **Main Trading Stage**: 3-column responsive grid:
  - *Left*: Watchlist & Market Scanner.
  - *Center*: TradingView Candlestick Chart + Positions & Orders table.
  - *Right*: Confidence Gauge, Agent Cognitive Activity Stream, and Risk Monitor.
- **Co-Pilot Floating Drawer**: Slide-out panel from the right edge with real-time multi-agent chat, reasoning steps, and trade cards.

---

## 12. Security Requirements

- **SEC-001 (XSS Defense)**: Strict sanitization of all LLM markdown outputs using `DOMPurify` before rendering in chat and rationale cards.
- **SEC-002 (CSRF Guard on WebSockets)**: WebSocket handshake verifies origin and session cookie authentication before upgrading connections.
- **SEC-003 (Zero Sensitive Data in LocalStorage)**: No private keys, JWTs, or broker secrets are stored in browser localStorage or sessionStorage.

---

## 13. Testing Strategy

- **Component Storybook & Visual Regression**: Storybook catalog covering all widgets with chromatic visual regression tests across light/dark viewports.
- **WebSocket Reconnection Chaos Test**: Emulate intermittent network drops to verify dashboard auto-reconnects and resynchronizes state without page refresh.
- **High-Frequency Tick Stress Test**: Feed 2,000 synthetic ticks/second into the chart and positions table to confirm zero React render bottlenecking.

---

## 14. Deployment Plan

- **Vercel / Next.js Edge Runtime**: Deployed via Vercel or containerized Next.js Node 22 standalone image with global CDN caching for static assets.
- **Optimized Bundle Splitting**: Dynamic imports for heavy chart libraries (`lightweight-charts`) ensuring sub-100KB initial JavaScript chunks.

---

## 15. Future Enhancements

- **3D Liquidity Depth Visualizer**: Three.js WebGL spatial visualization of order book depth and liquidation walls.
- **Multi-Monitor Window Detach**: Pop-out browser windows for multi-monitor trading desk setups with synchronized state across windows.
