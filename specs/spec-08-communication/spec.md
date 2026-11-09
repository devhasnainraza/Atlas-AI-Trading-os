# Spec 08 — Communication Platform

**Project**: Atlas AI Trading OS  
**Status**: Ratified | **Version**: 1.0.0 | **Date**: 2026-09-21  
**Target Path**: `specs/spec-08-communication/`  
**Constitutional Compliance**: Core Principles I, II, III, VIII, XI Verified  

---

## 1. Vision & Goals

### 1.1 System Vision
Spec 08 builds the omnichannel messaging and bi-directional command interface for Atlas AI Trading OS. In fast-moving global markets, traders are not always seated at their trading desks. Spec 08 allows traders to stay informed through their preferred communication channels (Telegram, Discord, Slack, WhatsApp, SMS, Push, Voice Calls) while enabling them to issue natural language commands and execute critical risk actions (closing positions, pausing automation) directly from mobile chat applications.

### 1.2 Core Business & Technical Goals
- **Omnichannel Outbound Alerts**: Unified notification dispatch across Telegram, Discord, Slack, WhatsApp Business, Email, Web Push, SMS, and emergency Voice Calls (Twilio).
- **Bi-Directional Chat Command Interface**: Secure webhook intake allowing traders to interact with the OS using natural language or slash commands (e.g. `Analyze BTC`, `Close EURUSD`, `Pause AI`, `Weekly Report`).
- **Priority-Tiered Notification Matrix**: Intelligent classification preventing alert fatigue:
  - `P0 Emergency`: Immediate Voice Call / SMS / Push (Margin call, circuit breaker tripped, emergency stop).
  - `P1 Trade Signals & Approvals`: Interactive Telegram/Discord buttons with 1-click execution.
  - `P2 Market Intelligence`: Configurable digests and whale alerts.
  - `P3 Low Priority`: Weekly coaching reports and administrative updates.
- **Anti-Spam Deduplication & Quiet Hours**: Intelligent rate-limiting ensuring repetitive alerts are consolidated into digests, respecting user sleep and time-zone preferences.
- **Cryptographic Command Authorization**: Interactive buttons and commands use single-use signed tokens to prevent spoofing or unauthorized chat actions.

---

## 2. Functional Requirements

- **FR-001**: The platform MUST implement outbound notification adapters for:
  - `Telegram`: Bot API with inline keyboards for interactive trade approval.
  - `Discord`: Rich embed webhooks with colored status banners and buttons.
  - `Slack`: Interactive Block Kit messages with workspace bot support.
  - `WhatsApp`: Cloud API templates for verified transaction notifications.
  - `Push Notifications`: Web Push (VAPID) and Mobile APNs / FCM.
  - `SMS & Voice`: Twilio fallback for critical margin calls and circuit breaker events.
  - `Email`: Transactional HTML email templates (SendGrid / Resend).
- **FR-002**: The bi-directional command engine MUST parse and execute standard chat commands:
  - `Analyze <symbol>`: Triggers multi-agent research and returns summarized card.
  - `Status`: Returns active positions, daily PnL, and agent system state.
  - `Close <symbol|all>`: Issues market close request through the risk gate.
  - `Pause AI`: Disarms all autonomous trading mandates immediately.
  - `Resume AI`: Re-arms mandates with user confirmation.
  - `Report`: Delivers latest daily or weekly performance summary.
- **FR-003**: The Notification Agent MUST support user-configurable channel routing (e.g. "Send P0 to Phone Call, P1 to Telegram, P2 to Discord").
- **FR-004**: Interactive buttons in chat messages (e.g. "Approve Trade") MUST be secured by ephemeral HMAC-signed action tokens that expire in 5 minutes.
- **FR-005**: The system MUST implement smart deduplication: multiple rapid price alerts on the same asset within 10 minutes are batched into a single consolidated update.
- **FR-006**: The platform MUST support configurable Quiet Hours (e.g. `22:00–06:00 Local Time`) during which all non-P0 alerts are held until morning.

---

## 3. Non-Functional Requirements

- **NFR-001 (Notification Dispatch Latency)**: P0 Emergency alerts MUST be dispatched to telecom/webhook providers in < 500ms; P1 Trade alerts in < 1,000ms.
- **NFR-002 (Inbound Command Processing)**: Incoming chat webhooks MUST be acknowledged with HTTP 200 within 200ms and process user intent asynchronously.
- **NFR-003 (Reliability & Retries)**: Outbound notifications MUST implement exponential backoff retries (3 attempts) with dead-letter queue logging for undelivered messages.
- **NFR-004 (Delivery Throughput)**: The notification pipeline MUST sustain 5,000 simultaneous push/webhook messages per minute during high-volatility events.

---

## 4. User Stories

### US-001: One-Click Trade Approval via Telegram (Priority: P1)
- **Given** an active trader walking away from their desk,
- **When** the Decision Engine generates a 78% confidence proposal on `BTC/USDT`,
- **Then** the trader receives a Telegram message with an inline chart preview, key metrics, and an "Approve Trade" button; clicking it securely authenticates the request and executes the order within 1 second.

### US-002: Emergency Voice Call on Circuit Breaker Trip (Priority: P1)
- **Given** unexpected flash crash market volatility triggering an account's daily loss limit,
- **When** the circuit breaker trips,
- **Then** the platform immediately initiates an automated voice call to the trader's mobile phone: "Atlas AI Emergency: Trading halted due to daily drawdown limit."

### US-003: Trader Checks Portfolio via Discord Command (Priority: P2)
- **Given** a trader typing `/status` in their private Discord channel,
- **When** the message is sent,
- **Then** the Atlas Bot replies within 2 seconds with an embed showing open positions, today's PnL (+$310.50), active agents, and margin health.

---

## 5. Agent Architecture

Spec 08 establishes the **Notification Agent** and **Inbound Command Gateway**:

```text
+-------------------------------------------------------------------------+
|                        Communication Subsystem                          |
|                                                                         |
|  +--------------------+                    +-------------------------+  |
|  | Notification Agent |                    | Inbound Command Gateway |  |
|  | - Priority triage  |                    | - NLP intent parser     |  |
|  | - Channel routing  |                    | - Slash command router  |  |
|  | - Quiet hours      |                    | - HMAC signature verify |  |
|  +---------+----------+                    +------------+------------+  |
|            |                                            |               |
|            v                                            v               |
|  +------------------------------------------------------+------------+  |
|  |                     Notification Dispatch Hub                     |  |
|  |    (Telegram | Discord | Slack | WhatsApp | Twilio | Push | Email) |  |
|  +-------------------------------------------------------------------+  |
+-------------------------------------------------------------------------+
```

---

## 6. State Design

### 6.1 Outbound Notification Envelope
```python
@dataclass(frozen=True)
class NotificationPayload:
    notification_id: str
    user_id: str
    priority: str  # P0_EMERGENCY | P1_TRADE | P2_INTELLIGENCE | P3_INFO
    category: str
    title: str
    body: str
    action_url: str | None
    action_token: str | None  # HMAC signed single-use action
    channels: tuple[str, ...]
    created_at: datetime
    expires_at: datetime
```

---

## 7. LangGraph Workflow Integration

The Notification Agent integrates into LangGraph at approval and completion points:

```text
[Graph State: Trade Proposal Formulated]
                 |
                 v
+--------------------------------+
| Dispatch Notification Node     |  Sends rich interactive message to
+----------------+---------------+  user's active channel (e.g. Telegram)
                 |
                 v
+--------------------------------+
| Human Approval Interrupt       |  Graph enters suspended state, awaiting
+----------------+---------------+  webhook callback from chat button
                 |
        (User clicks "Approve")
                 |
                 v
+--------------------------------+
| Inbound Webhook Resume Node    |  Validates HMAC token, updates graph state
+--------------------------------+  with human approval, and resumes execution
```

---

## 8. Tool Specifications

### 8.1 Dispatch Multi-Channel Alert Tool (`tool_dispatch_alert`)
- **Description**: Emits an alert across user-configured channels matching priority.
- **Input Schema**:
  ```json
  {
    "type": "object",
    "required": ["user_id", "priority", "title", "message"],
    "properties": {
      "user_id": { "type": "string" },
      "priority": { "type": "string", "enum": ["P0", "P1", "P2", "P3"] },
      "title": { "type": "string" },
      "message": { "type": "string" },
      "action_type": { "type": "string", "enum": ["APPROVE_TRADE", "VIEW_CHART", "NONE"] }
    }
  }
  ```

---

## 9. API Specifications

### 9.1 Inbound Webhook Routes
- **`POST /api/v1/communication/webhooks/telegram`**: Webhook intake for Telegram bot updates and button clicks.
- **`POST /api/v1/communication/webhooks/discord`**: Interaction endpoint for Discord slash commands and component buttons.
- **`POST /api/v1/communication/webhooks/whatsapp`**: Cloud API message webhook.

### 9.2 Notification Preferences
- **`GET /api/v1/communication/preferences`**: Retrieves user channel bindings and quiet hours.
- **`PUT /api/v1/communication/preferences`**: Updates channel preferences and alert priority routes.

---

## 10. Database Schema

### 10.1 Notification Channels Table (`communication_channels`)
```sql
CREATE TABLE communication_channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    channel_type VARCHAR(32) NOT NULL, -- TELEGRAM | DISCORD | SLACK | WHATSAPP | SMS | EMAIL
    destination VARCHAR(255) NOT NULL,  -- Chat ID, Webhook URL, Phone Number
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    min_priority VARCHAR(8) NOT NULL DEFAULT 'P2',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_comm_user ON communication_channels (user_id);
```

### 10.2 Notification Delivery Log Table (`communication_delivery_log`)
```sql
CREATE TABLE communication_delivery_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notification_id UUID NOT NULL,
    user_id UUID NOT NULL,
    channel_type VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,        -- SENT | DELIVERED | FAILED
    error_message TEXT,
    attempt_count INT NOT NULL DEFAULT 1,
    dispatched_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## 11. Frontend Screens & Components

### 11.1 Notification Preferences Matrix
- Interactive channel toggle grid: Matrix mapping alert types (Emergency, Trades, Intelligence, Reports) against channels (Telegram, Discord, Email, SMS).
- Verification modal for Telegram (bot pairing token) and Discord (server auth).
- Quiet Hours time-picker with local time conversion display.

---

## 12. Security Requirements

- **SEC-001 (HMAC Webhook Verification)**: All inbound webhooks (Telegram, Discord, Twilio) verify cryptographic signatures before processing payloads.
- **SEC-002 (Single-Use Action Tokens)**: Interactive execution tokens in messages expire after 5 minutes and become invalid immediately upon first use.
- **SEC-003 (Chat Credential Masking)**: No API keys or credentials are ever transmitted via external communication channels.

---

## 13. Testing Strategy

- **Webhook Fuzzing & Signature Verification Tests**: Validate that forged webhook payloads are rejected with HTTP 401.
- **Interactive Action Conformance Tests**: Simulate Telegram button click; verify graph resumes and executes order within latency budget.
- **Quiet Hours Filter Unit Tests**: Test notification suppression across multiple time zones during configured sleep windows.

---

## 14. Deployment Plan

- **Async Worker Delivery Queue**: Celery / Redis worker queues dedicated to external HTTP dispatch, isolating API core from third-party webhook latency spikes.

---

## 15. Future Enhancements

- **Two-Way Voice Conversational Agent**: Interactive phone call where the trader can ask "What is my PnL?" and the agent replies in natural synthetic speech.
- **Encrypted Signal Messenger Integration**: Native integration with Signal protocol for ultra-private military-grade messaging.
