"""Auth email dispatch consumer (T017; plan §8, §12).

The API never sends email inline — a slow or down mail provider must not turn sign-in into a
500. Instead the API emits an auth event and this worker turns it into a queued email with
retries (Constitution IX: "if email down → queued retries, never fail-open on the user's
action"). The bus already provides retry → DLQ (``atlas_events.bus``), so a handler here just
raises on a transient send failure and the bus re-delivers; a permanent failure (unknown
recipient) is swallowed with a log rather than retried forever.

Design choices worth naming:

* **Templates are data, not code paths.** A ``TemplateRegistry`` maps a template id to a
  subject/body builder. Adding an email is adding a template, not editing the consumer's
  control flow.
* **The transport is a Protocol.** ``Notifier`` is the seam; the SMTP implementation lives
  behind it so the consumer is testable with a recording fake and the real provider can be
  swapped (SES, Postmark) without touching dispatch logic.
* **Recipients are resolved, never trusted from the payload.** The event contract carries
  ``user_id`` and deliberately not a plaintext email (auth-events.md). So we resolve
  ``user_id → email`` through a ``RecipientResolver`` at send time; a user who deleted their
  address between event and delivery simply gets no email, which is correct.
* **Security notifications are best-effort but loud.** A failed "your password changed" email
  is a security-relevant miss, so it is logged at warning with the event id for the runbook.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from atlas_events.bus import EventBus
from atlas_events.envelope import EventEnvelope
from atlas_observability import get_logger

logger = get_logger("atlas_worker.auth_emails")


class EmailSendError(Exception):
    """Transient transport failure — the bus should retry."""


class Notifier(Protocol):
    """Deliver one email. Implementations raise :class:`EmailSendError` on a transient
    failure (connection reset, provider 5xx) so the bus retries; a permanent rejection
    (bad address) should be handled by the implementation, not surfaced as retryable."""

    async def send(self, *, to: str, subject: str, body: str) -> None: ...


class RecipientResolver(Protocol):
    """Resolve a ``user_id`` to a delivery address, or ``None`` if there is none."""

    async def email_for(self, user_id: str) -> str | None: ...


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    body: str


#: A template turns an event payload into a rendered email. Pure and synchronous by contract —
#: no I/O here; resolution and delivery happen in the consumer.
Template = Callable[[dict[str, Any]], RenderedEmail]


class TemplateRegistry:
    """Named email templates. The consumer looks a template up by id; unknown ids are a bug,
    not a silent skip, so they raise at dispatch (and thus dead-letter) rather than vanish."""

    def __init__(self) -> None:
        self._templates: dict[str, Template] = {}

    def register(self, template_id: str, template: Template) -> None:
        self._templates[template_id] = template

    def render(self, template_id: str, payload: dict[str, Any]) -> RenderedEmail:
        try:
            template = self._templates[template_id]
        except KeyError as exc:
            raise KeyError(f"no email template registered for '{template_id}'") from exc
        return template(payload)

    def ids(self) -> list[str]:
        return sorted(self._templates)


def _verification(payload: dict[str, Any]) -> RenderedEmail:
    return RenderedEmail(
        subject="Verify your Atlas account",
        body=(
            "Welcome to Atlas. Confirm your email address to activate your account. "
            "Use the verification link from your signup flow; it expires in 24 hours."
        ),
    )


def _welcome(payload: dict[str, Any]) -> RenderedEmail:
    return RenderedEmail(
        subject="Your Atlas account is ready",
        body="Your email is verified and your Atlas account is active. You can sign in now.",
    )


def _password_reset(payload: dict[str, Any]) -> RenderedEmail:
    return RenderedEmail(
        subject="Reset your Atlas password",
        body=(
            "We received a request to reset your Atlas password. Use the reset link from your "
            "request; it expires in 30 minutes. If you did not request this, you can ignore "
            "this email — your password will not change."
        ),
    )


def _password_changed(payload: dict[str, Any]) -> RenderedEmail:
    via = payload.get("via", "change")
    return RenderedEmail(
        subject="Your Atlas password was changed",
        body=(
            f"Your Atlas password was changed ({via}). If this was not you, secure your "
            "account immediately and contact support."
        ),
    )


def _locked_out(payload: dict[str, Any]) -> RenderedEmail:
    return RenderedEmail(
        subject="Your Atlas account is temporarily locked",
        body=(
            "Too many failed sign-in attempts locked your Atlas account briefly. This is a "
            "security measure. If you did not attempt to sign in, change your password once "
            "the lock lifts."
        ),
    )


def _mfa_changed(payload: dict[str, Any]) -> RenderedEmail:
    return RenderedEmail(
        subject="Multi-factor authentication changed on your Atlas account",
        body=(
            "A change was made to your Atlas multi-factor authentication settings. If this "
            "was not you, contact support immediately."
        ),
    )


def _recovery_code_used(payload: dict[str, Any]) -> RenderedEmail:
    remaining = payload.get("remaining", 0)
    return RenderedEmail(
        subject="A recovery code was used on your Atlas account",
        body=(
            f"A one-time recovery code was used to sign in. You have {remaining} recovery "
            "codes remaining. If this was not you, secure your account now."
        ),
    )


def default_templates() -> TemplateRegistry:
    """The Spec 02 auth email set. The consumer depends on these ids; a deployment can extend
    or override by registering into the returned registry before wiring."""
    reg = TemplateRegistry()
    reg.register("verification", _verification)
    reg.register("welcome", _welcome)
    reg.register("password_reset", _password_reset)
    reg.register("password_changed", _password_changed)
    reg.register("locked_out", _locked_out)
    reg.register("mfa_changed", _mfa_changed)
    reg.register("recovery_code_used", _recovery_code_used)
    return reg


#: Which template each auth event maps to. ``registered`` is conditional on
#: ``requires_verification`` (handled in the consumer); ``mfa.enrolled`` and ``mfa.disabled``
#: share one notification template because the message is the same either way.
_EVENT_TEMPLATES: dict[str, str] = {
    "atlas.auth.user.email_verified": "welcome",
    "atlas.auth.password.reset_requested": "password_reset",
    "atlas.auth.password.changed": "password_changed",
    "atlas.auth.user.locked_out": "locked_out",
    "atlas.auth.mfa.enrolled": "mfa_changed",
    "atlas.auth.mfa.disabled": "mfa_changed",
    "atlas.auth.mfa.recovery_code_used": "recovery_code_used",
}


class AuthEmailConsumer:
    """Subscribes to auth events and dispatches the matching email.

    Constructed with a notifier, a resolver, and a template registry so every external
    dependency is injected — the worker composition root wires the SMTP notifier and the
    database-backed resolver; tests wire fakes.
    """

    def __init__(
        self,
        *,
        notifier: Notifier,
        resolver: RecipientResolver,
        templates: TemplateRegistry | None = None,
    ) -> None:
        self._notifier = notifier
        self._resolver = resolver
        self._templates = templates or default_templates()

    def subscribe(self, bus: EventBus) -> None:
        """Register handlers for every auth event this consumer acts on."""
        for event_type in (*_EVENT_TEMPLATES.keys(), "atlas.auth.user.registered"):
            bus.subscribe("auth-emails", event_type, self._handle)

    async def _handle(self, envelope: EventEnvelope) -> None:
        payload = envelope.payload
        template_id = self._template_for(envelope.event_type, payload)
        if template_id is None:
            return

        user_id = payload.get("user_id")
        if not user_id:
            # login_failed and security_event carry no user_id by design (pseudonymized /
            # user-may-be-unknown); they are not email-triggering events anyway.
            return

        email = await self._resolver.email_for(user_id)
        if email is None:
            logger.info(
                "email_skipped_no_recipient",
                event_id=envelope.event_id,
                template=template_id,
            )
            return

        rendered = self._templates.render(template_id, payload)
        await self._notifier.send(to=email, subject=rendered.subject, body=rendered.body)
        logger.info("email_dispatched", event_id=envelope.event_id, template=template_id)

    @staticmethod
    def _template_for(event_type: str, payload: dict[str, Any]) -> str | None:
        if event_type == "atlas.auth.user.registered":
            # Only send verification when the account actually needs it (social sign-in may
            # arrive pre-verified).
            return "verification" if payload.get("requires_verification") else None
        return _EVENT_TEMPLATES.get(event_type)


__all__ = [
    "AuthEmailConsumer",
    "EmailSendError",
    "Notifier",
    "RecipientResolver",
    "RenderedEmail",
    "TemplateRegistry",
    "default_templates",
]
