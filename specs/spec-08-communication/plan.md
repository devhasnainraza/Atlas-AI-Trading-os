# Implementation Plan: Communication Platform

**Branch**: `08-communication` | **Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/spec-08-communication/spec.md`

## Summary

Deliver Atlas's omnichannel notification and bi-directional mobile command hub: bridging traders and agents across Telegram, Discord, Slack, WhatsApp, SMS, Web Push, and emergency Twilio voice calls. Features a 4-tier priority alert matrix (P0 Emergency through P3 Low Priority), HMAC-signed single-use action tokens for 1-click trade confirmations in mobile chat, an intelligent deduplication and quiet-hours engine, and an inbound NLP command parser allowing traders to query status, analyze assets, and execute emergency flatten commands directly from mobile messengers.

## Technical Context

**Language/Version**: Python 3.12 (notification dispatchers & webhook intake in `apps/api`), TypeScript 5.x / Next.js 15 (notification routing matrix & bot pairing screens in `apps/web`)  
**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2 (async) + Alembic, aiohttp / httpx (external webhook dispatch), python-telegram-bot / direct Telegram Bot API, discord-webhook / Discord interactions, twilio (Voice & SMS fallback), pywebpush (VAPID web push), Redis 7 (alert deduplication caches & HMAC token storage), Celery (async dispatch queues)  
**Storage**: PostgreSQL 16 (communication channels, notification preferences, delivery audit log, action tokens), Redis 7 (channel rate limits, alert deduplication hashes, quiet-hours lookup cache), Kafka (`atlas.communication.*` topics)  
**Testing**: pytest-asyncio, wiremock / mock external API servers (Telegram, Discord, Twilio), HMAC signature tamper tests, time-zone quiet hours fuzzing, Schemathesis (webhook intake contracts)  
**Target Platform**: Containerized Linux worker pools (dedicated Celery worker queues for outbound HTTP dispatch + FastAPI webhook endpoints)  
**Performance Goals**: P0 Emergency voice/SMS dispatch < 500ms; P1 Trade alert dispatch < 1,000ms; inbound chat webhook ACK < 200ms; 5,000 messages/min delivery throughput  
**Constraints**: Zero transmission of API keys, passwords, or raw secrets over external chat channels; interactive action tokens strictly expire in 5 minutes and are single-use; all incoming webhooks require cryptographic signature verification  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Compliance in this plan | Status |
|---|-----------|------------------------|--------|
| I | Human First | Mobile chat interfaces keep humans firmly in the loop with 1-click approvals and instant remote emergency stops. | ✅ |
| II | Security First | Inbound webhooks validated with provider HMAC signatures; action tokens bound to single-use nonces; zero secrets in chat payloads. | ✅ |
| III | Transparency | Alerts carry complete trade parameters, confidence scores, and reasons for triggered risk events. | ✅ |
| IV | Multi-Agent Collab | Notification Agent receives messages from all other agents, triaging priority before outbound routing. | ✅ |
| V | Explainability | Delivery logs record attempt counts, provider response codes, and sanitized failure reasons. | ✅ |
| VI | Risk Before Profit | P0 emergency alerts (margin calls, daily loss limit trips) bypass quiet hours and activate telecom channels (voice call/SMS). | ✅ |
| VII | Continuous Learning | User chat commands and response speeds captured to personalize alert delivery timing and channel preferences. | ✅ |
| VIII | Privacy by Design | External channel identifiers (phone numbers, chat IDs) encrypted at rest using Spec 01 vault encryption. | ✅ |
| IX | Reliability | Asynchronous outbound dispatch with exponential backoff retries and Dead-Letter Queue logging; core trading never blocked by slow webhooks. | ✅ |
| X | Modular Architecture | Clean separation between notification channel adapters (`adapters/telegram.py`, etc.) and the core Notification Agent. | ✅ |
| XI | Observability | Delivery latency histograms, delivery success/failure ratios, and channel queue depths exported to Prometheus. | ✅ |
| XII | Scalability | Sharded worker queues prevent high-volume social alerts from delaying critical P0 emergency alerts. | ✅ |

**Gate result**: PASS.

## 1. High-Level Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│ System Event Sources: Decision Engine · Circuit Breaker · Intelligence │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Notification Agent & Priority Triage (services/worker/src/notify/)     │
│  - Categorizes into P0 (Emergency), P1 (Trades), P2 (Intel), P3 (Info) │
│  - Filters against User Preferences & Timezone Quiet Hours             │
│  - Deduplicates repetitive alerts in Redis (< 10 min window)           │
└───────┬────────────────────────────────────────────────────────────────┘
        │
        ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Channel Routing & Action Token Signer                                  │
│  - Generates HMAC-SHA256 Single-Use Action Token for interactive cards │
│  - Encodes 5-minute TTL                                                │
└───────┬────────────────────────────────────────────────────────────────┘
        │
        ├──────────────────────┬──────────────────────┬──────────────────┐
        ▼                      ▼                      ▼                  ▼
┌───────────────┐      ┌───────────────┐      ┌───────────────┐  ┌───────────────┐
│ Telegram Bot  │      │ Discord Web-  │      │ Twilio Voice  │  │ Web Push /    │
│  (Inline      │      │  hook / Embed │      │  & SMS Fall-  │  │  Mobile FCM   │
│   Keyboards)  │      │   with Buttons│      │   back (P0)   │  │  (VAPID)      │
└───────┬───────┘      └───────┬───────┘      └───────────────┘  └───────────────┘
        │                      │
        │ Trader Clicks Action │
        ▼                      ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Inbound Webhook Gateway (apps/api/communication/webhooks)              │
│  - Validates Telegram / Discord Cryptographic Signatures               │
│  - Verifies HMAC Action Token (Not Expired, Not Replayed)              │
│  - Emits `atlas.agent.human_approved` event to resume LangGraph thread │
└────────────────────────────────────────────────────────────────────────┘
```

## 2. Directory Structure

```text
specs/spec-08-communication/
├── spec.md              # Specification document
├── plan.md              # This architecture plan
├── data-model.md        # Data models (channels, preferences, logs)
└── tasks.md             # Test-first task breakdown
```

## 3. Core Technical Decisions & Rationale

### ADR-08-01: Single-Use Ephemeral Action Tokens for Chat Approvals
- **Context**: Allowing trade execution via Telegram/Discord buttons creates security vulnerability if messages are forwarded or chat sessions are compromised.
- **Decision**: Embed an HMAC-SHA256 action token encoding `user_id + proposal_id + action + nonce + expiry`. The token is validated and marked consumed in Redis atomically upon the first webhook callback.
- **Consequences**: Zero replay capability; expires in 5 minutes; guarantees only the intended trader can trigger execution.

### ADR-08-02: Isolated Priority Dispatch Queues
- **Context**: A flood of informational intelligence alerts (P2/P3) during market volatility could saturate HTTP worker threads, delaying critical margin call warnings (P0).
- **Decision**: Partition Celery worker queues into `queue_emergency` (P0), `queue_trading` (P1), and `queue_bulk` (P2/P3) with dedicated worker thread allocations.
- **Consequences**: Guarantees sub-500ms dispatch for life-critical risk alerts under all system loads.

### ADR-08-03: Provider-Agnostic Channel Abstraction
- **Context**: New messaging platforms emerge frequently (e.g. Signal, Matrix, WhatsApp Cloud).
- **Decision**: Implement a unified `ChannelAdapter` interface (`send_alert`, `parse_webhook`, `verify_signature`) separating business logic from platform-specific SDKs.
- **Consequences**: Adding new communication channels requires zero modification to core agent notification logic.
