"""HMAC-SHA256 single-use ephemeral action token manager (Spec 08 §2, §4)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Any
import uuid

from atlas_api.modules.communication.domain.models import ActionTokenRecord
from atlas_core.errors import ValidationError


def generate_action_token(
    user_id: str,
    action_type: str,
    payload: dict[str, Any],
    ttl_seconds: int = 300,
) -> tuple[str, ActionTokenRecord]:
    """Generates an ephemeral, single-use action token with a default 5-minute TTL."""
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=ttl_seconds)

    record = ActionTokenRecord(
        id=str(uuid.uuid4()),
        token_hash=token_hash,
        user_id=user_id,
        action_type=action_type.upper(),
        payload=payload,
        expires_at=expires_at,
        is_consumed=False,
        consumed_at=None,
    )
    return raw_token, record


def consume_action_token(record: ActionTokenRecord) -> None:
    """Validates and atomically consumes the action token, raising error on replay or expiry."""
    now = datetime.now(timezone.utc)

    if record.is_consumed:
        raise ValidationError("Action token has already been consumed and cannot be replayed")

    if record.expires_at < now:
        raise ValidationError("Action token has expired (> 5 minutes elapsed)")

    record.is_consumed = True
    record.consumed_at = now
