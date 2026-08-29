"""T028 — credential material cannot reach a client, a log, or an event (FR-008).

Two layers are asserted here: that :class:`CredentialSecret` refuses to render itself, and
that the redaction pass scrubs venue traffic before it is stored. Both matter because venue
payloads carry keys in predictable places, and a redaction applied only at display time is one
forgotten code path away from a live API key in a log aggregator.

The checklist entry this backs: "Credential material is out of reach of every client, role,
log, and export."
"""

from __future__ import annotations

import logging
from typing import Any

import pytest

from atlas_venues.credentials import (
    CredentialError,
    CredentialSecret,
    InMemoryCredentialProvider,
    set_credential_provider,
    use_credential,
)
from atlas_venues.redaction import (
    REDACTED,
    contains_secret_marker,
    is_sensitive_key,
    redact,
    redact_headers,
    redact_text,
    redact_url,
)

LIVE_KEY = "vT8sQ2mPx7RkL0nZaC4eW9uY6bH3jF1dG5oI"
LIVE_SIG = "a" * 64


class TestCredentialSecretNeverRenders:
    def test_repr_is_redacted(self) -> None:
        secret = CredentialSecret("cred-1", {"api_key": LIVE_KEY})
        assert LIVE_KEY not in repr(secret)
        assert "[REDACTED]" in repr(secret)

    def test_str_is_redacted(self) -> None:
        secret = CredentialSecret("cred-1", {"api_key": LIVE_KEY})
        assert LIVE_KEY not in str(secret)

    def test_fstring_interpolation_is_redacted(self) -> None:
        """The most likely accidental disclosure: an f-string in a log line."""
        secret = CredentialSecret("cred-1", {"api_key": LIVE_KEY})
        assert LIVE_KEY not in f"submitting with {secret}"
        assert LIVE_KEY not in "{}".format(secret)  # noqa: UP032 - explicitly testing .format
        assert LIVE_KEY not in f"{secret!r}"

    def test_logging_a_secret_does_not_leak_it(self, caplog: pytest.LogCaptureFixture) -> None:
        secret = CredentialSecret("cred-1", {"api_key": LIVE_KEY})
        with caplog.at_level(logging.INFO):
            logging.getLogger("atlas.test").info("using %s", secret)
        assert LIVE_KEY not in caplog.text

    def test_reveal_is_the_only_disclosure_point(self) -> None:
        """Explicit and greppable — every real disclosure is one search away."""
        secret = CredentialSecret("cred-1", {"api_key": LIVE_KEY})
        assert secret.reveal("api_key") == LIVE_KEY

    def test_reveal_of_an_unknown_field_raises(self) -> None:
        secret = CredentialSecret("cred-1", {"api_key": LIVE_KEY})
        with pytest.raises(CredentialError, match="has no field"):
            secret.reveal("secret_key")


class TestCredentialAccessIsScopedAndAudited:
    async def test_access_requires_a_purpose(self) -> None:
        provider = InMemoryCredentialProvider()
        provider.put("cred-1", {"api_key": LIVE_KEY})
        set_credential_provider(provider)
        with pytest.raises(CredentialError, match="purpose is required"):
            async with use_credential("cred-1", purpose=""):
                pass

    async def test_every_access_is_recorded_with_its_purpose(self) -> None:
        provider = InMemoryCredentialProvider()
        provider.put("cred-1", {"api_key": LIVE_KEY})
        set_credential_provider(provider)
        async with use_credential("cred-1", purpose="submit_order") as secret:
            assert secret.reveal("api_key") == LIVE_KEY
        log = provider.access_log()
        assert len(log) == 1
        assert log[0].purpose == "submit_order"
        assert log[0].credential_id == "cred-1"

    async def test_the_audit_log_never_stores_the_material(self) -> None:
        provider = InMemoryCredentialProvider()
        provider.put("cred-1", {"api_key": LIVE_KEY})
        set_credential_provider(provider)
        async with use_credential("cred-1", purpose="verify_permissions"):
            pass
        assert LIVE_KEY not in repr(provider.access_log())

    async def test_revoked_credentials_are_refused(self) -> None:
        """FR-011: revocation takes effect at the next use, not at the next restart."""
        provider = InMemoryCredentialProvider()
        provider.put("cred-1", {"api_key": LIVE_KEY})
        set_credential_provider(provider)
        provider.revoke("cred-1")
        with pytest.raises(CredentialError, match="revoked"):
            async with use_credential("cred-1", purpose="submit_order"):
                pass

    async def test_unknown_credential_is_refused(self) -> None:
        set_credential_provider(InMemoryCredentialProvider())
        with pytest.raises(CredentialError, match="unknown credential"):
            async with use_credential("nope", purpose="submit_order"):
                pass


class TestRedaction:
    @pytest.mark.parametrize(
        "key",
        [
            "password",
            "api_key",
            "apiKey",
            "X-MBX-APIKEY",
            "Authorization",
            "signature",
            "secret_key",
            "refresh_token",
            "passphrase",
            "session_id",
            "Cookie",
        ],
    )
    def test_sensitive_keys_are_recognised(self, key: str) -> None:
        assert is_sensitive_key(key)

    @pytest.mark.parametrize("key", ["symbol", "quantity", "price", "order_id", "venue_code"])
    def test_ordinary_keys_are_left_alone(self, key: str) -> None:
        assert not is_sensitive_key(key)

    def test_nested_payloads_are_scrubbed(self) -> None:
        payload: dict[str, Any] = {
            "order": {"symbol": "BTCUSDT", "quantity": "0.5"},
            "auth": {"api_key": LIVE_KEY, "signature": LIVE_SIG},
            "headers": [{"Authorization": f"Bearer {LIVE_KEY}"}],
        }
        cleaned = redact(payload)
        assert LIVE_KEY not in str(cleaned)
        assert LIVE_SIG not in str(cleaned)
        assert cleaned["order"]["symbol"] == "BTCUSDT", "redaction must not destroy the audit value"

    def test_headers_are_scrubbed(self) -> None:
        cleaned = redact_headers({"X-MBX-APIKEY": LIVE_KEY, "Content-Type": "application/json"})
        assert cleaned["X-MBX-APIKEY"] == REDACTED
        assert cleaned["Content-Type"] == "application/json"

    def test_query_string_credentials_are_scrubbed_but_the_url_survives(self) -> None:
        url = f"https://api.binance.com/api/v3/order?symbol=BTCUSDT&signature={LIVE_SIG}"
        cleaned = redact_url(url)
        assert LIVE_SIG not in cleaned
        assert "symbol=BTCUSDT" in cleaned, "support needs the non-secret parameters"

    def test_bearer_tokens_in_free_text_are_scrubbed(self) -> None:
        assert LIVE_KEY not in redact_text(f"rejected: Bearer {LIVE_KEY} is invalid")

    def test_bytes_are_never_passed_through(self) -> None:
        assert redact({"body": b"secret bytes"})["body"] == REDACTED

    def test_deep_payloads_terminate(self) -> None:
        """A pathological payload must be dropped, not half-scrubbed or hung on."""
        deep: dict[str, Any] = {"k": "v"}
        for _ in range(50):
            deep = {"nested": deep, "api_key": LIVE_KEY}
        cleaned = redact(deep)
        assert LIVE_KEY not in str(cleaned)

    def test_contains_secret_marker_detects_unscrubbed_payloads(self) -> None:
        assert contains_secret_marker({"signature": LIVE_SIG})
        assert not contains_secret_marker({"symbol": "BTCUSDT", "quantity": "0.5"})


class TestAdaptersDoNotCacheCredentials:
    """FR-008: material is borrowed per operation, never held on the instance."""

    def test_paper_adapter_holds_no_credential_state(self, paper_adapter: object) -> None:
        for name, value in vars(paper_adapter).items():
            assert not isinstance(value, CredentialSecret), f"{name} caches a CredentialSecret"
            assert not is_sensitive_key(name), f"{name} looks like cached credential state"
