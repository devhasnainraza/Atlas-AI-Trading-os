# Tasks: Communication Platform

**Input**: Design documents from `/specs/spec-08-communication/`
**Prerequisites**: [spec.md](./spec.md), Spec 00, Spec 03 (decision/approvals), Spec 06 (circuit breakers)
**Tests**: INCLUDED — webhook signature verification, single-use action token expiry, and quiet-hours filter tests.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: `US1`–`US3`, or blank for setup/foundational/polish

---

## Phase 1: Setup

- [x] T001 [P] Scaffold communication module in `apps/api/src/atlas_api/modules/communication/`
- [x] T002 [P] Configure `CommunicationSettings` (Telegram Bot Token, Discord App ID, Twilio Auth Token, WhatsApp API Key) in `shared/atlas_core/config.py`
- [x] T003 [P] Register communication events in `shared/atlas_events/catalog.py`: `notification.dispatched`, `notification.delivered`, `command.received`

---

## Phase 2: Foundational (⚠️ CRITICAL — blocks every user story)

- [x] T004 Create Alembic migration for `communication_channels` and `communication_delivery_log` in `apps/api/src/atlas_api/modules/communication/migrations/`
- [x] T005 [P] Implement HMAC-SHA256 Token Generator & Validator for single-use 5-minute action buttons
- [x] T006 [P] Implement Notification Dispatch Hub routing messages across adapters based on priority and user preferences

---

## Phase 3: User Story 1 — One-Click Trade Approval via Telegram & Discord (Priority: P1) 🎯 MVP

**Goal**: Deliver actionable trade proposals to Telegram/Discord with interactive buttons that execute confirmed orders upon click.

### Tests for User Story 1 ⚠️ write first, must fail

- [x] T007 [P] [US1] Unit test: Inbound Telegram webhook with valid HMAC token resumes paused LangGraph workflow
- [x] T008 [P] [US1] Unit test: Expired action token (>5 min) is rejected with clear error message
- [x] T009 [P] [US1] Integration test: Trade approval proposal dispatches Telegram message with inline chart preview

### Implementation for User Story 1

- [x] T010 [US1] Implement Telegram Bot adapter with inline button keyboards in `apps/api/src/atlas_api/modules/communication/adapters/telegram.py`
- [x] T011 [US1] Implement Discord Webhook adapter with rich embeds in `apps/api/src/atlas_api/modules/communication/adapters/discord.py`
- [x] T012 [US1] Implement Webhook Endpoints `POST /api/v1/communication/webhooks/telegram` and `/discord`
- [ ] T013 [P] [US1] Web: Notification Preferences & Bot Pairing modal in `apps/web/src/features/communication/`

---

## Phase 4: User Story 2 — Emergency Voice Call & SMS on Circuit Breaker (Priority: P1)

**Goal**: Instant automated voice call and SMS dispatched to trader's phone when daily loss limits trip or emergency stop activates.

### Tests for User Story 2 ⚠️ write first, must fail

- [x] T014 [P] [US2] Unit test: P0 Emergency event triggers immediate Twilio voice call dispatch
- [x] T015 [P] [US2] Integration test: Twilio mock verification confirming speech synthesis message content

### Implementation for User Story 2

- [x] T016 [US2] Implement Twilio Voice & SMS adapter in `apps/api/src/atlas_api/modules/communication/adapters/twilio.py`
- [x] T017 [US2] Wire Kafka consumer listening to `automation.circuit_breaker.tripped` to trigger P0 dispatch immediately

---

## Phase 5: User Story 3 — Bi-Directional Chat Commands (Priority: P2)

**Goal**: Traders issue natural language commands in Telegram/Discord (`/analyze BTC`, `/status`, `/pause`) and receive instant responses.

### Tests for User Story 3 ⚠️ write first, must fail

- [x] T018 [P] [US3] Unit test: `/status` command returns active positions, today's PnL, and agent states
- [x] T019 [P] [US3] Unit test: `/pause` command successfully disarms active automation mandates

### Implementation for User Story 3

- [x] T020 [US3] Implement Inbound Command Parser routing slash commands in `apps/api/src/atlas_api/modules/communication/domain/commands.py`
- [x] T021 [US3] Wire command router to Manager Agent chat endpoint and automation controller

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T022 [P] Implement Anti-Spam Deduplication Engine consolidating rapid alerts within a 10-minute window
- [ ] T023 [P] Implement Quiet Hours Scheduler holding non-P0 alerts during configured sleep hours
