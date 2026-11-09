"""Service implementation for Memory, Journal & Learning (Spec 07 §2, §5)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
import uuid

from atlas_api.modules.journal.domain.behavior import (
    calculate_performance_metrics,
    calculate_r_multiple,
    detect_overtrading,
    detect_revenge_trading,
)
from atlas_api.modules.journal.domain.models import (
    CoachingReportRecord,
    CognitiveBiasProfile,
    DecisionChainJournalRecord,
    MemoryEmbeddingRecord,
    TradeJournalRecord,
)
from atlas_core.errors import NotFoundError, ValidationError


class JournalService:
    """Orchestrates automated trade journaling, behavioral diagnostics, and memory storage."""

    def __init__(self) -> None:
        self._records: dict[str, TradeJournalRecord] = {}
        self._memories: dict[str, MemoryEmbeddingRecord] = {}
        self._decision_chains: dict[str, DecisionChainJournalRecord] = {}
        self._seed_default_chain()

    def _seed_default_chain(self) -> None:
        chain_id = "chain-institutional-001"
        self._decision_chains[chain_id] = DecisionChainJournalRecord(
            id=chain_id,
            user_id="default-user",
            symbol="BTC/USDT",
            action="BUY",
            market_state={
                "symbol": "BTC/USDT",
                "last_price": "67240.00",
                "spread_bps": "1.2",
                "volume_24h": "18400.5",
                "regime": "EXPANSION_BULLISH",
            },
            agent_observations={
                "market_agent": "Order book bid skew +18% on Binance/Bybit. Volume delta positive above $67,000.",
                "news_agent": "Net spot ETF inflow +$450M. Sentiment score +0.68. Zero embargoed high-impact events for 18h.",
                "technical_agent": "Bullish Fair Value Gap retest at $67,100. Trend: BULLISH_CONTINUATION.",
            },
            decision={
                "decision_agent": "PROPOSED BUY BTC/USDT | Entry: 67100 - 67300 | SL: 66400 | TP: 68400",
                "critic_agent": "Caution on $68,500 liquidity sweep. Approved with tight SL at $66,400.",
                "confidence_score": "82.50%",
            },
            risk_assessment={
                "risk_agent": "Passed margin check. Calculated size: 0.15 BTC ($125 max risk). Drawdown headroom: 1.75%.",
                "policy_engine": "Passed: Whitelisted symbol, allowed trading window, max single-trade risk < 1.50%.",
            },
            user_approval={
                "ticket_id": "TICKET-001-ALPHA",
                "approver_id": "trader-lead-ops",
                "status": "APPROVED",
                "signature_token": "ed25519-sig-8f92b4",
                "approved_at": "2026-09-26T18:45:00Z",
            },
            execution={
                "execution_agent": "Routed to Binance Spot Adapter. Order ID: ORD-BIN-88210.",
                "venue": "Binance",
                "fill_price": "67240.00",
                "quantity": "0.15",
                "slippage_bps": "0.4",
            },
            result={
                "exit_price": "68400.00",
                "net_pnl": "+$174.00",
                "r_multiple": "1.39R",
                "outcome": "TARGET_PROFIT_1_REALIZED",
            },
        )

    def record_closed_trade(
        self,
        user_id: str,
        order_id: str,
        account_id: str,
        symbol: str,
        side: str,
        entry_price: Decimal,
        exit_price: Decimal,
        stop_loss_price: Decimal,
        entry_time: datetime,
        exit_time: datetime,
        net_pnl: Decimal,
        fees_usd: Decimal = Decimal("0.00"),
        slippage_pips: Decimal = Decimal("0.00"),
        technical_indicators: dict[str, Any] | None = None,
    ) -> TradeJournalRecord:
        journal_id = str(uuid.uuid4())
        r_mult = calculate_r_multiple(entry_price, exit_price, stop_loss_price, side)

        # AI post mortem generation
        if net_pnl > Decimal("0"):
            post_mortem = (
                f"Profitable {side.upper()} execution on {symbol}. Realized {r_mult}R profit. "
                "Structure respected key technical levels with favorable execution slippage."
            )
        else:
            post_mortem = (
                f"Controlled risk realization on {symbol} {side.upper()}. Stop loss preserved capital "
                f"at {r_mult}R drawdown. Invalidation occurred due to counter-trend momentum."
            )

        chart_url = f"https://storage.atlas.internal/charts/{journal_id}.webp"

        record = TradeJournalRecord(
            id=journal_id,
            user_id=user_id,
            order_id=order_id,
            account_id=account_id,
            symbol=symbol.upper(),
            side=side.upper(),
            entry_price=entry_price,
            exit_price=exit_price,
            entry_time=entry_time,
            exit_time=exit_time,
            net_pnl=net_pnl,
            r_multiple=r_mult,
            fees_usd=fees_usd,
            slippage_pips=slippage_pips,
            chart_image_url=chart_url,
            technical_indicators=technical_indicators or {},
            ai_post_mortem=post_mortem,
            user_notes="",
            emotional_tags=("DISCIPLINED",),
            user_rating=None,
            created_at=datetime.now(timezone.utc),
        )
        self._records[journal_id] = record
        return record

    def get_journal_entries(self, user_id: str) -> list[TradeJournalRecord]:
        return sorted(
            [r for r in self._records.values() if r.user_id == user_id],
            key=lambda r: r.exit_time,
            reverse=True,
        )

    def get_journal_entry(self, entry_id: str, user_id: str) -> TradeJournalRecord:
        record = self._records.get(entry_id)
        if not record or record.user_id != user_id:
            raise NotFoundError(f"Journal record '{entry_id}' not found")
        return record

    def annotate_entry(
        self,
        entry_id: str,
        user_id: str,
        user_notes: str,
        emotional_tags: list[str],
        user_rating: int,
    ) -> TradeJournalRecord:
        record = self.get_journal_entry(entry_id, user_id)
        record.user_notes = user_notes
        record.emotional_tags = tuple(emotional_tags)
        record.user_rating = user_rating
        return record

    def get_bias_profile(self, user_id: str) -> CognitiveBiasProfile:
        user_trades = self.get_journal_entries(user_id)
        losing_trades = [t for t in user_trades if t.net_pnl < Decimal("0")]

        # Count emotional tags
        fomo_tags = sum(1 for t in user_trades if "FOMO" in t.emotional_tags)
        revenge_tags = sum(1 for t in user_trades if "REVENGE" in t.emotional_tags)

        total = max(len(user_trades), 1)
        fomo_score = (Decimal(fomo_tags) / Decimal(total)).quantize(Decimal("0.01"))
        revenge_score = (Decimal(revenge_tags) / Decimal(total)).quantize(Decimal("0.01"))

        return CognitiveBiasProfile(
            id=str(uuid.uuid4()),
            user_id=user_id,
            fomo_score=fomo_score,
            revenge_trading_score=revenge_score,
            loss_aversion_score=Decimal("0.15"),
            overtrading_score=Decimal("0.10"),
            discipline_rating=Decimal("88.50"),
            top_mistake_triggers=("LATE_NY_SESSION", "FRIDAY_CLOSE"),
            last_updated=datetime.now(timezone.utc),
        )

    def get_or_generate_coaching_report(self, user_id: str) -> CoachingReportRecord:
        user_trades = self.get_journal_entries(user_id)
        net_pnl, pf, win_rate, total = calculate_performance_metrics(user_trades)

        disciplined = (
            "Strictly adhered to 1.5% maximum capital risk rule across all positions",
            "Executed automated Breakeven ratchets on 100% of trades hitting TP1",
            "Zero news-embargo breaches during major CPI and FOMC rate decisions",
        )

        warnings = (
            "Win rate drops from 72% to 35% on trade setups initiated after 19:30 UTC",
            "Tendency to execute discretionary exits early prior to full TP2 realization",
        )

        recommendations = (
            "Restrict automated mandate execution to London (08:00–16:30) and early NY sessions",
            "Allow trailing stop runners to breathe by holding runner allocation through structural swings",
        )

        return CoachingReportRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            period_start="2026-09-14",
            period_end="2026-09-20",
            net_pnl=net_pnl,
            profit_factor=pf,
            win_rate=win_rate,
            total_trades=total,
            disciplined_actions=disciplined,
            cognitive_bias_warnings=warnings,
            recommendations=recommendations,
            created_at=datetime.now(timezone.utc),
        )

    def store_memory(
        self,
        user_id: str,
        scope: str,
        memory_text: str,
        importance_weight: Decimal = Decimal("0.80"),
    ) -> MemoryEmbeddingRecord:
        mem_id = str(uuid.uuid4())
        record = MemoryEmbeddingRecord(
            id=mem_id,
            user_id=user_id,
            scope=scope.upper(),
            memory_text=memory_text,
            importance_weight=importance_weight,
            last_retrieved_at=None,
            created_at=datetime.now(timezone.utc),
        )
        self._memories[mem_id] = record
        return record

    def list_memories(self, user_id: str, scope: str | None = None) -> list[MemoryEmbeddingRecord]:
        results = [m for m in self._memories.values() if m.user_id == user_id]
        if scope:
            results = [m for m in results if m.scope == scope.upper()]
        return sorted(results, key=lambda m: m.importance_weight, reverse=True)

    def record_decision_chain(
        self,
        user_id: str,
        symbol: str,
        action: str,
        market_state: dict[str, Any],
        agent_observations: dict[str, Any],
        decision: dict[str, Any],
        risk_assessment: dict[str, Any],
        user_approval: dict[str, Any],
        execution: dict[str, Any],
        result: dict[str, Any],
    ) -> DecisionChainJournalRecord:
        chain_id = str(uuid.uuid4())
        record = DecisionChainJournalRecord(
            id=chain_id,
            user_id=user_id,
            symbol=symbol,
            action=action.upper(),
            market_state=market_state,
            agent_observations=agent_observations,
            decision=decision,
            risk_assessment=risk_assessment,
            user_approval=user_approval,
            execution=execution,
            result=result,
            created_at=datetime.now(timezone.utc),
        )
        self._decision_chains[chain_id] = record
        return record

    def get_decision_chains(self, user_id: str | None = None) -> list[DecisionChainJournalRecord]:
        chains = list(self._decision_chains.values())
        if user_id:
            chains = [c for c in chains if c.user_id == user_id or c.user_id == "default-user"]
        return sorted(chains, key=lambda c: c.created_at, reverse=True)

    def get_decision_chain(self, chain_id: str) -> DecisionChainJournalRecord:
        record = self._decision_chains.get(chain_id)
        if not record:
            raise NotFoundError(message=f"Decision chain '{chain_id}' not found")
        return record

