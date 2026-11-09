"""Framework-free auth entities and status state machines (T023; data-model.md).

The repository layer (``repository/tables.py``) imports the enums here — never the other
way around. That direction is what keeps the CHECK constraints and the domain transitions
in lockstep: one tuple of literals, two consumers.

State machines are explicit methods that raise on an illegal transition rather than
free-form setters. The reason is security-specific: an auth bug that sets
``status = "active"`` from a code path that should not be able to activate accounts is
invisible in review; ``user.verify_email()`` called from the wrong place is at least
traceable to a named operation.

What lives here vs. the ORM rows:

* **Enums and transitions** — the invariants.
* **Pure derivations** — ``Session.is_expired(now)``, ``Device.is_trusted(now)`` — logic
  that must be identical in the API and in any worker that reads these rows.
* **No I/O, no SQLAlchemy, no FastAPI.** A frozen dataclass plus methods is enough to
  unit-test every rule in this file without a database.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import StrEnum


class DomainTransitionError(Exception):
    """An illegal state transition was attempted. Callers map this to a 4xx/5xx per the
    error taxonomy (T014); the message is for logs, never for the client."""


# -- user ---------------------------------------------------------------------------------------


class UserStatus(StrEnum):
    """``pending_verification → active → (suspended | locked | deleting | deleted)``.

    ``locked`` is the abuse-backoff state (transient, self-healing); ``suspended`` is an
    operator action (persists until lifted). Keeping them separate means "too many bad
    passwords" and "support froze this account" cannot be confused by any reader of the
    row — including the login service, which treats them differently.
    """

    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    LOCKED = "locked"
    DELETING = "deleting"
    DELETED = "deleted"


#: The transition table, as data. A dict of sets is auditable in one screenful; a
#: distributed set of if-statements across services is not.
_USER_TRANSITIONS: dict[UserStatus, frozenset[UserStatus]] = {
    UserStatus.PENDING_VERIFICATION: frozenset({UserStatus.ACTIVE, UserStatus.DELETING}),
    UserStatus.ACTIVE: frozenset({UserStatus.SUSPENDED, UserStatus.LOCKED, UserStatus.DELETING}),
    # A locked account whose lockout elapsed returns to whatever it was; the service
    # records the prior status and uses unlock() with it.
    UserStatus.LOCKED: frozenset({UserStatus.ACTIVE, UserStatus.DELETING}),
    UserStatus.SUSPENDED: frozenset({UserStatus.ACTIVE, UserStatus.DELETING}),
    # deleting is cancelable during the 14-day grace (back to active); deleted is terminal.
    UserStatus.DELETING: frozenset({UserStatus.ACTIVE, UserStatus.DELETED}),
    UserStatus.DELETED: frozenset(),
}


def user_status_can_transition(src: UserStatus, dst: UserStatus) -> bool:
    return dst in _USER_TRANSITIONS[src]


@dataclass(frozen=True)
class User:
    """The identity core row as a domain object.

    Field set mirrors ``UserTable`` but carries only what services reason about — the
    repository maps to/from the row. ``roles_ver`` and ``mfa_enabled`` are stored here as
    plain values; bumping them is the service's job (it knows the event/audit side effects).
    """

    id: uuid.UUID
    email: str
    status: UserStatus = UserStatus.PENDING_VERIFICATION
    email_verified_at: datetime | None = None
    has_password: bool = False
    roles_ver: int = 0
    mfa_enabled: bool = False
    locked_until: datetime | None = None
    failed_login_count: int = 0
    created_at: datetime | None = None

    @property
    def can_authenticate(self) -> bool:
        """Whether login is currently allowed for this account.

        ``locked`` is excluded on purpose: the lockout check happens earlier (backoff
        state, T026) so the response can carry ``retry_after``; by the time this is
        consulted, a locked account should already have been refused.
        """
        return self.status is UserStatus.ACTIVE

    @property
    def is_passwordless(self) -> bool:
        return not self.has_password

    def transition_to(self, dst: UserStatus) -> User:
        """Return a copy in ``dst``. Raises :class:`DomainTransitionError` if illegal."""
        if not user_status_can_transition(self.status, dst):
            raise DomainTransitionError(f"user status {self.status} -> {dst} is not allowed")
        return replace(self, status=dst)

    def verify_email(self, *, now: datetime) -> User:
        """pending_verification → active, stamping the verification time."""
        if self.status is not UserStatus.PENDING_VERIFICATION:
            raise DomainTransitionError(
                f"email verification requires pending_verification, got {self.status}"
            )
        return replace(
            self,
            status=UserStatus.ACTIVE,
            email_verified_at=self.email_verified_at or now,
        )

    def lock(self, *, until: datetime) -> User:
        """active → locked with the backoff deadline."""
        return replace(self.transition_to(UserStatus.LOCKED), locked_until=until)

    def unlock(self) -> User:
        """locked/suspended → active (lockout elapsed, or operator lift)."""
        return self.transition_to(UserStatus.ACTIVE)

    def begin_deletion(self) -> User:
        """Any live state → deleting (privacy request; 14-day grace, cancelable)."""
        return self.transition_to(UserStatus.DELETING)

    def cancel_deletion(self) -> User:
        """deleting → active within the grace window."""
        return self.transition_to(UserStatus.ACTIVE)

    def mark_deleted(self) -> User:
        """deleting → deleted. The hard-erase step ran; the row is a tombstone."""
        return self.transition_to(UserStatus.DELETED)


# -- session --------------------------------------------------------------------------------------


class SessionStatus(StrEnum):
    """``active → rotated | revoked | expired``.

    ``rotated`` and ``revoked`` are terminal; ``expired`` is the janitor's mark on an
    ``active`` row past its deadlines. A rotated row is still *live data* — its family
    must be revocable on reuse — but it can never authenticate again.
    """

    ACTIVE = "active"
    ROTATED = "rotated"
    REVOKED = "revoked"
    EXPIRED = "expired"


_SESSION_TRANSITIONS: dict[SessionStatus, frozenset[SessionStatus]] = {
    SessionStatus.ACTIVE: frozenset(
        {SessionStatus.ROTATED, SessionStatus.REVOKED, SessionStatus.EXPIRED}
    ),
    # Reuse detection revokes a family member that was already rotated — the theft signal
    # is "someone used the old token", and the answer is to kill the whole family.
    SessionStatus.ROTATED: frozenset({SessionStatus.REVOKED}),
    SessionStatus.REVOKED: frozenset(),
    SessionStatus.EXPIRED: frozenset(),
}


def session_status_can_transition(src: SessionStatus, dst: SessionStatus) -> bool:
    return dst in _SESSION_TRANSITIONS[src]


@dataclass(frozen=True)
class Session:
    """A refresh-token session row as a domain object.

    ``family_id`` is the rotation family: one interactive login, N chained refreshes.
    ``parent_id`` is the previous token in the chain (None for the family root).
    """

    id: uuid.UUID
    user_id: uuid.UUID
    family_id: uuid.UUID
    status: SessionStatus = SessionStatus.ACTIVE
    parent_id: uuid.UUID | None = None
    device_id: uuid.UUID | None = None
    mfa_verified_at: datetime | None = None
    last_used_at: datetime | None = None
    absolute_expires_at: datetime | None = None
    idle_timeout_seconds: int = 14 * 24 * 3600

    def is_expired(self, now: datetime) -> bool:
        """Expiry is *derived* from timestamps, not stored: a janitor marks rows, but a
        request that arrives before the janitor must still refuse an expired token. The
        stored ``status`` is the durable record; this is the live truth.

        ``now`` is a parameter, not ``datetime.now()`` — every time decision in this
        codebase is testable against an injected clock, and a property that reads the wall
        clock internally is the one that cannot be proven.
        """
        if self.absolute_expires_at is None or self.last_used_at is None:
            return False
        if now >= self.absolute_expires_at:
            return True
        return now >= self.last_used_at + timedelta(seconds=self.idle_timeout_seconds)

    def transition_to(self, dst: SessionStatus) -> Session:
        if not session_status_can_transition(self.status, dst):
            raise DomainTransitionError(f"session status {self.status} -> {dst} is not allowed")
        return replace(self, status=dst)

    def rotate(self, *, new_id: uuid.UUID, now: datetime) -> tuple[Session, Session]:
        """Refresh: this session becomes ``rotated``, and a child session is returned.

        Returns a pair rather than mutating because both rows are written in one unit of
        work — the rotation is exactly the transaction where reuse detection gets its
        evidence, so half-applying it is the bug that defeats the whole mechanism.
        """
        rotated = self.transition_to(SessionStatus.ROTATED)
        child = Session(
            id=new_id,
            user_id=self.user_id,
            family_id=self.family_id,
            parent_id=self.id,
            device_id=self.device_id,
            mfa_verified_at=self.mfa_verified_at,
            last_used_at=now,
            absolute_expires_at=self.absolute_expires_at,
            idle_timeout_seconds=self.idle_timeout_seconds,
        )
        return rotated, child

    def revoke(self) -> Session:
        return self.transition_to(SessionStatus.REVOKED)

    def expire(self) -> Session:
        return self.transition_to(SessionStatus.EXPIRED)


# -- device ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Device:
    """A remembered browser/device.

    Trust is a *time-boxed* skip of the MFA challenge (FR-011): ``is_trusted`` is false
    once ``trusted_until`` passes, and the service slides the window forward on use.
    ``revoked_at`` kills trust immediately (user clicked "this wasn't me").
    """

    id: uuid.UUID
    user_id: uuid.UUID
    label: str | None = None
    platform: str | None = None
    trusted: bool = False
    trusted_until: datetime | None = None
    revoked_at: datetime | None = None
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None

    def is_trusted(self, now: datetime) -> bool:
        if not self.trusted or self.revoked_at is not None:
            return False
        return self.trusted_until is not None and now < self.trusted_until

    def revoke(self, *, now: datetime) -> Device:
        """Mark revoked. Idempotent: re-revoking keeps the original timestamp."""
        if self.revoked_at is not None:
            return self
        return replace(self, trusted=False, revoked_at=now)


__all__ = [
    "Device",
    "DomainTransitionError",
    "Session",
    "SessionStatus",
    "User",
    "UserStatus",
    "session_status_can_transition",
    "user_status_can_transition",
]
