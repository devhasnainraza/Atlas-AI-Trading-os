<!--
Sync Impact Report
==================
Version change: 1.0.0 → 2.0.0
Rationale: Major amendment to formalize the Autonomous AI Hedge Fund architecture:
- Zero-Trust Broker & Exchange API Vault (AES-256-GCM + KMS)
- 24/7 Autonomous Multi-Agent Swarm loop
- Interactive Two-Way WhatsApp & Telegram Conversational Trading
- Mandatory Human-in-the-Loop (HITL) Execution Consent Gate ("Trade execute kar dun? YES/NO")
- Social Media Broadcast & Privacy Sanitization Guards
- Automated Risk Gate Supremacy & Capital Preservation Invariants

Modified principles:
- Principle I (Human First) expanded with mandatory HITL Execution Consent contract
- Principle II (Security First) expanded with Zero-Trust API Key Vault & withdrawal prohibition
- Principle IV (Multi-Agent Collaboration) expanded with 24/7 Swarm and Chief Manager role
- Principle VIII (Privacy by Design) expanded with Social Media Sanitization Guard
Added sections:
- Omnichannel Protocol (WhatsApp / Telegram / Push)
- Capital Protection & Risk Gate Invariants
-->

# Atlas AI Trading OS Constitution

## Mission

Build the world's most secure, intelligent, and trustworthy Autonomous AI Trading Operating System.
Atlas empowers traders by running an autonomous 24/7 multi-agent swarm that scans markets, analyzes order flow, monitors macro catalysts, communicates seamlessly via WhatsApp, Telegram, and Web, and executes institutional-grade strategies on connected broker APIs **exclusively with explicit human consent**.

---

## Core Principles

### I. Human First & The Mandatory Execution Consent Gate

1. **Assistance, Not Usurpation:** The AI assists, analyzes, and drafts orders, but human agency is sovereign.
2. **The Final Consent Contract:** No real-capital market order shall ever be dispatched to a broker or exchange API without explicit, uncoerced human confirmation.
   - The Chief Manager Agent MUST present a structured trade proposal containing: Symbol, Side, Entry Price, Stop-Loss, Multi-Tier Take-Profit targets, Maximum Capital at Risk ($ and %), and Conviction Score.
   - The prompt MUST conclude with an unambiguous consent request:
     `"Kya main aapke broker account par yeh trade execute kar dun? [YES / NO]"`
   - Execution is strictly blocked until the user confirms (via WhatsApp reply, Telegram button, or Web Cockpit click).
3. **Emergency Override:** The user retains an unconditional right to trigger an instant **EMERGENCY FLATTEN** or pause any running autonomous bot at any time across any channel.

---

### II. Security First & The Zero-Trust API Vault

1. **Bank-Grade Envelope Encryption:** All broker and exchange API keys, secrets, and passphrases MUST be encrypted at rest using AES-256-GCM authenticated envelope encryption backed by a Key Management Service (KMS) or hardware security module.
2. **Strict Withdrawal Disallowance:** The system MUST validate incoming API keys upon connection. Any API key that contains "Withdrawal" or "Fund Transfer" permissions MUST be rejected immediately. The system ONLY operates with Read and Spot/Futures/Margin Trading permissions.
3. **Zero Client-Side Exposure:** Raw API credentials MUST never touch client-side browsers, mobile viewports, or local storage. All exchange requests are signed and dispatched exclusively by hardened backend vault workers.
4. **Static IP Whitelisting:** The platform provides dedicated, redundant static IP addresses so users can lock their exchange API keys to Atlas egress nodes only.
5. **No Secrets in Logs:** Secrets, JWT tokens, and API signatures MUST NEVER appear in application logs, database traces, or prompt histories.

---

### III. 24/7 Autonomous Multi-Agent Swarm

1. **Continuous Market Vigilance:** Specialized AI agents run 24 hours a day, 7 days a week in asynchronous event loops:
   - **Market Analyst Agent:** Real-time price action, Fair Value Gaps (FVG), order blocks, and market structure.
   - **Quantitative & Momentum Agent:** Algorithmic indicators, volume profile, VWAP bands, RSI/MACD divergences.
   - **Whale & Sentiment Scraper Agent:** On-chain whale transactions, exchange netflows, social sentiment (Twitter/X, Reddit, Fear & Greed).
   - **Macro & News Sentinel Agent:** Economic calendars (CPI, FOMC, Non-Farm Payrolls), geopolitical breaking alerts, and central bank statements.
   - **Risk Manager Agent:** Position sizing, account margin health, correlation exposure, and portfolio drawdown monitoring.
2. **The Chief Manager Agent (Orchestrator):** Individual agents do NOT execute trades independently. All agent insights flow into the Chief Manager Agent, which synthesizes deliberative consensus, filters out low-conviction noise, and drafts institutional trade proposals.

---

### IV. Omnichannel Two-Way Communication (WhatsApp, Telegram, Web)

1. **Conversational Copilot:** Users can interact with their Atlas trading instance natively via WhatsApp Business API, Telegram Bot, or the Web Cockpit.
2. **Natural Language Queries:** The system MUST understand natural user inquiries in Roman Urdu and English (e.g., *"BTC ka kya view hai?"*, *"Aaj ka net PnL dikhao"*, *"Risk per trade 1% kardo"*).
3. **Real-Time Push Alerts:** High-priority market shifts, triggered price alerts, and macro catalyst warnings are instantly delivered to the user's preferred messaging channel.
4. **Interactive Trade Approval:** Trade proposals sent to WhatsApp or Telegram feature direct interactive buttons (`[YES, EXECUTE]` / `[NO, ABORT]`) allowing instant 1-tap authorization from anywhere in the world.

---

### V. Social Media Integrations & Privacy Sanitization Guard

1. **Automated Market Dispatches:** The Chief Manager Agent can be authorized to publish automated market debriefs, technical analyses, and educational trade setups to public or private channels (Twitter/X, Discord server, Telegram community channel).
2. **The Privacy Sanitization Guard (Strict Invariant):**
   - Public social posts MUST NEVER disclose private portfolio balances, account equity, exact dollar sizes, user identity, or sensitive broker credentials.
   - Only percentage returns (e.g., `+3.4%`, `2.8 R:R`), technical chart patterns, and educational setup theses may be published.

---

### VI. Risk Gate Supremacy & Capital Preservation

1. **Survival Precedes Profit:** Capital preservation is the absolute highest priority. When a risk invariant conflicts with an attractive profit signal, the Risk Gate wins unconditionally.
2. **Daily Drawdown Circuit Breaker:** If realized or unrealized daily loss hits the user's defined ceiling (e.g., 3% of account balance), the platform halts all active bots, prevents new orders, and alerts the user.
3. **Deterministic Multi-Tier Exits (Spec 06):**
   - **TP1:** Closes 50% of position size upon hitting target and automatically moves Stop-Loss to Breakeven (entry + spread/commissions).
   - **TP2:** Closes 25% of position and locks trailing stop.
   - **TP3:** 25% runner trails with dynamic 1.5x ATR volatility bands to capture outsized market trends.
4. **News Blackout Shield:** Automated bots pause order submission 15 minutes before and after High-Impact macro events (FOMC, CPI, NFP) to protect from extreme slippage and spread widening.

---

### VII. Explainability & Radical Transparency

1. **Four-Part Justification Mandate:** Every trade recommendation MUST provide:
   - **Confidence Score:** Quantified conviction level (e.g., 91%).
   - **Concrete Evidence:** Specific technical, on-chain, or macro catalysts.
   - **Identified Invalidation Point:** The exact price level where the thesis is proven false (hard Stop-Loss).
   - **Alternative Scenarios:** What occurs if the market breaks opposing structure.
2. **No Black Boxes:** Recommendations without clear, auditable reasoning are rejected by the Chief Manager Agent.

---

### VIII. Continuous Learning & Reflexion

1. **Automated Trade Journaling:** Every executed trade is automatically recorded with entry time, exit time, setup tags, PnL, and deliberation logs.
2. **AI Reflexion Loop:** When a trade hits Stop-Loss, the AI performs an automated post-mortem: Was the rule followed? Was there unexpected slippage? Did whale liquidity front-run the level? Insights compound to improve future consensus without violating user privacy.

---

### IX. Fail-Safe Reliability

1. **Graceful Degradation:** If exchange websockets disconnect or external APIs experience outages, the system transitions to safe mode, cancels unconfirmed intents, and notifies the user immediately.
2. **Inaction Over Recklessness:** In financial markets, missing a trade is infinitely better than entering an erroneous one. When data is ambiguous, the system's default state is patient inaction.

---

## Governance & Ratification

This Constitution is the supreme architectural document of the Atlas AI Trading OS. Any new feature, pull request, agent prompt, or backend service MUST adhere strictly to these principles.

- **Human-in-the-Loop Consent is Non-Negotiable.**
- **Zero-Trust Credential Security is Absolute.**
- **Risk Gate Invariants cannot be bypassed by any AI Agent.**

**Version**: 2.0.0 | **Ratified**: 2026-09-23 | **Status**: ACTIVE & BINDING
