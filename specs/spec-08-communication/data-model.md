# Data Model: Communication Platform

**Feature**: 08-communication | **Date**: 2026-09-21 | **Plan**: [plan.md](./plan.md)

Conventions per Spec 00: UUIDv7 `id` primary keys, `created_at` / `updated_at` `timestamptz`, snake_case names, enums CHECK-constrained. Tables carry indexed `user_id` for multi-tenant isolation. External identifiers (phone numbers, webhook URLs) stored encrypted using the Spec 01 credential vault.

## communication_channels

Registered outbound and inbound communication destinations configured by users.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| user_id | uuid | FK user; indexed |
| channel_type | text | `TELEGRAM | DISCORD | SLACK | WHATSAPP | SMS | EMAIL | WEB_PUSH` |
| destination | text | Chat ID, Webhook URL, or Phone Number (AES-256 encrypted at rest) |
| destination_masked| text | Masked display string (e.g. `+1 (***) ***-8912`, `Discord #trading-alerts`) |
| is_verified | boolean | Requires successful 2-way handshake or bot code entry |
| is_enabled | boolean | Active toggle |
| min_priority | text | `P0 | P1 | P2 | P3` (Minimum priority level routed to this channel) |
| created_at | timestamptz | Registration timestamp |
| updated_at | timestamptz | Modification timestamp |

## communication_preferences

User-specific notification rules, quiet hours, and channel routing priorities.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| user_id | uuid | FK user; unique |
| quiet_hours_enabled| boolean | Toggles suppression of non-P0 alerts during sleep |
| quiet_hours_start | time | e.g. `22:00:00` |
| quiet_hours_end | time | e.g. `06:30:00` |
| timezone | text | IANA timezone (e.g. `America/New_York`, `Asia/Tokyo`) |
| emergency_phone | text | Secondary phone number for Twilio voice calls on P0 events |
| digest_frequency | text | `REALTIME | HOURLY | DAILY_DIGEST` |
| updated_at | timestamptz | Last updated timestamp |

## communication_action_tokens

Ephemeral, single-use HMAC-signed tokens enabling 1-click execution from mobile messaging channels.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| token_hash | text | SHA-256 hash of the generated token string; unique, indexed |
| user_id | uuid | FK user; indexed |
| action_type | text | `APPROVE_TRADE | REJECT_TRADE | EMERGENCY_FLATTEN | PAUSE_AI` |
| payload | jsonb | Target parameters (e.g. `{"proposal_id": "...", "account_id": "..."}`) |
| expires_at | timestamptz | Hard 5-minute TTL; indexed |
| is_consumed | boolean | Atomic flag preventing token replay |
| consumed_at | timestamptz | Timestamp when action was executed |

## communication_delivery_log

Comprehensive audit ledger capturing every outbound message dispatch attempt.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| notification_id | uuid | Global correlation identifier |
| user_id | uuid | FK user; indexed |
| channel_type | text | Target channel |
| priority | text | `P0 | P1 | P2 | P3` |
| status | text | `PENDING | SENT | DELIVERED | FAILED | SUPPRESSED_QUIET_HOURS` |
| attempt_count | int | Number of retry attempts made (up to 3) |
| provider_msg_id | text | Third-party provider message ID (Twilio SID, Telegram msg ID) |
| error_message | text | Sanitized error code and message on failure |
| dispatched_at | timestamptz | Timestamp of initial dispatch; indexed |
