"""Unit tests for single-use action tokens and chat command parsing (Spec 08 §2, §4)."""

from datetime import datetime, timedelta, timezone
import pytest
from atlas_api.modules.communication.domain.commands import parse_chat_command
from atlas_api.modules.communication.domain.tokens import (
    consume_action_token,
    generate_action_token,
)
from atlas_core.errors import ValidationError


def test_action_token_lifecycle():
    raw_token, record = generate_action_token(
        user_id="trader-1",
        action_type="APPROVE_TRADE",
        payload={"proposal_id": "prop-123"},
        ttl_seconds=300,
    )
    assert len(record.token_hash) == 64
    assert record.is_consumed is False

    # Consume token
    consume_action_token(record)
    assert record.is_consumed is True
    assert record.consumed_at is not None

    # Replay attack prevention
    with pytest.raises(ValidationError, match="already been consumed"):
        consume_action_token(record)


def test_action_token_expiry():
    _, record = generate_action_token(
        user_id="trader-1",
        action_type="APPROVE_TRADE",
        payload={},
        ttl_seconds=1,
    )
    # Fast-forward expiry
    record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=10)

    with pytest.raises(ValidationError, match="expired"):
        consume_action_token(record)


def test_parse_chat_command():
    assert parse_chat_command("/status") == ("STATUS", None)
    assert parse_chat_command("status") == ("STATUS", None)
    assert parse_chat_command("/analyze SOL/USDT") == ("ANALYZE", "SOL/USDT")
    assert parse_chat_command("/pause") == ("PAUSE", None)
    assert parse_chat_command("/resume") == ("RESUME", None)
    assert parse_chat_command("/close EUR/USD") == ("CLOSE", "EUR/USD")
    assert parse_chat_command("/close") == ("CLOSE", "ALL")
    assert parse_chat_command("/report") == ("REPORT", None)
