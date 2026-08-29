"""Trading and market data configuration (T004).

Fail-fast at startup, per Spec 00 FR-005/006: a bad value aborts the process naming the field
rather than surfacing as a wrong order size later.

Two conventions matter here:

* ``live_orders_enabled`` defaults to ``False``. A fresh deployment, a misread env file, or a
  missing variable all land on "cannot send real orders". Enabling live transmission is an
  explicit act (FR-046, Constitution VI).
* Money and quantity limits are ``Decimal``, never ``float``. Pydantic will coerce a string
  like ``"250000"`` to ``Decimal``; a float in the environment is still a float in binary, and
  a limit that is silently ``0.1 + 0.2`` is not a limit anyone reviewed.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class TradingSettings(BaseSettings):
    """Order lifecycle, risk defaults, and the live-order kill flag."""

    model_config = SettingsConfigDict(
        env_prefix="TRADING_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # -- The switch ------------------------------------------------------------------------
    #: Master enable for transmitting orders to real-money venues. OFF unless explicitly set.
    #: Paper and demo trading are unaffected, so the platform stays fully usable with this off.
    live_orders_enabled: bool = False

    #: Require a step-up MFA challenge before a live connection is created or a mandate granted.
    #: On by default: these two actions are what stand between an account and real money.
    require_step_up_for_live: bool = True

    # -- Intent lifecycle ------------------------------------------------------------------
    #: How long a reviewed intent stays confirmable. Short on purpose — a confirmation must
    #: authorize the terms the user actually saw, and prices move (FR-025).
    intent_ttl_seconds: int = Field(default=60, ge=5, le=900)

    #: Price drift beyond this invalidates an unconfirmed intent even inside its TTL.
    intent_max_price_drift_percent: Decimal = Field(default=Decimal("0.5"), gt=0, le=100)

    # -- Submission ------------------------------------------------------------------------
    #: Venue submit timeout. On expiry the order becomes `unresolved` — never resubmitted.
    submit_timeout_seconds: float = Field(default=10.0, gt=0, le=120)

    #: How long an order may sit `unresolved` before it becomes page-worthy.
    unresolved_alert_after_seconds: int = Field(default=300, ge=30)

    # -- Reconciliation --------------------------------------------------------------------
    reconcile_interval_seconds: int = Field(default=300, ge=30, le=86_400)
    reconcile_on_reconnect: bool = True
    account_sync_interval_seconds: int = Field(default=60, ge=5, le=3600)
    position_sync_interval_seconds: int = Field(default=30, ge=5, le=3600)

    # -- Default risk policy template (per-user policies override these) -------------------
    default_max_order_notional: Decimal | None = Field(default=None, ge=0)
    default_max_position_notional: Decimal | None = Field(default=None, ge=0)
    default_max_open_positions: int | None = Field(default=None, ge=0)
    default_max_orders_per_hour: int | None = Field(default=None, ge=0)

    # -- Paper trading ---------------------------------------------------------------------
    paper_starting_balance: Decimal = Field(default=Decimal("100000"), gt=0)
    paper_slippage_bps: Decimal = Field(default=Decimal("1"), ge=0, le=1000)
    paper_commission_bps: Decimal = Field(default=Decimal("0"), ge=0, le=1000)

    # -- Sidecars (MT5 / IBKR) -------------------------------------------------------------
    mt5_bridge_url: str | None = None
    ibkr_gateway_host: str | None = None
    ibkr_gateway_port: int | None = Field(default=None, ge=1, le=65_535)

    @field_validator(
        "intent_max_price_drift_percent",
        "default_max_order_notional",
        "default_max_position_notional",
        "paper_starting_balance",
        "paper_slippage_bps",
        "paper_commission_bps",
        mode="before",
    )
    @classmethod
    def _no_binary_floats(cls, value: object) -> object:
        """Refuse a float even though Pydantic would happily coerce one.

        ``TRADING_PAPER_STARTING_BALANCE`` arrives from the environment as a string, so this
        only fires when code constructs the settings with a float literal. That is exactly the
        mistake worth catching: ``Decimal(0.1)`` is ``0.1000000000000000055511151231257827``.
        """
        if isinstance(value, float):
            raise ValueError(
                "monetary settings must be given as a decimal string or int, not float"
            )
        return value

    @model_validator(mode="after")
    def _sidecars_configured_when_needed(self) -> TradingSettings:
        """IBKR needs host *and* port, or neither. A half-configured gateway fails at the
        first order rather than at startup, which is the wrong time to find out."""
        host, port = self.ibkr_gateway_host, self.ibkr_gateway_port
        if bool(host) != bool(port):
            raise ValueError(
                "TRADING_IBKR_GATEWAY_HOST and TRADING_IBKR_GATEWAY_PORT must be set together"
            )
        return self

    @property
    def live_trading_possible(self) -> bool:
        """Read by the risk gate. Named for what it means: not "configured", but *possible*."""
        return self.live_orders_enabled


__all__ = ["TradingSettings"]
