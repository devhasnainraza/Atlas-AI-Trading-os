# Tasks: Dashboard & Analytics

**Input**: Design documents from `/specs/spec-09-dashboard/`
**Prerequisites**: [spec.md](./spec.md), Next.js 15 App Router (`apps/web/`), Spec 00 (API), Spec 03 (agents)
**Tests**: INCLUDED — FCP / TTI load benchmarks, WebSocket reconnection chaos tests, and 60fps tick rendering tests.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: `US1`–`US3`, or blank for setup/foundational/polish

---

## Phase 1: Setup

- [ ] T001 [P] Install dashboard UI dependencies in `apps/web/package.json`: `lightweight-charts`, `zustand`, `@tanstack/react-query`, `lucide-react`, `dompurify`
- [ ] T002 [P] Establish dark obsidian theme tokens (`#080A10`), neon telemetry accents, and glassmorphic utility classes in `apps/web/src/app/globals.css`
- [ ] T003 [P] Configure TanStack Query provider and global error boundary in `apps/web/src/app/providers.tsx`

---

## Phase 2: Foundational (⚠️ CRITICAL — blocks every user story)

- [x] T004 Create Alembic migration for `dashboard_user_layouts` in `apps/api/src/atlas_api/modules/platform/migrations/`
- [ ] T005 [P] Implement WebSocket client hook (`apps/web/src/hooks/use-dashboard-socket.ts`) with exponential backoff and heartbeat pinging
- [ ] T006 [P] Implement global Zustand store (`apps/web/src/stores/use-dashboard-store.ts`) holding positions, orders, market ticks, and agent states

---

## Phase 3: User Story 1 — Multi-Agent Cognitive Cockpit & Live Stream (Priority: P1) 🎯 MVP

**Goal**: Traders watch 24/7 multi-agent reasoning, thought token streams, and radial confidence meters update in real time.

### Tests for User Story 1 ⚠️ write first, must fail

- [ ] T007 [P] [US1] Component test: Agent status ribbon accurately reflects state transitions (`IDLE`, `THINKING`, `WAITING_APPROVAL`)
- [ ] T008 [P] [US1] Integration test: SSE streaming thought tokens render progressively without re-mounting chat component

### Implementation for User Story 1

- [ ] T009 [US1] Implement `AgentStatusRibbon` component in `apps/web/src/features/dashboard/components/agent-status-ribbon.tsx`
- [ ] T010 [US1] Implement `ConfidenceRadialMeter` component in `apps/web/src/features/dashboard/components/confidence-meter.tsx`
- [ ] T011 [US1] Implement `RiskMonitorWidget` visualizing margin heat and daily drawdown in `apps/web/src/features/dashboard/components/risk-monitor.tsx`
- [x] T012 [P] [US1] Implement `GET /api/v1/dashboard/overview` endpoint in `apps/api/src/atlas_api/modules/platform/router.py`

---

## Phase 4: User Story 2 — Interactive TradingView Chart & Visual SL/TP (Priority: P1)

**Goal**: Interactive candlestick charts with draggable Stop Loss and Take Profit lines and sub-second tick updates.

### Tests for User Story 2 ⚠️ write first, must fail

- [ ] T013 [P] [US2] Performance test: Chart renders 2,000 synthetic ticks/second maintaining 60fps
- [ ] T014 [P] [US2] Component test: Dragging SL line triggers modify-order confirmation dialog with updated price

### Implementation for User Story 2

- [ ] T015 [US2] Implement `TradingViewChart` wrapper component using `lightweight-charts` in `apps/web/src/features/dashboard/components/tradingview-chart.tsx`
- [ ] T016 [US2] Implement draggable order lines overlay binding to active position SL/TP
- [ ] T017 [US2] Implement `OpenPositionsTable` with 1-click Breakeven and Market Close buttons in `apps/web/src/features/dashboard/components/positions-table.tsx`

---

## Phase 5: User Story 3 — Persistent AI Co-Pilot Drawer & Emergency Kill Switch (Priority: P1)

**Goal**: Persistent slide-out conversational drawer for multi-agent co-piloting, paired with a permanent red emergency kill switch.

### Tests for User Story 3 ⚠️ write first, must fail

- [ ] T018 [P] [US3] Security test: Chat markdown output strips malicious scripts via DOMPurify before DOM insertion
- [ ] T019 [P] [US3] Integration test: Emergency Kill Switch button triggers API halt request within 200ms

### Implementation for User Story 3

- [ ] T020 [US3] Implement `CoPilotDrawer` slide-out chat component in `apps/web/src/features/dashboard/components/copilot-drawer.tsx`
- [ ] T021 [US3] Implement `EmergencyKillSwitchModal` with slide-to-confirm safety gate in `apps/web/src/features/dashboard/components/kill-switch-modal.tsx`
- [ ] T022 [P] [US3] Implement persistent master header with venue connection latency pills and session badges

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T023 [P] Lighthouse audit: Verify First Contentful Paint < 800ms and Time to Interactive < 1.2s
- [ ] T024 [P] Storybook visual regression catalog for all core dashboard widgets
