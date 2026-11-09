# Data Model: Dashboard & Analytics

**Feature**: 09-dashboard | **Date**: 2026-09-21 | **Plan**: [plan.md](./plan.md)

Conventions per Spec 00: UUIDv7 `id` primary keys, `created_at` / `updated_at` `timestamptz`, snake_case names, enums CHECK-constrained. User preferences and watchlists carry indexed `user_id` enforcing multi-tenant isolation.

## dashboard_user_layouts

Persistent user configuration for cockpit grid layout, active widgets, and display preferences.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| user_id | uuid | FK user; unique per user |
| layout_config | jsonb | Widget positions, sizes, and visibility map |
| theme_preference | text | `DARK_OBSIDIAN | MIDNIGHT_BLUE | CYBER_NEON` |
| default_symbol | text | Initial asset loaded on chart (e.g. `BTC/USDT`, `EUR/USD`) |
| default_timeframe | text | `1m | 5m | 15m | 1h | 4h | 1d` |
| sound_effects_enabled| boolean | Audio alert chime on order fills and risk alerts |
| updated_at | timestamptz | Timestamp of last layout modification |

## dashboard_watchlists

Custom user-curated symbol watchlists for rapid asset monitoring and scanner filtering.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| user_id | uuid | FK user; indexed |
| name | text | e.g. `Forex Majors`, `Crypto Momentum`, `DeFi Runners` |
| symbols | text[] | Array of standardized symbol identifiers |
| sort_order | int | Display ordering |
| is_default | boolean | True for the user's primary startup watchlist |
| created_at | timestamptz | Creation timestamp |
| updated_at | timestamptz | Last updated timestamp |

## dashboard_scanner_presets

Saved technical screener filter criteria and opportunity detection presets.

| Field | Type | Rules |
|---|---|---|
| id | uuid | PK, UUIDv7 |
| user_id | uuid | FK user; indexed |
| name | text | e.g. `RSI Oversold + FVG`, `High RVOL Breakout` |
| filters | jsonb | Structured rules: `{ "min_rvol": 2.0, "rsi_max": 30, "timeframes": ["15m", "1h"] }` |
| alert_on_match | boolean | Emits P2 notification when new asset matches criteria |
| is_public | boolean | If true, shareable in Atlas community/marketplace |
| created_at | timestamptz | Preset creation timestamp |
