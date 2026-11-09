"""Dialectic debate engine coordinating Bull vs. Bear adversarial analysis (Spec 05 §2, §5)."""

from __future__ import annotations

from typing import Any
from atlas_api.modules.decision.domain.models import DebateTranscript


def run_dialectic_debate(
    symbol: str,
    direction: str,
    market_metrics: dict[str, Any] | None = None,
) -> DebateTranscript:
    """Simulates adversarial debate between Bull and Bear agents with synthesis arbitration."""
    if direction.upper() in ("BUY", "LONG"):
        bull_args = (
            f"Strong liquidity sweep on {symbol} 1h timeframe confirms institutional accumulation.",
            "Bullish RSI divergence present across both 15m and 1h charts.",
            "Spot ETF net inflows positive for 3 consecutive days.",
        )
        bear_args = (
            f"Overhead resistance at major daily order block has rejected price twice.",
            "Derivatives funding rate is elevated (+0.01%), signaling potential long squeeze risk.",
            "High-impact US CPI report scheduled within 24 hours.",
        )
        synthesis = (
            f"Arbitrator verdict: Bull case holds statistical edge provided entry is taken on a retest of support. "
            f"Position size must be reduced by 25% due to approaching CPI release volatility."
        )
    else:
        bull_args = (
            f"Price is testing oversold territory on {symbol} with heavy buyer volume on dips.",
            "Macro dollar index (DXY) showing signs of exhaustion.",
        )
        bear_args = (
            f"Breakdown below key swing low establishes clean bearish market structure on {symbol}.",
            "On-chain exchange inflows surged by 1,800 BTC indicating imminent spot selling pressure.",
            "Open interest dropping with declining price confirms aggressive distribution.",
        )
        synthesis = (
            f"Arbitrator verdict: Bearish continuation favored. Set invalidation stop loss above the breakdown order block."
        )

    return DebateTranscript(
        bull_arguments=bull_args,
        bear_arguments=bear_args,
        arbitrator_synthesis=synthesis,
        identified_fallacies=("Confirmation bias: Ignore minor lower timeframe bounce without 1h confirmation.",),
    )
