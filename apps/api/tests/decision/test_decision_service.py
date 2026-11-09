"""Unit tests for DecisionService and dialectic AI debate (Spec 05 §2, §5)."""

from decimal import Decimal
import pytest
from atlas_api.modules.decision.service import DecisionService
from atlas_core.errors import NotFoundError, ValidationError


@pytest.mark.asyncio
async def test_evaluate_setup_long_pipeline():
    service = DecisionService()
    record = await service.evaluate_setup(
        user_id="trader-1",
        symbol="BTC/USDT",
        direction="LONG",
        timeframe="1h",
        entry_price=Decimal("67200.00"),
        stop_loss_price=Decimal("66400.00"),
    )

    assert record.symbol == "BTC/USDT"
    assert record.direction == "LONG"
    assert record.confidence_score == Decimal("78.50")
    assert record.status == "PENDING_APPROVAL"
    assert record.calculated_position_size > Decimal("0")
    assert record.risk_reward_ratio >= Decimal("1.50")
    assert len(record.proposal_hash) == 64  # SHA-256 string
    assert len(record.debate_transcript.bull_arguments) > 0
    assert len(record.debate_transcript.bear_arguments) > 0
    assert "Arbitrator verdict" in record.debate_transcript.arbitrator_synthesis


@pytest.mark.asyncio
async def test_evaluate_setup_short_pipeline():
    service = DecisionService()
    record = await service.evaluate_setup(
        user_id="trader-1",
        symbol="EUR/USD",
        direction="SHORT",
        timeframe="4h",
        entry_price=Decimal("1.0850"),
        stop_loss_price=Decimal("1.0900"),
    )

    assert record.symbol == "EUR/USD"
    assert record.direction == "SHORT"
    assert record.status == "PENDING_APPROVAL"


@pytest.mark.asyncio
async def test_proposal_approval_and_rejection_lifecycle():
    service = DecisionService()
    
    # Create proposal
    record = await service.evaluate_setup(
        user_id="trader-2",
        symbol="SOL/USDT",
        direction="BUY",
    )
    prop_id = record.id

    # Pending check
    pending = await service.get_pending_proposals(user_id="trader-2")
    assert len(pending) == 1
    assert pending[0].id == prop_id

    # Approve
    approved = await service.approve_proposal(
        proposal_id=prop_id,
        user_id="trader-2",
        signature_token="sig-human-approved",
    )
    assert approved.status == "APPROVED"
    assert approved.resolved_at is not None

    # Should no longer be in pending
    pending_after = await service.get_pending_proposals(user_id="trader-2")
    assert len(pending_after) == 0

    # Cannot approve again
    with pytest.raises(ValidationError, match="cannot approve"):
        await service.approve_proposal(proposal_id=prop_id, user_id="trader-2")
