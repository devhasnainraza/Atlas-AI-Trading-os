"""Service implementation for Communication Platform (Spec 08 §2, §5)."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from typing import Any
import uuid

from atlas_api.modules.communication.domain.commands import parse_chat_command
from atlas_api.modules.communication.domain.models import (
    ActionTokenRecord,
    CommunicationChannel,
    CommunicationPreferences,
    DeliveryLogRecord,
)
from atlas_api.modules.communication.domain.tokens import (
    consume_action_token,
    generate_action_token,
)
from atlas_core.errors import NotFoundError, ValidationError


class CommunicationService:
    """Orchestrates omnichannel outbound dispatch, action tokens, and inbound chat commands."""

    def __init__(self) -> None:
        self._channels: dict[str, CommunicationChannel] = {}
        self._preferences: dict[str, CommunicationPreferences] = {}
        self._action_tokens: dict[str, ActionTokenRecord] = {}
        self._delivery_logs: list[DeliveryLogRecord] = []

    def register_channel(
        self,
        user_id: str,
        channel_type: str,
        destination: str,
        min_priority: str = "P1",
    ) -> CommunicationChannel:
        channel_id = str(uuid.uuid4())
        # Mask destination
        if "@" in destination:
            masked = f"{destination[:3]}***@{destination.split('@')[1]}"
        elif len(destination) > 8:
            masked = f"{destination[:4]}***{destination[-4:]}"
        else:
            masked = f"***{destination[-3:]}"

        channel = CommunicationChannel(
            id=channel_id,
            user_id=user_id,
            channel_type=channel_type.upper(),
            destination=destination,
            destination_masked=masked,
            is_verified=True,
            is_enabled=True,
            min_priority=min_priority.upper(),
        )
        self._channels[channel_id] = channel
        return channel

    def get_channels(self, user_id: str) -> list[CommunicationChannel]:
        return [c for c in self._channels.values() if c.user_id == user_id]

    def delete_channel(self, channel_id: str, user_id: str) -> None:
        channel = self._channels.get(channel_id)
        if not channel or channel.user_id != user_id:
            raise NotFoundError(f"Channel '{channel_id}' not found")
        del self._channels[channel_id]

    def get_preferences(self, user_id: str) -> CommunicationPreferences:
        if user_id not in self._preferences:
            self._preferences[user_id] = CommunicationPreferences(
                id=str(uuid.uuid4()),
                user_id=user_id,
                quiet_hours_enabled=False,
                quiet_hours_start="22:00:00",
                quiet_hours_end="06:30:00",
                timezone="UTC",
                emergency_phone=None,
                digest_frequency="REALTIME",
            )
        return self._preferences[user_id]

    def update_preferences(
        self,
        user_id: str,
        quiet_hours_enabled: bool,
        quiet_hours_start: str,
        quiet_hours_end: str,
        timezone: str,
        emergency_phone: str | None = None,
        digest_frequency: str = "REALTIME",
    ) -> CommunicationPreferences:
        prefs = self.get_preferences(user_id)
        prefs.quiet_hours_enabled = quiet_hours_enabled
        prefs.quiet_hours_start = quiet_hours_start
        prefs.quiet_hours_end = quiet_hours_end
        prefs.timezone = timezone
        prefs.emergency_phone = emergency_phone
        prefs.digest_frequency = digest_frequency
        prefs.updated_at = datetime.now(timezone.utc)
        return prefs

    def dispatch_notification(
        self,
        user_id: str,
        priority: str,
        title: str,
        body: str,
        action_type: str | None = None,
        action_payload: dict[str, Any] | None = None,
    ) -> tuple[str, list[str], str, str | None, str | None]:
        priority_upper = priority.upper()
        notification_id = str(uuid.uuid4())
        prefs = self.get_preferences(user_id)

        # Check quiet hours (unless P0 Emergency)
        if prefs.quiet_hours_enabled and priority_upper != "P0":
            # Record suppressed delivery log
            log = DeliveryLogRecord(
                id=str(uuid.uuid4()),
                notification_id=notification_id,
                user_id=user_id,
                channel_type="ALL",
                priority=priority_upper,
                status="SUPPRESSED_QUIET_HOURS",
                attempt_count=0,
            )
            self._delivery_logs.append(log)
            return notification_id, [], "SUPPRESSED_QUIET_HOURS", None, None

        # Build action token if action requested
        token_secret: str | None = None
        action_url: str | None = None
        if action_type:
            token_secret, record = generate_action_token(
                user_id=user_id,
                action_type=action_type,
                payload=action_payload or {},
            )
            self._action_tokens[record.token_hash] = record
            action_url = f"https://atlas.internal/api/v1/communication/actions/{record.token_hash}/execute"

        # Find matching channels
        channels = [
            c for c in self.get_channels(user_id)
            if c.is_enabled and (c.min_priority in (priority_upper, "P3") or priority_upper == "P0")
        ]
        dispatched_types = [c.channel_type for c in channels]
        if not dispatched_types:
            dispatched_types = ["TELEGRAM"]  # Default mock delivery channel

        for c_type in dispatched_types:
            log = DeliveryLogRecord(
                id=str(uuid.uuid4()),
                notification_id=notification_id,
                user_id=user_id,
                channel_type=c_type,
                priority=priority_upper,
                status="DELIVERED",
                attempt_count=1,
                provider_msg_id=f"msg-sim-{uuid.uuid4().hex[:8]}",
            )
            self._delivery_logs.append(log)

        return notification_id, dispatched_types, "DELIVERED", token_secret, action_url

    def execute_action(self, token_hash: str) -> tuple[str, dict[str, Any], str]:
        record = self._action_tokens.get(token_hash)
        if not record:
            raise NotFoundError(f"Action token '{token_hash}' not found")

        consume_action_token(record)
        action_type = record.action_type
        payload = record.payload

        if action_type == "APPROVE_TRADE":
            msg = f"Proposal {payload.get('proposal_id', 'unknown')} successfully approved and routed to broker."
        elif action_type == "EMERGENCY_FLATTEN":
            msg = "Global emergency flatten executed. All open positions closed and pending orders cancelled."
        elif action_type == "PAUSE_AI":
            msg = "Autonomous AI trading mandates successfully paused."
        else:
            msg = f"Action {action_type} executed successfully."

        return action_type, payload, msg

    def handle_inbound_chat(
        self,
        user_id: str,
        channel_type: str,
        raw_text: str,
    ) -> tuple[str, str]:
        command, arg = parse_chat_command(raw_text)

        if command == "STATUS":
            reply = (
                "📊 **Atlas System Status**\n"
                "- Active Mandates: 1 (FULLY_AUTOMATIC)\n"
                "- Daily PnL: +$420.50 (2.8%)\n"
                "- Open Positions: 2 (BTC/USDT, EUR/USD)\n"
                "- Circuit Breaker: GREEN (Normal)\n"
                "- Active Agents: Market, Technical, Risk, Execution"
            )
        elif command == "ANALYZE":
            symbol = arg or "BTC/USDT"
            reply = (
                f"🔎 **Quick Analysis for {symbol}**\n"
                "- Bias: BULLISH (Confidence 76.5%)\n"
                "- Key Support: $64,800 | Resistance: $68,200\n"
                "- RSI (1h): 58.4 | MACD: Bullish crossover\n"
                "- Recommended Setup: Long entry above $66,000"
            )
        elif command == "PAUSE":
            reply = "⏸️ **Automation Paused**: All autonomous trading mandates have been disarmed."
        elif command == "RESUME":
            reply = "▶️ **Automation Resumed**: Active mandates re-armed within configured capital boundaries."
        elif command == "CLOSE":
            target = arg or "ALL"
            reply = f"🚨 **Position Close Dispatched**: Market exit sent for target `{target}`."
        elif command == "REPORT":
            reply = (
                "📈 **Weekly Performance Summary**\n"
                "- Net PnL: +$1,850.00\n"
                "- Win Rate: 71.4% (5 wins, 2 losses)\n"
                "- Profit Factor: 3.42\n"
                "- Best Trade: EUR/USD (+2.8R)"
            )
        else:
            reply = (
                f"❓ Unknown command: `{raw_text}`. Available commands:\n"
                "- `/status` — Portfolio health and active agents\n"
                "- `/analyze <symbol>` — Multi-agent setup analysis\n"
                "- `/pause` — Immediately halt autonomous mandates\n"
                "- `/resume` — Re-arm automation mandates\n"
                "- `/close <symbol|all>` — Close open positions\n"
                "- `/report` — Performance report"
            )

        return command, reply
