# Feature Specification: Trading Integration (Venues, Market Data & Order Execution)

**Feature Branch**: `003-trading-integration`
**Created**: 2026-08-25
**Status**: Draft
**Input**: User description: "Spec 03 — Trading Integration: Connect Atlas to real brokers and exchanges so users can stream market data, see their live accounts and positions, and place, modify, and cancel orders under an unbypassable pre-trade risk gate with explicit human confirmation — including a paper-trading mode and continuous reconciliation against the venue."

## User Scenarios & Testing *(mandatory)*

The users of this capability are retail and professional traders (forex and crypto first),
algorithmic traders who will later attach agents and strategies, and support staff who must
diagnose a broken connection or a disputed order without ever seeing a secret.

This is the first specification in which Atlas can move real money. Every story below is
written so that the safe outcome — refusing to act — is always reachable.

### User Story 1 - Connect a Broker or Exchange Account (Priority: P1)

A trader links an existing broker or exchange account to Atlas by selecting the venue,
supplying credentials once, choosing whether the connection is live or demo, and confirming
that Atlas can read the account. The connection then reports its own health over time.

**Why this priority**: Nothing else in this specification can be demonstrated without a
connection. It is also the highest-risk moment in the feature, because it is when a user
hands over trading authority.

**Independent Test**: Can be fully tested by connecting one venue in demo mode, seeing the
connection reach a healthy state with the account identifier and balance displayed, then
disconnecting it and confirming Atlas can no longer reach the account.

**Acceptance Scenarios**:

1. **Given** a trader with valid demo credentials for a supported venue, **When** they create
   a connection, **Then** Atlas verifies reachability, records the venue's granted
   capabilities and permissions, and shows the connection as healthy with its account summary.
2. **Given** a trader supplies credentials that are invalid, expired, or lack the required
   permissions, **When** they attempt to connect, **Then** Atlas refuses the connection and
   explains which requirement failed, without storing an unusable connection and without
   echoing the supplied secret.
3. **Given** a live connection whose credentials are later revoked at the venue, **When** the
   next health check runs, **Then** Atlas marks the connection degraded, surfaces it to the
   user, and refuses to submit new orders through it.
4. **Given** a connected venue, **When** the trader disconnects it, **Then** Atlas stops all
   data subscriptions and order routing for it immediately and records the change.
5. **Given** a trader with a live connection, **When** they inspect it, **Then** they can see
   which environment it points at (live or demo), what Atlas is permitted to do with it, and
   when it was last contacted — but never the credential itself.

---

### User Story 2 - Stream Trustworthy Market Data (Priority: P1)

A trader watches live prices for the instruments they care about, sees recent price history,
and is told plainly whenever the data they are looking at is stale, delayed, or unavailable.

**Why this priority**: Price is the input to every decision in the product. Data that is
silently wrong is more dangerous than no data, so the freshness contract has to exist before
any order can be justified.

**Independent Test**: Can be fully tested by subscribing to a handful of instruments,
observing prices update, requesting historical bars, then interrupting the feed and confirming
the interface marks the data stale rather than showing a frozen price as if it were current.

**Acceptance Scenarios**:

1. **Given** a healthy connection, **When** the trader subscribes to an instrument, **Then**
   live prices arrive continuously and each price carries the time it was observed and the
   venue it came from.
2. **Given** an active subscription, **When** the feed stops delivering updates beyond the
   freshness limit, **Then** Atlas marks that instrument's data stale, tells the user, and
   any dependent action that requires fresh prices is refused rather than approximated.
3. **Given** a trader wants context, **When** they request recent price history for an
   instrument and timeframe, **Then** Atlas returns a complete, gap-marked series and states
   which venue and timeframe it represents.
4. **Given** two venues quote the same instrument differently, **When** the trader views it,
   **Then** Atlas shows which venue each price came from and never blends them into a single
   unattributed number.
5. **Given** an instrument is outside its trading session or has been suspended by the venue,
   **When** the trader views it, **Then** Atlas shows the session state instead of implying
   the market is tradable.

---

### User Story 3 - See Real Account, Balance and Position State (Priority: P2)

A trader sees their true balance, equity, margin, open positions, and open orders for each
connected venue, refreshed continuously, with unrealized profit and loss that matches what the
venue itself reports.

**Why this priority**: Traders will not trust — and must not act on — a position view that
disagrees with their broker. This is also the state the risk gate in US5 depends on.

**Independent Test**: Can be fully tested by opening a position directly at the venue
(outside Atlas), then confirming Atlas discovers and displays it with matching quantity,
entry price, and unrealized result, and that closing it at the venue makes it disappear.

**Acceptance Scenarios**:

1. **Given** a healthy connection, **When** the trader opens the account view, **Then** Atlas
   shows balance, equity, used and free margin, leverage, and account currency as reported by
   the venue, with the time of the last successful sync.
2. **Given** positions exist at the venue — including ones Atlas did not create, **When**
   Atlas syncs, **Then** every position appears with instrument, direction, quantity, average
   entry price, current price, unrealized result, and any attached protective levels.
3. **Given** a position changes at the venue, **When** the next sync or venue update arrives,
   **Then** Atlas reflects the change within the stated freshness target and records that it
   did.
4. **Given** the venue is unreachable, **When** the trader opens the account view, **Then**
   Atlas shows the last known state clearly labelled with its age and marks the account view
   degraded — it never presents stale state as live.
5. **Given** multiple connected venues, **When** the trader views their overall exposure,
   **Then** Atlas presents each venue's state separately and any combined figure states which
   venues it includes.

---

### User Story 4 - Place, Modify and Cancel Orders With Explicit Confirmation (Priority: P2)

A trader composes an order, reviews exactly what will be sent — instrument, direction,
quantity, order type, price terms, time in force, protective levels, and estimated cost —
confirms it deliberately, and then watches its progress from submission through fills or
rejection. They can cancel or amend a working order, and every step is recorded.

**Why this priority**: This is the feature's reason to exist, and it is the point where the
Human First and Risk Before Profit principles are either real or decorative.

**Independent Test**: Can be fully tested in demo or paper mode by composing an order, seeing
the review step, confirming it, watching it reach a terminal state, then cancelling a second
working order and amending a third — with a full event history available for each.

**Acceptance Scenarios**:

1. **Given** a trader has composed an order, **When** they submit it, **Then** Atlas does not
   send anything to the venue until the trader explicitly confirms a review that shows the
   exact order terms, the risk verdict, and the estimated cost and margin impact.
2. **Given** a trader confirms an order, **When** Atlas submits it, **Then** the order is sent
   exactly once even if the trader's confirmation is retried or duplicated, and the trader can
   see its live status.
3. **Given** a submitted order, **When** the venue partially fills it, **Then** Atlas shows
   filled quantity, average fill price, remaining quantity, and fees, updating as further
   fills arrive.
4. **Given** a working order, **When** the trader cancels or amends it, **Then** Atlas sends
   the request to the venue, reports the venue's actual answer, and never reports success for
   a cancellation the venue refused.
5. **Given** the venue rejects an order, **When** the rejection arrives, **Then** Atlas shows
   the venue's reason in plain language, keeps the full history, and leaves no phantom order
   or position behind.
6. **Given** Atlas submits an order and then loses contact before learning the outcome,
   **When** the trader views that order, **Then** its state is shown as unresolved and under
   reconciliation — never as filled, and never silently retried.
7. **Given** an order is closed out or a position is closed, **When** the trader reviews it
   later, **Then** they can see who or what initiated it, the risk verdict at the time, the
   prices used, and every state change with timestamps.

---

### User Story 5 - Trade Inside an Unbypassable Risk Gate (Priority: P3)

A trader sets their own risk limits — maximum position size, maximum exposure, maximum daily
loss, maximum open positions, leverage ceiling, permitted instruments and sessions — and every
order is checked against them before it can be sent. When a limit would be breached, the order
is refused with a clear explanation. A kill switch halts all new orders immediately.

**Why this priority**: The constitution puts risk ahead of profit without exception. Users can
demo the product without this, but Atlas must not route live orders without it.

**Independent Test**: Can be fully tested by setting a small limit, attempting an order that
violates it, confirming the refusal names the breached rule and its values, then engaging the
kill switch and confirming that every new order is refused while existing positions remain
visible and closable.

**Acceptance Scenarios**:

1. **Given** a trader has risk limits configured, **When** an order would breach one, **Then**
   Atlas refuses it before anything reaches the venue and shows which rule was breached, the
   limit, and the value that triggered it.
2. **Given** any origin of an order — manual, agent, or strategy, **When** it is evaluated,
   **Then** the same risk rules apply and no origin, role, or setting can skip, relax, or
   override them at the time of the order.
3. **Given** required inputs for a risk check are missing or stale — no fresh price, unknown
   account balance, unreachable venue, **When** an order is evaluated, **Then** Atlas refuses
   the order and recommends waiting rather than proceeding on assumptions.
4. **Given** a trader engages the kill switch, **When** any new order is attempted, **Then**
   it is refused immediately, and the trader can still view, cancel, and close existing
   orders and positions.
5. **Given** a daily loss limit is reached, **When** further orders are attempted, **Then**
   Atlas blocks new risk-increasing orders for the remainder of the period, states when the
   block lifts, and still permits risk-reducing actions.
6. **Given** a trader wants to relax a limit, **When** they change it, **Then** the change is
   recorded with who made it and when, takes effect only for future orders, and cannot be
   applied retroactively to unblock an already-refused order.
7. **Given** a trader delegates a scoped automation, **When** they define it, **Then** they
   must state its instruments, maximum order size, maximum total commitment, and expiry, and
   they can revoke it at any moment with immediate effect.

---

### User Story 6 - Practice Safely in Paper Trading Mode (Priority: P3)

A trader runs the entire experience — data, orders, fills, positions, risk — against a
simulated account with no venue connection and no real money, and can never confuse it with
live trading.

**Why this priority**: Paper mode is how users build trust, how the team tests execution
safely, and how future agents and strategies will be validated before touching capital.

**Independent Test**: Can be fully tested with no venue credentials at all: create a paper
account, place orders against live prices, receive simulated fills, watch positions and
balance change, then reset the account to its starting state.

**Acceptance Scenarios**:

1. **Given** a trader with no connected venue, **When** they enable paper trading, **Then**
   they receive a simulated account with a starting balance and can trade the same instruments
   through the same flow.
2. **Given** a paper order, **When** it is filled, **Then** the fill uses live market prices
   with disclosed assumptions about spread, slippage, and delay, and the trader can see those
   assumptions.
3. **Given** a trader is in paper mode, **When** they view any account, order, position, or
   confirmation screen, **Then** it is unmistakably marked as simulated.
4. **Given** a trader has both paper and live accounts, **When** they place an order, **Then**
   the destination account is shown in the confirmation and cannot be changed after
   confirming.
5. **Given** a paper account, **When** the trader resets it, **Then** balances, positions,
   orders, and history return to the starting state and the reset is recorded.

---

### User Story 7 - Reconcile, Audit and Explain Every Execution (Priority: P4)

A trader or support agent can prove what happened: Atlas continuously compares its own view
against the venue's, surfaces and explains any discrepancy, and keeps a complete, tamper-
evident record of every order, fill, risk verdict, and connection change.

**Why this priority**: Disputes and incidents are inevitable when money moves. This story
turns "we think it filled" into evidence, and it is what makes the earlier stories safe to
operate rather than merely functional.

**Independent Test**: Can be fully tested by deliberately creating a divergence — cancel an
order directly at the venue while Atlas believes it is working — then confirming the next
reconciliation detects it, classifies it, corrects Atlas's view, and records the correction.

**Acceptance Scenarios**:

1. **Given** Atlas holds a view of orders and positions, **When** reconciliation runs, **Then**
   it compares against the venue's authoritative state and reports every difference with its
   classification and resolution.
2. **Given** a discrepancy is found, **When** it is resolved, **Then** the venue's state wins,
   Atlas's view is corrected, and both the original divergence and the correction are recorded.
3. **Given** a discrepancy cannot be resolved automatically, **When** reconciliation completes,
   **Then** it is escalated to the trader and to support with enough detail to act, and
   affected order routing for that account is held until it is settled.
4. **Given** any order in history, **When** a trader or support agent inspects it, **Then**
   they can see its full chain: origin, risk verdict and inputs, confirmation, submission,
   venue responses, fills, and final state — with correlated identifiers throughout.
5. **Given** support is investigating a connection problem, **When** they inspect the account,
   **Then** they can see connection health, permissions, and error history without any access
   to the credential itself.

---

### Edge Cases

- **Venue unreachable mid-order**: submission times out with no answer — the order must land
  in an explicit unresolved state, be reconciled against the venue, and never be blindly
  resubmitted.
- **Duplicate confirmation**: a trader double-clicks confirm, or a client retries — exactly one
  order must reach the venue.
- **Stale price at confirmation**: the price moves or the feed goes stale between review and
  confirmation — the confirmation must be invalidated and re-reviewed rather than sent.
- **Partial fill then cancel**: a cancellation arrives after part of the order filled — the
  filled portion must remain accurate and the remainder must be shown as cancelled.
- **Venue rejects for reasons Atlas cannot see** (margin call, instrument suspended, account
  restriction) — the venue's reason must be surfaced verbatim in sanitized form, not replaced
  by a generic failure.
- **Position opened outside Atlas**: manual trades at the venue must be discovered and counted
  against risk limits, not ignored.
- **Instrument specification changes** (contract size, tick size, minimum quantity, symbol
  rename) — quantity and price validation must fail safe rather than send an invalid order.
- **Venue rate limits and bans**: hitting a venue's limit must degrade the connection and back
  off, never spin or silently drop user actions.
- **Clock skew between Atlas and the venue**: time-sensitive rules (session guards, daily loss
  windows, expiry) must use a reconciled time reference.
- **Revoked or rotated credentials**: order routing must stop immediately on revocation, with
  in-flight orders reconciled rather than abandoned.
- **Weekend, holiday, and session boundaries**: orders placed into a closed market must be
  refused or explicitly queued with the queuing behavior disclosed.
- **Kill switch during in-flight orders**: already-submitted orders must be reported honestly;
  the kill switch stops new risk, it does not rewrite history.
- **Paper and live confusion**: no flow may allow a paper confirmation to route to a live
  account or vice versa.
- **Currency and precision**: quantity, price, and money values must never lose precision or
  round in a way that changes the order sent.
- **Multiple Atlas sessions**: the same user acting from two devices must not create duplicate
  or conflicting orders.

## Requirements *(mandatory)*

### Functional Requirements

**Venue connections**

- **FR-001**: Users MUST be able to connect broker and exchange accounts to Atlas by selecting
  a supported venue and supplying credentials once.
- **FR-002**: The platform MUST support the venues MetaTrader 5, OANDA, Binance, Bybit, and
  Interactive Brokers, and MUST expose a venue-agnostic capability contract so further venues
  can be added without changing user-facing behavior.
- **FR-003**: Each connection MUST declare its environment as live, demo, or paper, and MUST
  make that environment visible everywhere the connection is used.
- **FR-004**: The platform MUST verify a connection's reachability and permissions before
  accepting it, and MUST refuse to store a connection that cannot be verified.
- **FR-005**: The platform MUST record, per connection, the capabilities the venue actually
  grants (for example: read account, read market data, place orders, amend orders) and MUST
  refuse any action the connection is not permitted to perform.
- **FR-006**: The platform MUST monitor connection health continuously and MUST mark a
  connection degraded, expired, or failed with a user-visible reason when it stops working.
- **FR-007**: Users MUST be able to disconnect a venue at any time, which MUST immediately stop
  data subscriptions and order routing for that connection.
- **FR-008**: Venue credentials MUST never be visible to any client, any role, or any log, and
  MUST be used only by trusted server-side components.

**Market data**

- **FR-009**: Users MUST be able to subscribe to live prices for instruments available on their
  connected venues and receive continuous updates.
- **FR-010**: Every price MUST carry its observation time and originating venue.
- **FR-011**: The platform MUST define a freshness limit per asset class and MUST mark data
  stale, and tell the user, when that limit is exceeded.
- **FR-012**: Any action that requires a current price MUST be refused when only stale data is
  available.
- **FR-013**: Users MUST be able to retrieve recent price history for an instrument and
  timeframe, with gaps explicitly marked rather than interpolated.
- **FR-014**: The platform MUST publish an instrument catalog including tradability, session
  state, minimum and maximum quantity, quantity step, and price precision per venue.
- **FR-015**: Prices from different venues MUST remain separately attributed and MUST NOT be
  merged into an unattributed value.

**Account, position and order state**

- **FR-016**: The platform MUST synchronize account balance, equity, margin, leverage, and
  account currency from each connected venue.
- **FR-017**: The platform MUST synchronize all open positions and working orders, including
  ones created outside Atlas.
- **FR-018**: Position views MUST include instrument, direction, quantity, average entry price,
  current price, unrealized result, and attached protective levels.
- **FR-019**: The platform MUST record and display the age of the last successful sync for
  every account, and MUST mark account state degraded when it exceeds the freshness target.
- **FR-020**: The platform MUST treat the venue as the authoritative source for balances,
  orders, positions, and fills; Atlas's stored view is a correctable projection.
- **FR-021**: Users MUST be able to see historical closed positions and completed orders with
  their realized results and fees.
- **FR-022**: Combined exposure figures MUST state which accounts and venues they include.

**Order lifecycle**

- **FR-023**: Users MUST be able to compose market, limit, stop, and stop-limit orders with a
  time-in-force selection and optional protective levels (stop loss and take profit).
- **FR-024**: The platform MUST NOT transmit any order to a venue without an explicit human
  confirmation of a review that states the exact order terms, the risk verdict, and the
  estimated cost and margin impact — except under an active, scoped automation mandate
  (FR-041).
- **FR-025**: A confirmation MUST expire, and MUST be invalidated when the price, account
  state, or risk verdict it was based on is no longer current; an invalidated confirmation
  MUST require a fresh review.
- **FR-026**: Every order MUST carry a client-assigned identifier that guarantees it is
  transmitted to the venue at most once, regardless of retries, duplicate confirmations, or
  concurrent sessions.
- **FR-027**: The platform MUST maintain an explicit order state for every order and MUST
  record every state transition with its time, cause, and originating actor.
- **FR-028**: Users MUST be able to cancel and amend working orders, and the platform MUST
  report the venue's actual response rather than an assumed outcome.
- **FR-029**: The platform MUST record fills individually, including quantity, price, fees, and
  venue execution identifier, and MUST derive filled quantity and average price from them.
- **FR-030**: When an order's outcome is unknown after submission, the platform MUST place it
  in an explicit unresolved state, MUST NOT report it as filled or cancelled, and MUST NOT
  resubmit it automatically.
- **FR-031**: Users MUST be able to close a position and to attach, change, or remove
  protective levels on an existing position.
- **FR-032**: Venue rejection reasons MUST be surfaced to the user in sanitized, readable form.
- **FR-033**: The platform MUST refuse orders that violate the venue's own instrument
  constraints (quantity bounds, quantity step, price precision, session state) before
  transmission.
- **FR-034**: The platform MUST record, for every order, its origin (manual, agent, strategy,
  or automation mandate) and the identity of the human accountable for it.
- **FR-035**: The platform MUST respect each venue's rate limits and MUST degrade the
  connection with a clear user-visible reason rather than dropping or silently delaying user
  actions.

**Risk gate and controls**

- **FR-036**: The platform MUST evaluate every order against the user's risk policy before
  transmission, and MUST refuse the order when any rule would be breached.
- **FR-037**: The risk policy MUST support at minimum: maximum order size, maximum position
  size per instrument, maximum total exposure, maximum daily loss, maximum open positions,
  leverage ceiling, permitted instruments, and permitted trading sessions.
- **FR-038**: No user, role, agent, setting, or request parameter MAY bypass, disable, or
  relax the risk gate for an order being evaluated; there MUST be no override path.
- **FR-039**: The platform MUST refuse an order when any input required to evaluate risk is
  missing, stale, or unavailable, and MUST recommend waiting.
- **FR-040**: Every risk evaluation MUST be recorded with the rules evaluated, the values used,
  the verdict, and a correlating identifier, and MUST be retrievable later for any order.
- **FR-041**: Users MUST be able to grant a scoped automation mandate that permits orders
  without per-order confirmation, and such a mandate MUST require explicit instrument scope,
  maximum order size, maximum total commitment, and expiry, and MUST remain subject to the
  risk gate.
- **FR-042**: Users MUST be able to revoke an automation mandate at any time with immediate
  effect.
- **FR-043**: Users MUST be able to engage a kill switch that immediately refuses all new
  orders for their accounts while leaving cancellation and position-closing available; the
  platform MUST also support an operator-level kill switch.
- **FR-044**: Risk policy changes and kill-switch changes MUST be recorded with actor and time
  and MUST apply only to subsequent orders.

**Paper trading**

- **FR-045**: Users MUST be able to trade a simulated account through the same flows without
  any venue connection or real funds.
- **FR-046**: Simulated fills MUST be based on live market prices with disclosed assumptions
  for spread, slippage, and delay.
- **FR-047**: Every simulated account, order, position, and confirmation surface MUST be
  unmistakably marked as simulated.
- **FR-048**: The destination account MUST be shown in every confirmation and MUST NOT be
  changeable after confirmation.
- **FR-049**: Users MUST be able to reset a simulated account to its starting state, and the
  reset MUST be recorded.
- **FR-050**: Simulated activity MUST NOT be counted in any figure presented as real
  performance.

**Reconciliation, audit and operations**

- **FR-051**: The platform MUST reconcile its view of orders, positions, and balances against
  each venue on a defined cadence and after any unresolved outcome.
- **FR-052**: Reconciliation MUST classify each discrepancy, resolve it in favor of the venue,
  and record both the divergence and the correction.
- **FR-053**: Discrepancies that cannot be resolved automatically MUST be escalated to the user
  and to support, and order routing for the affected account MUST be held until settled.
- **FR-054**: The platform MUST record an audit entry for every connection change, order
  transition, risk verdict, mandate change, kill-switch change, and reconciliation outcome.
- **FR-055**: Users and support MUST be able to retrieve the complete chain for any order:
  origin, risk verdict and inputs, confirmation, submission, venue responses, fills, and final
  state.
- **FR-056**: Support and administrative surfaces MUST show connection health, permissions, and
  sanitized error history without exposing credentials or secret material.
- **FR-057**: Error responses MUST remain user-friendly and MUST NOT expose internal
  architecture, stack traces, credential values, or raw venue payloads containing secrets.
- **FR-058**: The platform MUST erase or pseudonymize a user's trading data on an account
  erasure request, subject to legally required retention of execution records.

### Key Entities *(include if feature involves data)*

- **Venue**: A supported broker or exchange, described by the capabilities and order types it
  offers and the environments it exposes.
- **Venue Connection**: A user's link to one venue account, with environment, granted
  capabilities, health, and a reference to the securely stored credential.
- **Venue Account**: The account behind a connection — balance, equity, margin, leverage,
  currency, and last sync state.
- **Instrument**: A tradable symbol with its per-venue specification: asset class, quantity
  bounds and step, price precision, session schedule, and tradability.
- **Quote**: A latest observed price for an instrument at a venue, with observation time and
  freshness state.
- **Price History Series**: A sequence of aggregated price bars for an instrument, timeframe,
  and venue, with gaps marked.
- **Order Intent**: A proposed order awaiting review and confirmation, holding the exact terms,
  the risk verdict, the estimated cost, and an expiry.
- **Order**: A transmitted order with its client identifier, venue identifier, terms, state,
  and complete transition history.
- **Fill**: A single execution against an order, with quantity, price, fees, and venue
  execution identifier.
- **Position**: A current holding in an instrument with direction, quantity, average entry,
  unrealized result, and protective levels.
- **Risk Policy**: A user's set of risk limits governing what orders may be sent.
- **Risk Verdict**: The recorded outcome of evaluating one order against the risk policy,
  including rules, values, and decision.
- **Automation Mandate**: A user's scoped, expiring delegation permitting orders without
  per-order confirmation.
- **Kill Switch**: A user-level or operator-level halt on new orders.
- **Paper Account**: A simulated account with starting balance, fill assumptions, and reset
  history.
- **Reconciliation Run**: A comparison of Atlas's view against a venue's, with discrepancies,
  classifications, and resolutions.

## Assumptions

- Users already hold their own accounts at the venues they connect; Atlas does not open,
  fund, or broker accounts, and holds no client money.
- MetaTrader 5, OANDA, Binance, Bybit, and Interactive Brokers are the named in-scope venues;
  the venue contract is deliberately generic so additional venues are configuration and an
  adapter, not a redesign.
- Forex and crypto are the primary asset classes for launch; the instrument model does not
  preclude others.
- Credentials are stored, rotated, and revoked by the existing credential vault from Spec 01;
  this specification consumes that capability and does not re-implement it.
- Market data is sourced from the user's connected venues for launch; dedicated market data
  vendors are a later option and must not change the freshness contract.
- Venue clocks, symbol naming, and instrument specifications differ per venue and must be
  normalized by Atlas rather than pushed onto the user.
- Execution records may be subject to regulatory retention that overrides immediate deletion.
- Atlas is a decision-support and execution tool, not an investment adviser; the product makes
  no suitability determination in this specification.

## Out of Scope

- AI agents, the manager agent, and agent-initiated trading decisions (the mandate and origin
  model exists so they can arrive safely later).
- The visual strategy builder and backtesting engine.
- Portfolio analytics, performance attribution, and reporting beyond the position, order, and
  fill views defined here.
- The trade journal as a product feature.
- Notifications and alerting as a product feature; this specification only emits the events
  that a future notification capability consumes.
- Copy trading, social trading, and any multi-account order allocation.
- Custody, funding, deposits, withdrawals, and payments.
- Tax reporting.
- Market data redistribution to third parties, and vendor-licensed data feeds.
- Options, futures roll handling, and multi-leg or bracket order strategies beyond a single
  order with attached protective levels.
- Regulatory licensing, best-execution reporting, and jurisdiction-specific compliance
  workflows.

## Dependencies

- Spec 00 platform foundation — modules, routing, configuration, event log, background jobs,
  observability, and error taxonomy.
- Spec 01 authentication and security — user identity, roles and permissions, step-up
  verification for sensitive actions, the credential vault used for all venue credentials,
  audit log, and the account-erasure contract.
- External broker and exchange interfaces and their operational availability, permissions
  models, and rate limits.
- A reliable time reference for session, expiry, and daily-window rules.
- Future specs that will consume this capability: agents, strategy builder, journal,
  portfolio analytics, and notifications.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A trader can connect a supported venue in demo mode and see their account
  balance and positions in under 5 minutes, without support assistance.
- **SC-002**: Live prices for subscribed instruments reach the trader within 1 second of
  observation at the venue for 95% of updates, and any data older than its freshness limit is
  visibly marked stale rather than displayed as current.
- **SC-003**: Account, position, and order state matches the venue's own reported state for
  99.9% of reconciliation checks, and every mismatch is detected, classified, and recorded.
- **SC-004**: 95% of confirmed orders are transmitted to the venue within 500 milliseconds of
  confirmation, excluding venue response time.
- **SC-005**: No order is ever transmitted more than once: duplicate confirmations and client
  retries produce exactly one venue order in 100% of tested cases.
- **SC-006**: No order can be transmitted without either an explicit human confirmation or an
  active scoped mandate, and no order can be transmitted that breaches the risk policy — both
  demonstrated as having no bypass path.
- **SC-007**: When required data is stale, missing, or a venue is unreachable, the platform
  refuses the order and recommends waiting in 100% of tested cases, rather than proceeding.
- **SC-008**: A trader can engage the kill switch and have all new orders refused within
  1 second, while cancelling and closing remain available.
- **SC-009**: For any order, a trader or support agent can retrieve its complete chain —
  origin, risk verdict, confirmation, submission, venue responses, fills, final state — in
  under 1 minute.
- **SC-010**: A trader can complete a full paper-trading cycle — order, fill, position, close,
  reset — with no venue credentials, and paper state is never presented as real performance.
- **SC-011**: Venue credentials never appear in any client response, log, export, or support
  surface, verified by automated checks.
- **SC-012**: The platform sustains 1,000 concurrent traders with active subscriptions and
  order flow without exceeding any venue's rate limits or degrading the stated latency
  targets.
- **SC-013**: A new venue can be added by implementing the venue contract alone, with no change
  to order, risk, or reconciliation behavior, demonstrated by the reference simulated venue
  plus at least two real venues passing one shared conformance suite.
