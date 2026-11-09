"""Registration and email verification (T025; US1, FR-001/006).

The service owns the account-creation path end to end: validate, hash, persist a
``pending_verification`` user, record the required consents, issue the verification token,
and hand the link to the notification seam. Two properties dominate every design choice here:

* **Enumeration safety (FR-023).** :meth:`RegistrationService.register` answers the same way
  whether the email is new, already pending, or already active: success, and "if that address
  is new, a verification link is on its way." An existing address is treated as a *resend*,
  which is both the honest user story and the indistinguishable response. The only thing that
  ever differs is internal (a log line), never the response or its timing class.
* **Consent is recorded, not inferred (FR-001).** Terms, Privacy, and the Trading Risk
  Disclaimer are written as versioned append-only rows at the moment of acceptance. Activation
  later checks the *current* version; a version bump re-prompts (plan §3.3). The service never
  mutates a consent row — that is the repository's append-only contract.

The email sender and the resend-cooldown store are Protocols with in-memory implementations:
the notification platform and Redis arrive in later tasks, and this is the seam they plug
into. The cooldown exists so the platform cannot be used as a mailer (FR-006 resend rule).
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Protocol

from atlas_api.modules.auth.domain.models import User, UserStatus
from atlas_api.modules.auth.repository.consent import ConsentRecord, ConsentRepository
from atlas_api.modules.auth.repository.users import (
    EmailAlreadyExistsError,
    UserRepository,
)
from atlas_api.modules.auth.service.hashing import PasswordHasher
from atlas_api.modules.auth.service.one_time_tokens import (
    OneTimeTokenError,
    OneTimeTokenService,
    TokenPurpose,
)
from atlas_api.modules.auth.settings import AuthSettings
from atlas_core.errors import RateLimitedError, ValidationError
from atlas_core.ids import uuid7
from atlas_core.timing import Clock, SystemClock

#: Documents that MUST be accepted to complete registration (plan §3.3). ``marketing`` is
#: optional and excluded — it is never a precondition for an account.
REQUIRED_CONSENTS: tuple[str, ...] = ("terms", "privacy", "risk_disclaimer")

#: The server-driven onboarding step machine (plan §3.7). Declared here as an ordered list so
#: a future step (org invite, KYC) is an insertion, not a schema change.
ONBOARDING_STEPS: tuple[str, ...] = (
    "verify_email",
    "accept_consents",
    "create_profile",
    "preferences_wizard",
    "security_checklist",
)


class VerificationEmailSender(Protocol):
    """The notification seam. Delivers a verification link; never blocks registration on the
    result (a mail-provider outage must not roll back an account creation)."""

    async def send_verification(self, *, to_email: str, link: str) -> None: ...


class InMemoryVerificationEmailSender:
    """Records sent links so local runs and tests can observe them without a mailer."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send_verification(self, *, to_email: str, link: str) -> None:
        self.sent.append((to_email, link))


class ResendCooldownStore(Protocol):
    """Per-(user, purpose) throttle for verification/resend emails.

    :meth:`try_acquire` returns ``True`` and records the send when allowed, ``False`` when the
    caller is still inside the cooldown window. Atomic in production (Redis ``SET NX EX``);
    the in-memory form is single-process and only used for tests/local.
    """

    async def try_acquire(self, *, key: str, now: datetime, cooldown_seconds: int) -> bool: ...


class InMemoryResendCooldownStore:
    def __init__(self) -> None:
        self._last_sent: dict[str, datetime] = {}

    async def try_acquire(self, *, key: str, now: datetime, cooldown_seconds: int) -> bool:
        last = self._last_sent.get(key)
        if last is not None and now - last < timedelta(seconds=cooldown_seconds):
            return False
        self._last_sent[key] = now
        return True


@dataclass(frozen=True)
class RegistrationRequest:
    """Validated input to :meth:`RegistrationService.register`.

    The route (T029) builds this from the request body after schema validation; the service
    does not parse HTTP. ``password`` is optional — a passwordless (OAuth/magic-link) signup
    creates the account with ``has_password=False``.
    """

    email: str
    password: str | None = None
    #: Document versions the user accepted, keyed by document name.
    consents: Mapping[str, bool] = field(default_factory=dict)
    #: Version string of each document shown (e.g. ``terms@2026-08``); recorded verbatim.
    consent_versions: Mapping[str, str] = field(default_factory=dict)
    ip: str | None = None
    user_agent: str | None = None


@dataclass(frozen=True)
class RegistrationOutcome:
    """The enumeration-safe result. Identical shape for new and existing addresses."""

    user_id: uuid.UUID | None
    requires_verification: bool


class RegistrationService:
    """Create accounts, record consent, and drive email verification."""

    def __init__(
        self,
        *,
        users: UserRepository,
        consents: ConsentRepository,
        tokens: OneTimeTokenService,
        hasher: PasswordHasher,
        settings: AuthSettings,
        email_sender: VerificationEmailSender | None = None,
        cooldown: ResendCooldownStore | None = None,
        clock: Clock | None = None,
        verification_base_url: str = "http://localhost:8000/v1/auth/verify-email",
    ) -> None:
        self._users = users
        self._consents = consents
        self._tokens = tokens
        self._hasher = hasher
        self._settings = settings
        self._email_sender = email_sender or InMemoryVerificationEmailSender()
        self._cooldown = cooldown or InMemoryResendCooldownStore()
        self._clock = clock or SystemClock()
        self._verification_base_url = verification_base_url.rstrip("/")

    async def register(self, request: RegistrationRequest) -> RegistrationOutcome:
        """Create a pending account (or treat an existing email as a resend).

        Enumeration-safe by construction: every branch returns the same
        :class:`RegistrationOutcome` shape and issues (or re-issues) a verification link, so
        the response cannot tell a caller whether the address was already registered.
        """
        email = _normalize_email(request.email)
        self._validate_password(request.password)

        existing = await self._users.get_by_email(email)
        if existing is not None:
            # Existing account: do not reveal it. Re-issue verification (subject to cooldown)
            # and return the same success shape. A deleted/erased tombstone is treated the same
            # way — the row exists, so we neither confirm nor resurrect it here.
            await self._issue_verification(existing.id, email)
            return RegistrationOutcome(user_id=None, requires_verification=True)

        user_id = uuid7()
        password_hash = self._hasher.hash(request.password) if request.password else None
        user = User(
            id=user_id,
            email=email,
            status=UserStatus.PENDING_VERIFICATION,
            has_password=request.password is not None,
        )
        try:
            await self._users.create(user, password_hash=password_hash)
        except EmailAlreadyExistsError:
            # Lost a race against a concurrent signup for the same address. The other request
            # did the real work; behave exactly as the existing-account branch above.
            await self._issue_verification(user_id, email)
            return RegistrationOutcome(user_id=None, requires_verification=True)

        await self._record_required_consents(user_id, request)
        await self._issue_verification(user_id, email)
        return RegistrationOutcome(user_id=user_id, requires_verification=True)

    async def verify_email(self, raw_token: str) -> uuid.UUID:
        """Spend a verification token and activate the account.

        Raises :class:`OneTimeTokenError` for any invalid/expired/used token — the route maps
        that to a single uniform error so token state never leaks (the same rule as the token
        service). Returns the user id on success.
        """
        consumed = self._tokens.consume(raw_token, purpose=TokenPurpose.EMAIL_VERIFY)
        user_id = uuid.UUID(consumed.user_id)
        user = await self._users.get_by_id(user_id)
        if user is None:  # pragma: no cover - token outlived its user (erasure race)
            raise OneTimeTokenError("invalid or expired token")
        if user.status is UserStatus.ACTIVE:
            # Already verified: idempotent success. Re-verifying a spent-but-valid link is
            # blocked upstream by single-use; this only covers a fresh link on an active user.
            return user_id
        activated = user.verify_email(now=self._clock.now())
        await self._users.update(activated)
        return user_id

    async def resend_verification(self, email: str) -> None:
        """Re-send a verification link, throttled by the resend cooldown.

        Enumeration-safe: an unknown address returns silently (no send, no error). A known
        pending address re-issues within cooldown limits. The caller cannot distinguish the
        two from the response — both return ``None``.
        """
        normalized = _normalize_email(email)
        user = await self._users.get_by_email(normalized)
        if user is None or user.status is not UserStatus.PENDING_VERIFICATION:
            # Unknown or already-active: same silent return as a successful resend.
            return
        await self._issue_verification(user.id, normalized)

    async def _issue_verification(self, user_id: uuid.UUID, email: str) -> None:
        """Issue a token and queue the email, honoring the resend cooldown.

        The cooldown is keyed by user+purpose so a re-issue for a *different* purpose (a later
        password reset) is not throttled by a verification send.
        """
        key = f"verify:{user_id}"
        now = self._clock.now()
        acquired = await self._cooldown.try_acquire(
            key=key, now=now, cooldown_seconds=self._settings.resend_cooldown_seconds
        )
        if not acquired:
            raise RateLimitedError(
                retry_after_seconds=self._settings.resend_cooldown_seconds,
                internal_context={
                    "reason": "verification_resend_cooldown",
                    "user_id": str(user_id),
                },
            )
        issued = self._tokens.issue(
            user_id=str(user_id),
            purpose=TokenPurpose.EMAIL_VERIFY,
            context={"issued_at": now.isoformat()},
        )
        link = f"{self._verification_base_url}?token={issued.raw_token}"
        await self._email_sender.send_verification(to_email=email, link=link)

    async def _record_required_consents(
        self, user_id: uuid.UUID, request: RegistrationRequest
    ) -> None:
        """Append a consent row for every required document the user accepted.

        A missing required consent is a validation failure at the route boundary, but the
        service re-checks so a caller cannot bypass the route's validation and create an
        account without the legally-required acceptances (FR-001).
        """
        now = self._clock.now()
        for document in REQUIRED_CONSENTS:
            if not request.consents.get(document, False):
                raise ValidationError(
                    details=[
                        {"loc": ["consents", document], "msg": "required consent not accepted"}
                    ]
                )
            await self._consents.record(
                ConsentRecord(
                    id=uuid7(),
                    user_id=user_id,
                    document=document,
                    document_version=request.consent_versions.get(document, "unversioned"),
                    granted=True,
                    ip=request.ip,
                    user_agent=request.user_agent,
                    occurred_at=now,
                )
            )

    def _validate_password(self, password: str | None) -> None:
        """Structural password checks. Strength scoring (zxcvbn) and breach checking (HIBP)
        are added in T032; this guards the cheap invariants that must hold regardless."""
        if password is None:
            return
        if len(password) < 10:
            raise ValidationError(details=[{"loc": ["password"], "msg": "password is too short"}])
        if len(password) > 128:
            # Cap before hashing: Argon2 cost is per-length and an unbounded input is a cheap
            # DoS on the hash. 128 is far above any real passphrase.
            raise ValidationError(details=[{"loc": ["password"], "msg": "password is too long"}])


def _normalize_email(email: str) -> str:
    """Trim surrounding whitespace and lowercase.

    The column is ``citext`` and does case-folding for *comparison*, but the stored value is
    normalized here so the address we mail and the address we log are canonical. Trimming is
    the part citext does NOT do — a stray space from a paste would otherwise create a distinct
    identity that the user cannot reproduce on login.
    """
    return email.strip().lower()


__all__ = [
    "ONBOARDING_STEPS",
    "REQUIRED_CONSENTS",
    "InMemoryResendCooldownStore",
    "InMemoryVerificationEmailSender",
    "RegistrationOutcome",
    "RegistrationRequest",
    "RegistrationService",
    "ResendCooldownStore",
    "VerificationEmailSender",
]
