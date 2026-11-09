"""One-time token machinery (T011).

The properties pinned here are the ones email links depend on: a token is stored only as
a hash, is spendable exactly once, expires at its purpose's TTL against the *injected*
clock, cannot cross purpose boundaries, and every failure mode is indistinguishable from
every other — a client that learns "this link was already used" has learned that the link
was real, which is the oracle these tests check for.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from atlas_api.modules.auth.service.one_time_tokens import (
    InMemoryTokenRepository,
    OneTimeTokenError,
    OneTimeTokenService,
    TokenPurpose,
)
from atlas_api.modules.auth.settings import AuthSettings
from atlas_core.timing import FrozenClock

T0 = datetime(2026, 9, 7, 12, 0, 0, tzinfo=UTC)


def _service(
    **overrides: object,
) -> tuple[OneTimeTokenService, InMemoryTokenRepository, FrozenClock]:
    repo = InMemoryTokenRepository()
    clock = FrozenClock(T0)
    settings = AuthSettings(**overrides)  # type: ignore[arg-type]
    return OneTimeTokenService(repo=repo, settings=settings, clock=clock), repo, clock


def test_issue_returns_raw_token_and_consume_recovers_user() -> None:
    svc, _, _ = _service()
    issued = svc.issue(user_id="user-1", purpose=TokenPurpose.EMAIL_VERIFY)
    consumed = svc.consume(issued.raw_token, purpose=TokenPurpose.EMAIL_VERIFY)
    assert consumed.user_id == "user-1"
    assert consumed.purpose is TokenPurpose.EMAIL_VERIFY


def test_only_the_hash_is_stored() -> None:
    """A leaked table must not contain usable links."""
    svc, repo, _ = _service()
    issued = svc.issue(user_id="u", purpose=TokenPurpose.PASSWORD_RESET)
    assert issued.raw_token not in repr(repo._by_hash)
    stored = next(iter(repo._by_hash.values()))
    assert stored.token_hash == hashlib.sha256(issued.raw_token.encode()).digest()


def test_token_is_single_use() -> None:
    svc, _, _ = _service()
    issued = svc.issue(user_id="u", purpose=TokenPurpose.MAGIC_LINK)
    svc.consume(issued.raw_token, purpose=TokenPurpose.MAGIC_LINK)
    with pytest.raises(OneTimeTokenError):
        svc.consume(issued.raw_token, purpose=TokenPurpose.MAGIC_LINK)


def test_expiry_follows_purpose_policy_at_clock_boundary() -> None:
    svc, _, clock = _service()
    issued = svc.issue(user_id="u", purpose=TokenPurpose.MAGIC_LINK)  # 15 min default
    ttl = AuthSettings().magic_link_ttl_minutes * 60

    clock.advance(ttl - 1)
    svc.consume(issued.raw_token, purpose=TokenPurpose.MAGIC_LINK)  # still valid

    # Fresh token, then cross the boundary.
    issued2 = svc.issue(user_id="u", purpose=TokenPurpose.MAGIC_LINK)
    clock.advance(ttl + 1)
    with pytest.raises(OneTimeTokenError):
        svc.consume(issued2.raw_token, purpose=TokenPurpose.MAGIC_LINK)


def test_purpose_ttls_are_configurable_and_distinct() -> None:
    svc, _, _ = _service(
        email_verify_ttl_hours=24, password_reset_ttl_minutes=30, magic_link_ttl_minutes=15
    )
    assert svc.ttl_for(TokenPurpose.EMAIL_VERIFY) == timedelta(hours=24)
    assert svc.ttl_for(TokenPurpose.PASSWORD_RESET) == timedelta(minutes=30)
    assert svc.ttl_for(TokenPurpose.MAGIC_LINK) == timedelta(minutes=15)


def test_token_cannot_cross_purpose() -> None:
    """A password-reset link presented to the email-verify route fails."""
    svc, _, _ = _service()
    issued = svc.issue(user_id="u", purpose=TokenPurpose.PASSWORD_RESET)
    with pytest.raises(OneTimeTokenError):
        svc.consume(issued.raw_token, purpose=TokenPurpose.EMAIL_VERIFY)


def test_reissue_invalidates_previous_same_purpose_only() -> None:
    svc, _, _ = _service()
    first = svc.issue(user_id="u", purpose=TokenPurpose.PASSWORD_RESET)
    other = svc.issue(user_id="u", purpose=TokenPurpose.EMAIL_VERIFY)
    second = svc.issue(user_id="u", purpose=TokenPurpose.PASSWORD_RESET)

    with pytest.raises(OneTimeTokenError):
        svc.consume(first.raw_token, purpose=TokenPurpose.PASSWORD_RESET)
    # The unrelated purpose survives.
    svc.consume(other.raw_token, purpose=TokenPurpose.EMAIL_VERIFY)
    svc.consume(second.raw_token, purpose=TokenPurpose.PASSWORD_RESET)


def test_reissue_for_another_user_does_not_invalidate() -> None:
    svc, _, _ = _service()
    mine = svc.issue(user_id="alice", purpose=TokenPurpose.PASSWORD_RESET)
    svc.issue(user_id="bob", purpose=TokenPurpose.PASSWORD_RESET)
    svc.consume(mine.raw_token, purpose=TokenPurpose.PASSWORD_RESET)


def test_unknown_token_rejected() -> None:
    svc, _, _ = _service()
    with pytest.raises(OneTimeTokenError):
        svc.consume("never-issued", purpose=TokenPurpose.EMAIL_VERIFY)


def test_all_failure_modes_are_indistinguishable() -> None:
    """Unknown, expired, used, wrong-purpose: same exception, same message.

    If these ever diverge, the consume endpoint leaks token state to whoever holds a
    candidate token — the enumeration rule (FR-005) applied to links.
    """
    svc, _, clock = _service()
    unknown = "never-issued"

    expired = svc.issue(user_id="u", purpose=TokenPurpose.MAGIC_LINK)
    clock.advance(AuthSettings().magic_link_ttl_minutes * 60 + 1)

    spent = svc.issue(user_id="u", purpose=TokenPurpose.MAGIC_LINK)
    clock.set(T0)
    svc.consume(spent.raw_token, purpose=TokenPurpose.MAGIC_LINK)

    cross = svc.issue(user_id="u", purpose=TokenPurpose.PASSWORD_RESET)

    cases = [
        (unknown, TokenPurpose.EMAIL_VERIFY),
        (expired.raw_token, TokenPurpose.MAGIC_LINK),
        (spent.raw_token, TokenPurpose.MAGIC_LINK),
        (cross.raw_token, TokenPurpose.EMAIL_VERIFY),
    ]
    messages = set()
    for raw, purpose in cases:
        with pytest.raises(OneTimeTokenError) as exc_info:
            svc.consume(raw, purpose=purpose)
        messages.add(str(exc_info.value))
    assert len(messages) == 1


def test_tokens_are_urlsafe_and_high_entropy() -> None:
    svc, _, _ = _service()
    issued = svc.issue(user_id="u", purpose=TokenPurpose.EMAIL_VERIFY)
    assert issued.raw_token.replace("-", "").replace("_", "").isalnum()
    ids = {svc.issue(user_id="u", purpose=TokenPurpose.EMAIL_VERIFY).raw_token for _ in range(50)}
    assert len(ids) == 50  # no collisions across reissues


def test_context_is_stored_for_audit() -> None:
    """Issue-time ip/ua rides the row so a later anomaly review can reconstruct it."""
    svc, repo, _ = _service()
    issued = svc.issue(user_id="u", purpose=TokenPurpose.PASSWORD_RESET, context={"ip": "1.2.3.4"})
    stored = repo._by_hash[hashlib.sha256(issued.raw_token.encode()).digest()]
    assert stored.context["ip"] == "1.2.3.4"
