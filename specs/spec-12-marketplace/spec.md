# Spec 12 — AI Marketplace

**Project**: Atlas AI Trading OS  
**Status**: Ratified | **Version**: 1.0.0 | **Date**: 2026-09-21  
**Target Path**: `specs/spec-12-marketplace/`  
**Constitutional Compliance**: Core Principles I, II, VI, VIII, X, XII Verified  

---

## 1. Vision & Goals

### 1.1 System Vision
Spec 12 defines the decentralized ecosystem and creator economy for Atlas AI Trading OS: the **AI Trading Marketplace** ("The App Store for Trading Agents"). Financial markets are too dynamic for any single development team to build every niche strategy or indicator. Spec 12 establishes an open, secure, and audited marketplace where quantitative researchers, developers, and experienced traders can publish, monetize, and install custom Trading Agents, LangGraph Strategy Workflows, Technical Indicators, Prompt Packs, and Custom Dashboard Widgets.

### 1.2 Core Business & Technical Goals
- **Decentralized Strategy Ecosystem**: Discover, test, and install modular trading capabilities across six asset categories: Agents, Strategies, Indicators, Prompts, Workflows, and Custom UI Dashboards.
- **Automated Sandbox Certification & Security Audit**: Every submitted plugin undergoes automated static code analysis, dependency vulnerability scanning, sandbox execution tests, and simulated risk audits before publishing.
- **Verifiable Backtest & Forward-Test Provenance**: Plugins MUST publish verifiable historical backtests and paper-trading performance provenance; false claims or misleading marketing metrics are programmatically prevented.
- **Frictionless 1-Click Installation & Activation**: Users can install and bind marketplace agents into their personal Atlas operating system with immediate sandboxed execution.
- **Sustainable Creator Monetization Engine**: Flexible monetization models (monthly subscriptions, one-time purchases, profit-share incentives) with automated Stripe Connect payouts and transparent platform splits (e.g. 70% Creator / 30% Platform).

---

## 2. Functional Requirements

- **FR-001**: The Marketplace MUST support six distinct plugin manifest types:
  1. `Trading Agent`: Standalone specialized agent with defined capabilities and system prompts.
  2. `Strategy Graph`: Complete LangGraph workflow definition with predefined decision nodes.
  3. `Custom Indicator`: Algorithmic indicator calculation script (pure Python / WebAssembly).
  4. `Prompt Pack`: Curated, versioned prompt templates for market research and sentiment analysis.
  5. `Custom Workflow`: Multi-step automated task pipeline (e.g. Morning Routine, Weekend Journaling).
  6. `Dashboard Extension`: Custom React / Tailwind widget components.
- **FR-002**: Every plugin MUST define a standardized `AtlasPluginManifest` specifying version, dependencies, permissions requested, and supported venues.
- **FR-003**: The **Marketplace Verification Pipeline** MUST execute automated pre-publishing checks:
  - Static security analysis (AST scan forbidding unauthorized network/filesystem access).
  - Memory leak and execution timeout evaluation in isolated Docker/gVisor sandboxes.
  - Multi-year historical backtesting against historical tick datasets with maximum drawdown verification.
- **FR-004**: Users MUST be able to browse, search, filter, and inspect marketplace listings with verified reviews, star ratings, and transparent performance telemetry.
- **FR-005**: Installed marketplace agents MUST execute inside restricted Python runtime sandboxes with zero access to raw broker API keys or credentials.
- **FR-006**: The platform MUST integrate with Stripe Connect to automate creator onboarding, KYC verification, revenue collection, and automated monthly creator payouts.
- **FR-007**: The platform MUST provide version management allowing creators to publish non-breaking updates with automated rollback capabilities.

---

## 3. Non-Functional Requirements

- **NFR-001 (Plugin Sandbox Overhead)**: Sandboxed execution wrapper overhead for marketplace agents MUST NOT exceed 10ms per inference invocation.
- **NFR-002 (Installation Latency)**: 1-click plugin installation and state provisioning MUST complete in < 2 seconds.
- **NFR-003 (Marketplace Search Response)**: Algolia / pgvector hybrid search queries across marketplace listings MUST return in < 30ms at p95.
- **NFR-004 (Creator Payout Precision)**: Royalty and fee calculations MUST strictly use `Decimal` accounting with immutable financial ledgers.

---

## 4. User Stories

### US-001: Trader Installs Verified Crypto Scalping Agent (Priority: P1)
- **Given** a trader seeking an automated scalping agent for `SOL/USDT`,
- **When** they discover the "Solana Momentum Scalper" in the Marketplace with a verified 4.8-star rating and 8-month audited paper track record,
- **Then** they click "Install", select their Binance paper account, configure a 0.5% risk limit, and activate the agent in under 60 seconds.

### US-002: Quantitative Developer Publishes Strategy Graph (Priority: P1)
- **Given** a quantitative analyst creating a specialized Wyckoff Accumulation strategy graph,
- **When** they package the graph and submit it through the Creator Portal,
- **Then** the automated verification pipeline tests the graph against 3 years of historical EUR/USD ticks, validates memory safety, and publishes the listing upon passing.

### US-003: Sandboxed Agent Attempting Unauthorized Network Call is Barred (Priority: P1)
- **Given** a malicious or buggy third-party agent attempting to make an external HTTP request to an unknown IP address,
- **When** the tool call executes,
- **Then** the Atlas Sandbox interceptor immediately blocks the connection, suspends the agent instance, and alerts the platform security daemon.

---

## 5. Marketplace Architecture

```text
+-------------------------------------------------------------------------+
|                         AI Marketplace Subsystem                        |
|                                                                         |
|  +--------------------+                    +-------------------------+  |
|  |   Creator Portal   |                    | Automated Verification  |  |
|  | - Upload package   |                    | - AST security linter   |  |
|  | - Payout setup     |                    | - Backtest verification |  |
|  +---------+----------+                    | - Sandbox test runner   |  |
|            |                               +------------+------------+  |
|            v                                            |               |
|  +------------------------------------------------------+------------+  |
|  |                     Marketplace Registry & Store                  |  |
|  |         (Catalog DB -> Version Control -> Search Index)           |  |
|  +--------------------------------------+----------------------------+  |
|                                         |                               |
|        +--------------------------------+-----------------------+       |
|        |                                |                       |       |
|  +-----v--------------+      +----------v-----------+    +------v-----+ |
|  | User Installation  |      | Sandboxed Execution  |    | Stripe     | |
|  | & License Engine   |      | Runtime (gVisor/WASM)|    | Connect    | |
|  +--------------------+      +----------------------+    +------------+ |
+-------------------------------------------------------------------------+
```

---

## 6. State Design

### 6.1 Plugin Manifest Schema (`AtlasPluginManifest`)
```python
@dataclass(frozen=True)
class AtlasPluginManifest:
    plugin_id: str
    name: str
    version: str
    creator_id: str
    plugin_type: str  # AGENT | STRATEGY | INDICATOR | PROMPT | WORKFLOW | DASHBOARD
    description: str
    pricing_model: str  # FREE | ONE_TIME | SUBSCRIPTION
    price_usd: Decimal
    required_permissions: tuple[str, ...]
    supported_venues: tuple[str, ...]
    min_atlas_version: str
    signature: str  # Creator cryptographic signature
```

---

## 7. LangGraph Workflow Integration

Marketplace Strategy Graphs are instantiated as subgraphs within the host LangGraph runtime:

```text
[Host Manager Agent]
         |
         v
+------------------------------------+
| Resolve Installed Marketplace Node |
+--------------------+---------------+
                     |
                     v
+------------------------------------+
| Sandboxed Subgraph Execution       |  Executes verified creator graph
| (gVisor / Restricted Environment)  |  with pre-allocated token & risk caps
+--------------------+---------------+
                     |
                     v
+------------------------------------+
| Intercept Proposed Actions         |  All proposals routed back to host
+------------------------------------+  Pre-Trade Risk Gate before execution
```

---

## 8. Tool Specifications

### 8.1 Install Marketplace Plugin Tool (`tool_marketplace_install`)
- **Description**: Installs and provisions a verified plugin into the user's workspace.
- **Input Schema**:
  ```json
  {
    "type": "object",
    "required": ["plugin_id", "version", "target_account_id"],
    "properties": {
      "plugin_id": { "type": "string" },
      "version": { "type": "string" },
      "target_account_id": { "type": "string" }
    }
  }
  ```

---

## 9. API Specifications

### 9.1 Marketplace Endpoints
- **`GET /api/v1/marketplace/plugins`**: Lists and searches available plugins with filters.
- **`GET /api/v1/marketplace/plugins/{id}`**: Retrieves detailed listing with verified backtest curves, reviews, and manifest.
- **`POST /api/v1/marketplace/plugins/{id}/install`**: Subscribes and installs plugin.
- **`POST /api/v1/marketplace/creator/submit`**: Submits a new plugin package for automated verification.

---

## 10. Database Schema

### 10.1 Marketplace Plugins Table (`marketplace_plugins`)
```sql
CREATE TABLE marketplace_plugins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    creator_id UUID NOT NULL,
    slug VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    plugin_type VARCHAR(32) NOT NULL,
    current_version VARCHAR(32) NOT NULL,
    pricing_model VARCHAR(32) NOT NULL DEFAULT 'FREE',
    price_usd NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    status VARCHAR(32) NOT NULL DEFAULT 'IN_REVIEW', -- IN_REVIEW | APPROVED | REJECTED
    rating_avg NUMERIC(3, 2) NOT NULL DEFAULT 5.00,
    rating_count INT NOT NULL DEFAULT 0,
    install_count INT NOT NULL DEFAULT 0,
    manifest JSONB NOT NULL,
    backtest_metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_plugins_type_status ON marketplace_plugins (plugin_type, status);
```

### 10.2 User Plugin Installations Table (`marketplace_installations`)
```sql
CREATE TABLE marketplace_installations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    plugin_id UUID NOT NULL REFERENCES marketplace_plugins(id),
    installed_version VARCHAR(32) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    installed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_plugin UNIQUE (user_id, plugin_id)
);
```

---

## 11. Frontend Screens & Components

### 11.1 Marketplace Discovery App Store
- **Hero Carousel**: Featured verified agents of the month with verified Sharpe ratio and profit curves.
- **Category Filter Tabs**: "All", "Trading Agents", "Strategies", "Indicators", "Prompts", "Dashboards".
- **Product Card**: Thumbnail, Title, Creator Badge, Star Rating, Price/Month, "1-Click Install" button.

### 11.2 Plugin Detail Dossier
- Live equity backtest chart comparing strategy vs. Buy & Hold benchmark.
- Granular permission disclosure: "Requested: Market Data Read, Technical Calculation. Not Permitted: Direct Broker Execution."
- User Review section with verified purchase tags.

---

## 12. Security Requirements

- **SEC-001 (gVisor / WASM Sandboxing)**: All executable plugins run within sandboxed environments with zero host filesystem access and restricted outbound networking.
- **SEC-002 (Cryptographic Package Signing)**: Plugins are signed with creator ECDSA keys; tampering with code bundles invalidates verification.
- **SEC-003 (Pre-Trade Risk Immunity)**: Marketplace agents CANNOT bypass the platform's native Pre-Trade Risk Gate or user-configured maximum drawdown limits.

---

## 13. Testing Strategy

- **Automated Sandbox Escape Penetration Testing**: Subject plugin test harness to synthetic exploit vectors (socket creation, system call injection, environment variable reading) to confirm isolation.
- **Backtest Provenance Validation**: Verify that reported backtest performance numbers exactly match synthetic paper-engine outputs.
- **Stripe Connect Split Payout Verification**: Test financial accounting ledger ensuring 70/30 fee split calculates accurately down to the cent.

---

## 14. Deployment Plan

- **Isolated Sandbox Execution Pods**: Sandboxed container cluster dedicated exclusively to running third-party marketplace plugins with strict CPU/memory limits per instance.

---

## 15. Future Enhancements

- **Decentralized On-Chain Strategy Tokenization**: Fractional ownership and tokenized revenue sharing of quantitative trading algorithms.
- **Autonomous Strategy Tournaments**: Weekly automated algorithmic trading competitions with prize pools for top-performing creators.
