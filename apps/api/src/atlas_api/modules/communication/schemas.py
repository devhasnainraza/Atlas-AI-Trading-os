"""Pydantic schemas for Communication Platform API (Spec 08 §2, §9)."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class RegisterChannelRequest(BaseModel):
    channel_type: str = Field(..., description="TELEGRAM | DISCORD | SLACK | WHATSAPP | SMS | EMAIL | WEB_PUSH")
    destination: str = Field(..., description="Webhook URL, chat ID, phone number, or email")
    min_priority: str = Field(default="P1", description="P0 | P1 | P2 | P3")


class CommunicationChannelResponse(BaseModel):
    id: str
    user_id: str
    channel_type: str
    destination_masked: str
    is_verified: bool
    is_enabled: bool
    min_priority: str
    created_at: str


class UpdatePreferencesRequest(BaseModel):
    quiet_hours_enabled: bool = Field(default=False)
    quiet_hours_start: str = Field(default="22:00:00")
    quiet_hours_end: str = Field(default="06:30:00")
    timezone: str = Field(default="UTC")
    emergency_phone: str | None = Field(default=None)
    digest_frequency: str = Field(default="REALTIME")


class CommunicationPreferencesResponse(BaseModel):
    user_id: str
    quiet_hours_enabled: bool
    quiet_hours_start: str
    quiet_hours_end: str
    timezone: str
    emergency_phone: str | None
    digest_frequency: str


class DispatchNotificationRequest(BaseModel):
    priority: str = Field(default="P1", description="P0 | P1 | P2 | P3")
    title: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)
    action_type: str | None = Field(default=None, description="APPROVE_TRADE | REJECT_TRADE | EMERGENCY_FLATTEN | PAUSE_AI")
    action_payload: dict[str, Any] = Field(default_factory=dict)


class DispatchNotificationResponse(BaseModel):
    notification_id: str
    channels_dispatched: list[str]
    status: str
    action_token: str | None = None
    action_url: str | None = None


class ExecuteActionResponse(BaseModel):
    status: str
    action_type: str
    payload: dict[str, Any]
    message: str


class InboundWebhookRequest(BaseModel):
    channel_type: str = Field(default="TELEGRAM")
    raw_text: str = Field(..., description="Text message received in chat")
    sender_id: str = Field(default="trader-user-001")


class InboundWebhookResponse(BaseModel):
    command: str
    response_text: str
