# ADR-0001: Trading Execution Safety Architecture

> **Scope**: Document decision clusters, not individual technology choices. Group related decisions that work together (e.g., "Frontend Stack" not separate ADRs for framework, styling, deployment).

- **Status:** Accepted
- **Date:** 2026-08-29
- **Feature:** 003-trading-integration
- **Context:** Atlas is about to gain the ability to send real orders to real markets. Every other
  subsystem can be wrong and then corrected; this one spends money the instant it is wrong, and
  the two ways it goes wrong are irreversible: an order the user never approved, and the same
  order sent twice. Neither is recoverable by a retry, a rollback, or an apology.

  Three properties of the domain force the design. First, **order submission is not idempotent by
  nature** — venue REST APIs return a timeout without telling us whether the order reached the
  book, and the honest answer to "did it fill?" is often "unknown". Second, **a confirmation is
  only meaningful if it names exactly what will be sent** — prices move between composing an
  order and confirming it, so a confirmation that does not expire is a confirmation of something
  else. Third, **a risk limit that has an override parameter is a suggestion**; the bypass will be
  added under deadline pressure by someone with a good reason, and after that the gate is
  decorative.

  The constraints are therefore stated as invariants rather than goals: at-most-once venue
  transmission per intent (SC-005), no risk-gate bypass path anywhere (FR-038/SC-006), refuse
  rather than approximate on stale or missing inputs (SC-007), and explicit human confirmation of
  the exact terms before anything leaves the process (Constitution I, III, VI, IX).

<!-- Significance checklist (ALL must be true to justify this ADR)
     1) Impact: Long-term consequence for architecture/platform/security?
     2) Alternatives: Multiple viable options considered with tradeoffs?
     3) Scope: Cross-cutting concern (not an isolated detail)?
     If any are false, prefer capturing as a PHR note instead of an ADR. -->

## Decision

One safety architecture composed of four mechanisms that only work together. Each closes a hole
the others leave open, which is why they are one decision and not four.

**1. Two-phase order flow: intent → confirm.**
`POST /orders/intents` normalizes the symbol, validates instrument constraints and precision,
requires a fresh quote, prices the order, runs the risk gate, and persists an `order_intent`
carrying the verdict and an `expires_at` (default 30 s). The client reviews exact terms, verdict,
cost, margin, destination account, and environment. `POST /orders/intents/{id}/confirm` submits
the intent's `verdict_hash`; the server re-checks freshness, account state, kill switch, mandate
limits, and hash match. **Any drift returns `409` and forces re-review** (FR-025). The reviewable
artifact lives on the server, so the guarantee holds for every caller — not just the browser.

**2. At-most-once transmission via a pre-call submission ledger.**
The `order_submission` row (unique on `intent_id`) and the `order` row are committed **before**
the adapter is called, guarded by a Redis lock on `client_order_id`. The uniqueness constraint —
not application logic — is what makes a second submission impossible. A duplicate confirm returns
the first order. Exactly one `adapter.submit` per intent, ever.

**3. Ambiguity is a state, not an error to retry.**
`classify_error` is part of the `VenueAdapter` protocol and returns one of
`retryable_transient｜rate_limited｜terminal_rejection｜permission_denied｜ambiguous`. A submit
timeout or an `ambiguous` classification moves the order to a first-class **`unresolved`** state.
The request path **never retries and never guesses** — it does not render an ambiguous outcome as
either a fill or a rejection (FR-030). The only component permitted to resolve `unresolved` is
reconciliation, and the only authority on whether an order exists is the venue. `unresolved` count
and age are page-worthy metrics.

**4. A structurally unbypassable risk gate.**
`RiskGate.evaluate(intent, context) → RiskVerdict` is the only code path that can reach
`adapter.submit`. Enforcement is structural, not procedural: the submit call lives in one service
function that takes a `RiskVerdict` value object **it cannot construct itself**. No `force`,
`skip_risk`, `dry_run_bypass`, or admin equivalent exists in the OpenAPI surface, service
signatures, or the adapter protocol, and a contract test fails the build if one appears. Inputs
fail closed: stale quote, unknown balance, unreachable venue, or unknown instrument spec ⇒
`blocked` with `recommend_wait` (FR-039). Two consequences of "structural" worth stating
explicitly, because both look like exceptions and are not:

- **Risk-reducing orders** (closes and partial closes in the offsetting direction) remain
  permitted while a daily-loss or exposure block is active. This is *a rule inside the gate*, not
  a bypass of it (FR-043).
- **Automation mandates** skip *per-order confirmation only* — never the gate. A mandate requires
  step-up MFA, declares instrument scope and notional caps, and carries a mandatory expiry
  (max 30 days).

Live transmission is additionally gated by two independent switches — `TRADING_LIVE_ORDERS_ENABLED`
(config, default off) **and** `trading.live_orders.enabled` (feature flag, default off). A redeploy
takes minutes and a flag flip takes seconds, so an operator can stop transmission without waiting
on a release. Kill switches are deliberately *not* flags: they are stored state with actor, reason,
and timestamp, and they outrank everything including an active mandate.

### Implementation status at time of writing

The decision is accepted and being built against; the mechanisms are not all shipped. Recorded
here so this ADR is not read as a description of running code:

- Shipped: the risk gate's rule set and no-bypass guards, error taxonomy, adapter protocol with
  `classify_error`, Decimal-only enforcement, the two-switch live gate.
- Not yet shipped: the intent/confirm endpoints, the submission ledger, and reconciliation
  (Phases 4–9 of [tasks.md](../../specs/003-trading-integration/tasks.md)).
- The submission ledger initially lands as an in-memory repository port that enforces the
  `intent_id` uniqueness constraint itself, because Spec 00 shipped no persistence layer. **The
  at-most-once guarantee is only as durable as its store** — this mechanism is not complete until
  the Postgres constraint exists. See deviation #1 in tasks.md.

## Consequences

### Positive

- **The two failure modes that cost money are closed by construction, not by discipline.** A
  duplicate order requires violating a database constraint; a bypassed risk check requires
  constructing a value object the type system does not let you construct. Neither is reachable by
  writing careless code in a hurry.
- **The guarantee is server-side, so it holds for every caller** — future agents, strategies, and
  mandate-driven automation go through the same intent → gate → confirm path. Constitution IV
  (multi-agent collaboration) needs no second enforcement mechanism.
- **Ambiguity becomes visible instead of silently resolved.** A system that retries on timeout
  eventually double-fills; a system that assumes rejection eventually shows a phantom flat
  position. `unresolved` makes the honest answer representable, which is what allows every other
  component to trust the state it reads.
- **Every order is explainable end to end** — origin → verdict (rules, limits, actual values) →
  confirmation → submission ledger → venue responses → fills → final state, joined by correlation
  id (Constitution V, SC-009). The `verdict_hash` links the confirmation to the exact evaluation
  it was shown, so "what did the user actually approve?" has a cryptographic answer.
- **The no-bypass property is testable and therefore durable.** It is asserted at two layers
  (protocol/service signatures and the published OpenAPI surface) by tests that fail the build,
  so it survives contributors who never read this ADR.
- **Live routing can be switched off in seconds** without a deploy, and the module ships to
  production before live trading is enabled at all.

### Negative

- **Two round trips per order, and a confirmation that can expire under the user.** In a fast
  market a user may be forced to re-review repeatedly, which is genuinely worse UX than one-click
  placement. Accepted deliberately: the alternative is transmitting terms the user did not see.
- **`unresolved` orders need human-facing tooling and on-call attention.** Refusing to guess means
  the ambiguity is now someone's job. This buys correctness with operational load, and the load is
  real — hence the page-worthy metric and required runbooks.
- **Reconciliation becomes load-bearing rather than a background nicety.** `unresolved` is
  unresolvable without it, so reconciliation correctness is now on the critical path for order
  state. That is a second complex subsystem this decision makes mandatory.
- **The structural gate constrains future refactoring.** Any new execution path (a new order type,
  a bulk operation, a venue-specific shortcut) must route through `RiskGate` and accept a verdict
  it cannot mint. Some future feature will find this inconvenient, and the correct response will
  be to add a rule to the gate rather than a path around it.
- **Redis is on the order path** for the submit lock, so Redis unavailability means refusing to
  submit rather than degrading. Chosen over the alternative — submitting without a lock — because
  the failure mode of the alternative is a duplicate order.
- **State is duplicated on purpose.** The ledger, the order row, and the venue's own record all
  describe the same submission, and reconciling them is ongoing work rather than a one-time
  migration.

## Alternatives Considered

**Alternative A — Single-call placement with client-side confirmation.**
`POST /orders` places directly; the browser shows a confirm dialog first. Simplest to build, one
round trip, no expiry semantics, no intent table.
*Rejected*: the guarantee lives in the client, where any non-browser caller — a script, a future
agent, a mobile app, a curl command — skips it entirely. Constitution I requires explicit
confirmation of exactly what will be sent, and a client-side dialog cannot produce a reviewable,
invalidatable, auditable artifact. It also has nothing to hash, so there is no way to prove what
the user approved.

**Alternative B — Idempotency key only (no pre-call ledger).**
Send a `client_order_id` and rely on the venue to reject duplicates.
*Rejected*: idempotency support is uneven across MT5, OANDA, Binance, Bybit, and IBKR, the
semantics differ per venue, and the retention window for a used key is typically undocumented.
Delegating the one guarantee we must not lose to the least uniform part of five third-party APIs
means the guarantee holds only where it happens to. The pre-call ledger holds it in our own
database, identically for every venue including paper — and `client_order_id` is still sent as
defence in depth where the venue honours it.

**Alternative C — Automatic retry with deduplication on ambiguous outcomes.**
On timeout, retry the submit; detect and cancel the duplicate afterwards.
*Rejected*: this is the design that produces the incident. Detection requires the venue to answer
truthfully during the exact window in which it has already failed to answer, and "cancel the
duplicate afterwards" assumes the duplicate has not already filled. It converts a known-unknown
into an unbounded position at market. `unresolved` + reconciliation is slower and strictly safer.

**Alternative D — Risk checks as middleware, a decorator, or a service-layer convention.**
A `@requires_risk_check` decorator or an ASGI middleware in front of order endpoints.
*Rejected*: all three are bypassable by writing code that does not use them, and nothing fails
when someone doesn't. Middleware in particular cannot see the domain values it needs (position
size, exposure, mandate consumption) without duplicating the domain. Making the verdict an
unconstructible argument to the submit function means the bypass is a type error, and the "no
override parameter" contract test means an intentional one is a failed build.

**Alternative E — Post-trade risk monitoring instead of a pre-trade gate.**
Let orders through; detect and unwind breaches afterwards.
*Rejected outright by Constitution VI (Risk Before Profit)*. Unwinding a breach realizes the loss
it was meant to prevent and adds slippage, and in a gapping market the unwind price is arbitrary.
Post-trade monitoring remains valuable, but as a second layer, not the first.

**Alternative F — Local state as source of truth, with periodic sync.**
Trust Atlas's own order and position records; sync from the venue on a schedule.
*Rejected*: positions and orders change outside Atlas (manual terminal trades, stop-outs, margin
liquidations, corporate actions), so local-as-truth guarantees silent divergence and the risk gate
would compute limits against fiction. This is the reasoning behind the companion decision to treat
the venue as authoritative and local state as a correctable projection — a separate cluster,
recorded as a candidate ADR below rather than folded in here, because it could be revisited
independently.

## References

- Feature Spec: [specs/003-trading-integration/spec.md](../../specs/003-trading-integration/spec.md)
- Implementation Plan: [specs/003-trading-integration/plan.md](../../specs/003-trading-integration/plan.md)
  — §6 order lifecycle, §7 risk gate, §8 mandates and kill switch, §12 degraded modes,
  Complexity Tracking entries 2–3, Risks 1–2
- Research: [specs/003-trading-integration/research.md](../../specs/003-trading-integration/research.md)
- Data model: [specs/003-trading-integration/data-model.md](../../specs/003-trading-integration/data-model.md)
  — `order_intent`, `order`, `order_submission` (unique on `intent_id`), `risk_verdict`
- Tasks: [specs/003-trading-integration/tasks.md](../../specs/003-trading-integration/tasks.md)
  — T027/T028 (guard tests), T070–T093 (order lifecycle), T072 (single transmission per intent),
  T073 (timeout ⇒ `unresolved`, never a retry), and *Implementation deviations*
- Constitution: `.specify/memory/constitution.md` — I Human First, III Transparency,
  V Explainability, VI Risk Before Profit, IX Reliability / Fail Safe
- Related ADRs: none yet. Candidate companions identified in the same review: Venue Abstraction
  Layer, Venue-Authoritative State & Reconciliation, Market Data Freshness Contract.
- Evaluator Evidence: in-repo guard tests are the standing evidence for this ADR's central claims
  — `tests/contract/trading/test_api_surface_guards.py` and
  `shared/tests/venues/test_no_risk_bypass.py` (no bypass parameter, SC-006),
  `shared/tests/venues/test_no_credential_exposure.py` (SC-011),
  `tests/contract/trading/test_shipped_flags_are_safe.py` (live transmission ships off).
  T072/T073 will supply the at-most-once and ambiguity evidence when the order path lands.
