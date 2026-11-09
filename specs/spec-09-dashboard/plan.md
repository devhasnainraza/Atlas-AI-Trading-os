# Implementation Plan: Dashboard & Analytics

**Branch**: `09-dashboard` | **Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/spec-09-dashboard/spec.md`

## Summary

Deliver Atlas's elite mission-control cockpit: a responsive Next.js 15 (App Router) web application crafted with Tailwind CSS, shadcn/ui, and TradingView Lightweight Charts in an obsidian glassmorphic dark-mode palette (`#080A10`). The cockpit integrates real-time WebSocket telemetry for tick charts and positions, live visual activity stream for all 13 AI agents, radial confidence dials, draggable chart stop-loss/take-profit handles, a persistent slide-in AI Co-Pilot drawer with SSE token streaming, customizable widget grids, and an instantaneous emergency kill-switch.

## Technical Context

**Language/Version**: TypeScript 5.x / Node 22 LTS (frontend in `apps/web`), Python 3.12 (real-time WebSocket & aggregator backend in `apps/api`)  
**Primary Dependencies**: Next.js 15, React 19, Tailwind CSS, shadcn/ui, Radix UI primitives, Lucide icons, lightweight-charts (TradingView), TanStack Query v5, Zustand (client state management), dompurify (markdown sanitization), framer-motion (micro-animations)  
**Storage**: PostgreSQL 16 (user widget layout preferences, saved watchlists, custom indicators), Redis 7 (WebSocket subscription channels & live ticker fan-out)  
**Testing**: Vitest + React Testing Library (widget unit tests), Playwright (E2E browser tests: chart interactions, drag-and-drop SL adjustments, kill switch modal), Storybook (component visual regression), Lighthouse (performance & accessibility audits)  
**Target Platform**: Edge CDN / standalone containerized Next.js Node 22 runtime + FastAPI WebSocket edge gateway  
**Performance Goals**: First Contentful Paint (FCP) < 800ms; Time to Interactive (TTI) < 1.2s; 60fps chart rendering during high-frequency market tick bursts; client memory footprint < 200MB over 24h continuous operation  
**Constraints**: Zero float rendering for financial prices/PnL (strict string-formatted Decimal representation); absolute ban on raw tokens/secrets in browser storage; complete XSS defense on all streaming agent markdown; WCAG 2.1 AA contrast compliance  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Compliance in this plan | Status |
|---|-----------|------------------------|--------|
| I | Human First | Primary user cockpit; empowers traders with total visibility, intuitive drag-and-drop trade adjustments, and 1-click panic stop. | ✅ |
| II | Security First | HttpOnly session cookies; zero credentials in LocalStorage; strict DOMPurify sanitization on all streaming LLM text. | ✅ |
| III | Transparency | Every widget clearly identifies underlying venue source, latency in milliseconds, and calculation timestamp. | ✅ |
| IV | Multi-Agent Collab | 13-agent status ribbon renders live state chips and thought tokens, demystifying agent coordination. | ✅ |
| V | Explainability | Interactive trade cards render full evidence, counter-arguments, and risk metrics before approval. | ✅ |
| VI | Risk Before Profit | Risk monitor widget prominently displays margin heat and daily drawdown progress ring with color warning bands. | ✅ |
| VII | Continuous Learning | Trader UI feedback and journal annotations captured seamlessly from the dashboard. | ✅ |
| VIII | Privacy by Design | User layouts, watchlists, and custom views partitioned strictly by authenticated `user_id`. | ✅ |
| IX | Reliability | Automatic WebSocket reconnection with visual fallback offline pills; UI remains functional during temporary disconnects. | ✅ |
| X | Modular Architecture | Modular widget architecture allows independent development and dynamic code-split chunk loading. | ✅ |
| XI | Observability | Web Vitals (FCP, LCP, CLS), client render latencies, and WebSocket drops monitored via OpenTelemetry web SDK. | ✅ |
| XII | Scalability | Virtualized table rows for high-volume positions/orders; delta-only WebSocket payloads minimize network bandwidth. | ✅ |

**Gate result**: PASS.

## 1. High-Level Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│ Client Browser (Next.js 15 React 19 Client SPA)                       │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ Persistent Header: Latency Pills | Market Sessions | Panic Halt│   │
│   └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│   ┌─────────────────────┬───────────────────────┬──────────────────┐   │
│   │ Watchlist / Scanner │ TradingView Chart     │ Agent Mesh Ribbon│   │
│   │ - Real-time RVOL    │ - Draggable SL/TP     │ - 13 Agent Chips │   │
│   │ - Multi-asset heat  │ - Order overlay lines │ - Live thoughts  │   │
│   ├─────────────────────┴───────────────────────┼──────────────────┤   │
│   │ Open Positions & Active Orders Table        │ Confidence Dial  │   │
│   │ - Live Unrealized PnL | 1-Click Breakeven   │ Risk Heat Gauge  │   │
│   └─────────────────────────────────────────────┴──────────────────┘   │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ Slide-In Co-Pilot Drawer: Streaming Thought Tokens & Approvals │   │
│   └────────────────────────────────────────────────────────────────┘   │
└───────────────────▲───────────────────────────────▲────────────────────┘
                    │                               │
         WebSocket Connection (/ws)        SSE Chat Stream (/api/chat)
                    │                               │
┌───────────────────▼───────────────────────────────▼────────────────────┐
│ apps/api: Real-Time Gateway & Aggregator                               │
│  - Session Auth Verification via HttpOnly Cookie                       │
│  - Redis Pub/Sub Fanout for Ticks & Positions                          │
│  - Server-Sent Events (SSE) LangGraph Token Stream                     │
└────────────────────────────────────────────────────────────────────────┘
```

## 2. Directory Structure

```text
specs/spec-09-dashboard/
├── spec.md              # Specification document
├── plan.md              # This architecture plan
├── data-model.md        # Data models (layouts, watchlists, presets)
└── tasks.md             # Test-first task breakdown
```

## 3. Core Technical Decisions & Rationale

### ADR-09-01: TradingView Lightweight Charts with Canvas Overlays
- **Context**: Full TradingView charting library is heavy (>1MB JS) and commercial; retail traders need fast, responsive charting with interactive order lines.
- **Decision**: Adopt open-source `lightweight-charts` (<45KB) augmented with custom HTML5 Canvas overlays for draggable Stop Loss and Take Profit lines.
- **Consequences**: Blazing-fast initial load times (<800ms) with full 60fps rendering performance.

### ADR-09-02: Delta-Only WebSocket State Synchronization
- **Context**: Re-broadcasting full position and order arrays on every market tick causes severe CPU thrashing in browser React state trees.
- **Decision**: WebSocket emits granular delta packets (`{ type: "TICK", symbol: "BTCUSDT", price: "67420.50", unpnl: "+142.50" }`). Zustand client store updates targeted records in-place without triggering full table re-renders.
- **Consequences**: Guarantees zero UI lag even when processing 2,000+ ticks/sec.

### ADR-09-03: DOMPurify Sanitization on Streaming Agent Tokens
- **Context**: Streaming AI agent responses directly into the UI creates a critical Cross-Site Scripting (XSS) attack vector if external content contains malicious scripts.
- **Decision**: Stream tokens through a sanitizing markdown renderer using `DOMPurify` with strict HTML whitelisting before DOM insertion.
- **Consequences**: Completely neutralizes prompt injection XSS attacks.
