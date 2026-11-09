"""Domain models for Communication Platform (Spec 08 §2, §5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
import uuid


@dataclass
class CommunicationChannel:
    id: str
    user_id: str
    channel_type: str  # TELEGRAM | DISCORD | SLACK | WHATSAPP | SMS | EMAIL | WEB_PUSH
    destination: str
    destination_masked: str
    is_verified: bool
    is_enabled: bool
    min_priority: str  # P0 | P1 | P2 | P3
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class CommunicationPreferences:
    id: str
    user_id: str
    quiet_hours_enabled: bool
    quiet_hours_start: str  # "22:00:00"
    quiet_hours_end: str    # "06:30:00"
    timezone: str           # "UTC" or IANA
    emergency_phone: str | None = None
    digest_frequency: str = "REALTIME"  # REALTIME | HOURLY | DAILY_DIGEST
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ActionTokenRecord:
    id: str
    token_hash: str
    user_id: str
    action_type: str  # APPROVE_TRADE | REJECT_TRADE | EMERGENCY_FLATTEN | PAUSE_AI
    payload: dict[str, Any]
    expires_at: datetime
    is_consumed: bool = False
    consumed_at: datetime | None = None


@dataclass
class DeliveryLogRecord:
    id: str
    notification_id: str
    user_id: str
    channel_type: str
    priority: str  # P0 | P1 | P2 | P3
    status: str    # PENDING | SENT | DELIVERED | FAILED | SUPPRESSED_QUIET_HOURS
    attempt_count: int
    provider_msg_id: str | None = None
    error_message: str | None = None
    dispatched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
