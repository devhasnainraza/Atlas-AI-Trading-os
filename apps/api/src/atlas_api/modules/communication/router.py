"""Communication Platform API router and endpoints (Spec 08 §2, §9)."""

from __future__ import annotations

from dataclasses import dataclass
from fastapi import APIRouter, Depends, Path, Request

from atlas_api.modules.communication.domain.models import (
    CommunicationChannel,
    CommunicationPreferences,
)
from atlas_api.modules.communication.schemas import (
    CommunicationChannelResponse,
    CommunicationPreferencesResponse,
    DispatchNotificationRequest,
    DispatchNotificationResponse,
    ExecuteActionResponse,
    InboundWebhookRequest,
    InboundWebhookResponse,
    RegisterChannelRequest,
    UpdatePreferencesRequest,
)
from atlas_api.modules.communication.service import CommunicationService
from atlas_core.errors import InternalError

router = APIRouter(prefix="/communication", tags=["communication"])

STATE_KEY = "communication_context"


@dataclass(frozen=True)
class CommunicationModuleContext:
    service: CommunicationService


def get_communication_context(request: Request) -> CommunicationModuleContext:
    context = getattr(request.app.state, STATE_KEY, None)
    if not isinstance(context, CommunicationModuleContext):
        raise InternalError(
            internal_context={"detail": "communication module accessed before composition"}
        )
    return context


def get_communication_service(
    context: CommunicationModuleContext = Depends(get_communication_context),
) -> CommunicationService:
    return context.service


def _format_channel(channel: CommunicationChannel) -> CommunicationChannelResponse:
    return CommunicationChannelResponse(
        id=channel.id,
        user_id=channel.user_id,
        channel_type=channel.channel_type,
        destination_masked=channel.destination_masked,
        is_verified=channel.is_verified,
        is_enabled=channel.is_enabled,
        min_priority=channel.min_priority,
        created_at=channel.created_at.isoformat(),
    )


@router.post("/channels", response_model=CommunicationChannelResponse)
async def register_channel(
    body: RegisterChannelRequest,
    request: Request,
    service: CommunicationService = Depends(get_communication_service),
) -> CommunicationChannelResponse:
    """Registers an outbound communication channel (Telegram, Discord, Slack, etc.)."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    channel = service.register_channel(
        user_id=user_id,
        channel_type=body.channel_type,
        destination=body.destination,
        min_priority=body.min_priority,
    )
    return _format_channel(channel)


@router.get("/channels", response_model=list[CommunicationChannelResponse])
async def list_channels(
    request: Request,
    service: CommunicationService = Depends(get_communication_service),
) -> list[CommunicationChannelResponse]:
    """Lists registered notification channels for the current user."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    channels = service.get_channels(user_id=user_id)
    return [_format_channel(c) for c in channels]


@router.delete("/channels/{channel_id}")
async def delete_channel(
    channel_id: str = Path(..., description="Channel UUID"),
    request: Request = ...,
    service: CommunicationService = Depends(get_communication_service),
) -> dict[str, str]:
    """Removes a registered communication channel."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    service.delete_channel(channel_id=channel_id, user_id=user_id)
    return {"status": "DELETED", "id": channel_id}


@router.get("/preferences", response_model=CommunicationPreferencesResponse)
async def get_preferences(
    request: Request,
    service: CommunicationService = Depends(get_communication_service),
) -> CommunicationPreferencesResponse:
    """Returns user quiet hours and digest preferences."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    prefs = service.get_preferences(user_id=user_id)
    return CommunicationPreferencesResponse(
        user_id=prefs.user_id,
        quiet_hours_enabled=prefs.quiet_hours_enabled,
        quiet_hours_start=prefs.quiet_hours_start,
        quiet_hours_end=prefs.quiet_hours_end,
        timezone=prefs.timezone,
        emergency_phone=prefs.emergency_phone,
        digest_frequency=prefs.digest_frequency,
    )


@router.put("/preferences", response_model=CommunicationPreferencesResponse)
async def update_preferences(
    body: UpdatePreferencesRequest,
    request: Request,
    service: CommunicationService = Depends(get_communication_service),
) -> CommunicationPreferencesResponse:
    """Updates user quiet hours and notification routing preferences."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    prefs = service.update_preferences(
        user_id=user_id,
        quiet_hours_enabled=body.quiet_hours_enabled,
        quiet_hours_start=body.quiet_hours_start,
        quiet_hours_end=body.quiet_hours_end,
        timezone=body.timezone,
        emergency_phone=body.emergency_phone,
        digest_frequency=body.digest_frequency,
    )
    return CommunicationPreferencesResponse(
        user_id=prefs.user_id,
        quiet_hours_enabled=prefs.quiet_hours_enabled,
        quiet_hours_start=prefs.quiet_hours_start,
        quiet_hours_end=prefs.quiet_hours_end,
        timezone=prefs.timezone,
        emergency_phone=prefs.emergency_phone,
        digest_frequency=prefs.digest_frequency,
    )


@router.post("/dispatch", response_model=DispatchNotificationResponse)
async def dispatch_notification(
    body: DispatchNotificationRequest,
    request: Request,
    service: CommunicationService = Depends(get_communication_service),
) -> DispatchNotificationResponse:
    """Dispatches a priority-tiered notification across configured user channels."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    n_id, channels, status, token, url = service.dispatch_notification(
        user_id=user_id,
        priority=body.priority,
        title=body.title,
        body=body.body,
        action_type=body.action_type,
        action_payload=body.action_payload,
    )
    return DispatchNotificationResponse(
        notification_id=n_id,
        channels_dispatched=channels,
        status=status,
        action_token=token,
        action_url=url,
    )


@router.post("/actions/{token_hash}/execute", response_model=ExecuteActionResponse)
async def execute_action_token(
    token_hash: str = Path(..., description="Action token SHA-256 hash"),
    service: CommunicationService = Depends(get_communication_service),
) -> ExecuteActionResponse:
    """Atomically consumes single-use action token (1-click trade approval from chat)."""
    action_type, payload, message = service.execute_action(token_hash=token_hash)
    return ExecuteActionResponse(
        status="EXECUTED",
        action_type=action_type,
        payload=payload,
        message=message,
    )


@router.post("/webhooks/telegram", response_model=InboundWebhookResponse)
async def inbound_telegram_webhook(
    body: InboundWebhookRequest,
    request: Request,
    service: CommunicationService = Depends(get_communication_service),
) -> InboundWebhookResponse:
    """Receives and executes slash commands from Telegram bots."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else body.sender_id

    cmd, reply = service.handle_inbound_chat(
        user_id=user_id,
        channel_type="TELEGRAM",
        raw_text=body.raw_text,
    )
    return InboundWebhookResponse(command=cmd, response_text=reply)


@router.post("/webhooks/discord", response_model=InboundWebhookResponse)
async def inbound_discord_webhook(
    body: InboundWebhookRequest,
    request: Request,
    service: CommunicationService = Depends(get_communication_service),
) -> InboundWebhookResponse:
    """Receives and executes slash commands from Discord bot webhooks."""
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else body.sender_id

    cmd, reply = service.handle_inbound_chat(
        user_id=user_id,
        channel_type="DISCORD",
        raw_text=body.raw_text,
    )
    return InboundWebhookResponse(command=cmd, response_text=reply)
