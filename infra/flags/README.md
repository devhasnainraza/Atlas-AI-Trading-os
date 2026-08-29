# Feature flags

`flags.json` is the GitOps-managed flag file. Point a service at it with:

```
ATLAS_FEATURE_FLAGS_FILE=infra/flags/flags.json
```

`atlas_core.feature_flags.FileFlagProvider` re-reads the file when its mtime changes, so a flag
flip takes effect without a redeploy. `POST /v1/platform/feature-flags/sync` forces a re-read for
changes that land inside the filesystem's mtime resolution.

## Rules

- **Unknown flag ⇒ caller's default.** Every `is_enabled` call passes an explicit default, and a
  missing key resolves to it. That is why the defaults in code are fail-closed: an operator
  deleting a line must never widen what the platform permits.
- **Every real-money venue is `false` here and `false` in code.** `venue.paper.enabled` is the
  only venue that ships on, because a paper book cannot lose money.
- **`trading.live_orders.enabled` is one of two switches.** Live transmission also requires
  `TRADING_LIVE_ORDERS_ENABLED=true`. Both must agree; the flag exists so transmission can be
  stopped in seconds during an incident, which a redeploy cannot do.

## Flags

| Flag | Default | Effect when false |
| --- | --- | --- |
| `sample.guarded_capability` | `false` | Sample module's guarded endpoint returns disabled. |
| `venue.paper.enabled` | `true` | Paper venue cannot be used. |
| `venue.mt5.enabled` | `false` | MT5 connections rejected with `ATLAS-TRD-002`. |
| `venue.oanda.enabled` | `false` | OANDA connections rejected with `ATLAS-TRD-002`. |
| `venue.binance.enabled` | `false` | Binance connections rejected with `ATLAS-TRD-002`. |
| `venue.bybit.enabled` | `false` | Bybit connections rejected with `ATLAS-TRD-002`. |
| `venue.ibkr.enabled` | `false` | IBKR connections rejected with `ATLAS-TRD-002`. |
| `trading.live_orders.enabled` | `false` | No order reaches a live venue, whatever the config says. |
| `trading.reconciliation.enabled` | `true` | Reconciliation runs are skipped — leaves drift undetected, so only turn this off to stop a runaway loop. |
| `marketdata.streaming.enabled` | `true` | Quote streams are not opened; REST snapshots only. |

## Kill switches are not flags

An engaged kill switch is stored state with an actor, a reason, and a timestamp, and it outranks
every other check including an automation mandate. Flags gate *capabilities*; a kill switch stops
*trading*. Do not add one here.
