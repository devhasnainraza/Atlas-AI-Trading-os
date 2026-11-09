"use client";

import React, { useState } from "react";
import { DownloadIcon, ZapIcon, PlusIcon, TrashIcon, RefreshIcon, CheckIcon, CloseIcon } from "./Icons";
import { soundManager } from "../lib/soundEffects";

export interface JournalTrade {
  id: string;
  time: string;
  symbol: string;
  side: "LONG" | "SHORT";
  entryPrice: number;
  exitPrice: number;
  sizeStr: string;
  pnlUsd: number;
  pnlPct: number;
  tags: string[];
  notes?: string;
  status: "CLOSED" | "FLATTENED";
}

interface TradeJournalViewProps {
  balance: number;
  closedTrades: JournalTrade[];
  onReloadTrades?: () => void;
  onNavigateToCockpit?: () => void;
}

const AVAILABLE_TAGS = ["A+ Setup", "Rule Followed", "FVG Retest", "FOMO", "Chased Entry", "Revenge", "Scale-Out"];

export function TradeJournalView({
  balance,
  closedTrades,
  onReloadTrades,
  onNavigateToCockpit,
}: TradeJournalViewProps) {
  const [journalTab, setJournalTab] = useState<"executions" | "chains">("executions");
  const [filterOutcome, setFilterOutcome] = useState<"ALL" | "WINS" | "LOSSES">("ALL");
  const [tradesList, setTradesList] = useState<JournalTrade[]>(closedTrades);
  const [isLogModalOpen, setIsLogModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Manual Log Trade form state
  const [logSymbol, setLogSymbol] = useState("BTC/USDT");
  const [logSide, setLogSide] = useState<"LONG" | "SHORT">("LONG");
  const [logEntryPrice, setLogEntryPrice] = useState("86000");
  const [logExitPrice, setLogExitPrice] = useState("87500");
  const [logSizeStr, setLogSizeStr] = useState("0.25 BTC");
  const [logTags, setLogTags] = useState<string[]>(["Rule Followed", "A+ Setup"]);

  const decisionChains = [
    {
      id: "chain-8842",
      symbol: "BTC/USDT",
      time: "19:58:12",
      action: "BUY",
      market_state: "BTC $67,240.00 | Spread 1.2 bps | 24h Vol 18,400.5 | Regime: EXPANSION_BULLISH",
      agent_observations: "Market Agent: CVD buy ratio +18% absorption. News Agent: Net ETF inflow +$450M, zero news embargo.",
      decision: "Decision Agent: Proposed LONG $67,100-$67,300 (82.5% conviction). Critic Agent: Enforced SL at $66,400.",
      risk_assessment: "Risk Agent: Passed (1.25% equity risk, $125). Policy Engine: Passed (whitelisted crypto venue).",
      user_approval: "TICKET-8842-BTC: Approved by human trader with cryptographic token ed25519-sig-8f92b4.",
      execution: "Execution Agent: Routed to Binance Spot Adapter. Order ID: ORD-BIN-88210. Fill: $67,240.00 (0.15 BTC).",
      result: "Realized Exit: $68,400.00 | Net PnL: +$174.00 | R-Multiple: 1.39R | Outcome: TP1 Tagged.",
    },
    {
      id: "chain-8840",
      symbol: "ETH/USDT",
      time: "17:15:00",
      action: "BUY",
      market_state: "ETH $3,520.00 | Spread 0.8 bps | Regime: RANGE_EXPANSION",
      agent_observations: "Market Agent: FVG liquidity sweep on 15m. News Agent: Ethereum gas burns stabilizing.",
      decision: "Decision Agent: Proposed LONG $3,510 (78.0%). Critic Agent: Challenged $3,580 resistance.",
      risk_assessment: "Risk Agent: Passed (1.10% risk). Policy Engine: Cleared.",
      user_approval: "TICKET-8840-ETH: Approved by trader.",
      execution: "Execution Agent: Filled on Bybit Perp Adapter @ $3,520.00.",
      result: "Realized Exit: $3,575.00 | Net PnL: +$110.00 | R-Multiple: 1.25R | Outcome: Trail Hit.",
    },
  ];

  // Sync internal trades list when prop updates
  React.useEffect(() => {
    setTradesList(closedTrades);
  }, [closedTrades]);

  const toggleTag = async (tradeId: string, tag: string) => {
    soundManager.playClick();
    const trade = tradesList.find((t) => t.id === tradeId);
    if (!trade) return;

    const has = trade.tags.includes(tag);
    const updatedTags = has ? trade.tags.filter((x) => x !== tag) : [...trade.tags, tag];

    setTradesList((prev) =>
      prev.map((t) => (t.id === tradeId ? { ...t, tags: updatedTags } : t))
    );

    try {
      await fetch("/api/journal", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tradeId, tags: updatedTags }),
      });
    } catch {}
  };

  const handleExportCSV = () => {
    soundManager.playClick();
    const headers = "ID,Time,Symbol,Side,Size,EntryPrice,ExitPrice,PnL_USD,PnL_Pct,Status,Tags\n";
    const rows = tradesList
      .map(
        (t) =>
          `${t.id},"${t.time}",${t.symbol},${t.side},"${t.sizeStr}",${t.entryPrice},${t.exitPrice},${t.pnlUsd},${t.pnlPct}%,${t.status},"${t.tags.join(";")}"`
      )
      .join("\n");
    const blob = new Blob([headers + rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `atlas_trade_journal_${Date.now()}.csv`;
    a.click();
  };

  const handleSeedSampleTrades = async () => {
    soundManager.playClick();
    setIsSubmitting(true);
    try {
      const res = await fetch("/api/journal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "SEED" }),
      });
      if (res.ok) {
        soundManager.playOrderFilled();
        if (onReloadTrades) onReloadTrades();
      }
    } catch {
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClearJournal = async () => {
    if (!confirm("Are you sure you want to clear your trade journal? This will delete all recorded executions.")) return;
    soundManager.playClick();
    try {
      await fetch("/api/journal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "CLEAR" }),
      });
      setTradesList([]);
      if (onReloadTrades) onReloadTrades();
    } catch {}
  };

  const handleSaveManualTrade = async (e: React.FormEvent) => {
    e.preventDefault();
    soundManager.playClick();
    setIsSubmitting(true);

    const entry = parseFloat(logEntryPrice) || 0;
    const exit = parseFloat(logExitPrice) || 0;
    const diff = logSide === "LONG" ? exit - entry : entry - exit;
    const pnlPct = entry > 0 ? (diff / entry) * 100 : 0;

    let pnlUsd = 0;
    if (logSymbol.includes("BTC")) pnlUsd = diff * 0.25;
    else if (logSymbol.includes("ETH")) pnlUsd = diff * 2.5;
    else if (logSymbol.includes("SOL")) pnlUsd = diff * 25;
    else pnlUsd = diff * 10;

    const now = new Date();
    const timeStr = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`;

    const newTrade: JournalTrade = {
      id: "tr-man-" + Date.now(),
      time: timeStr,
      symbol: logSymbol,
      side: logSide,
      entryPrice: entry,
      exitPrice: exit,
      sizeStr: logSizeStr,
      pnlUsd: parseFloat(pnlUsd.toFixed(2)),
      pnlPct: parseFloat(pnlPct.toFixed(2)),
      tags: logTags,
      status: "CLOSED",
    };

    try {
      const res = await fetch("/api/journal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trade: newTrade }),
      });
      if (res.ok) {
        soundManager.playOrderFilled();
        setTradesList((prev) => [newTrade, ...prev]);
        setIsLogModalOpen(false);
        if (onReloadTrades) onReloadTrades();
      }
    } catch {
    } finally {
      setIsSubmitting(false);
    }
  };

  // Telemetry Calculations
  const totalTrades = tradesList.length;
  const wins = tradesList.filter((t) => t.pnlUsd > 0);
  const losses = tradesList.filter((t) => t.pnlUsd < 0);
  const winRate = totalTrades > 0 ? ((wins.length / totalTrades) * 100).toFixed(1) : "0.0";
  const totalNetPnl = tradesList.reduce((acc, t) => acc + t.pnlUsd, 0);
  const grossWin = wins.reduce((acc, t) => acc + t.pnlUsd, 0);
  const grossLoss = Math.abs(losses.reduce((acc, t) => acc + t.pnlUsd, 0));
  const profitFactor = grossLoss > 0 ? (grossWin / grossLoss).toFixed(2) : grossWin > 0 ? "MAX" : "0.00";

  // Filtered rows
  const displayedTrades = tradesList.filter((t) => {
    if (filterOutcome === "WINS") return t.pnlUsd > 0;
    if (filterOutcome === "LOSSES") return t.pnlUsd < 0;
    return true;
  });

  // Calculate cumulative equity points for SVG chart
  let runningEquity = balance - totalNetPnl;
  const equityPoints = [runningEquity, ...tradesList.slice().reverse().map((t) => {
    runningEquity += t.pnlUsd;
    return runningEquity;
  })];

  const minEq = Math.min(...equityPoints);
  const maxEq = Math.max(...equityPoints);
  const rangeEq = Math.max(maxEq - minEq, 100);

  const svgW = 600;
  const svgH = 100;
  const polylinePoints = equityPoints
    .map((val, idx) => {
      const x = (idx / Math.max(equityPoints.length - 1, 1)) * svgW;
      const y = svgH - ((val - minEq) / rangeEq) * (svgH - 20) - 10;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", gap: "8px", overflow: "hidden" }}>
      {/* Top Journal Telemetry Bar */}
      <div
        style={{
          background: "var(--bg-surface-card)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "6px",
          padding: "10px 14px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexShrink: 0,
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "13px", fontWeight: 700, color: "#fff", letterSpacing: "0.02em" }}>
              BEHAVIORAL TRADE JOURNAL & AUDIT
            </span>
            <span
              style={{
                fontSize: "10px",
                fontWeight: 600,
                color: totalTrades > 0 ? "var(--accent-green)" : "var(--text-muted)",
                background: totalTrades > 0 ? "rgba(34, 197, 94, 0.12)" : "var(--bg-surface)",
                padding: "2px 8px",
                borderRadius: "4px",
                border: totalTrades > 0 ? "1px solid rgba(34, 197, 94, 0.2)" : "1px solid var(--border-subtle)",
              }}
            >
              {totalTrades} EXECUTIONS RECORDED
            </span>
          </div>
          <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
            Track edge decay, behavioral tags, and equity curve telemetry across all algorithmic & discretionary trades.
          </span>
        </div>

        {/* Action Buttons */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <button
            onClick={() => setIsLogModalOpen(true)}
            style={{
              background: "rgba(56, 189, 248, 0.12)",
              border: "1px solid rgba(56, 189, 248, 0.3)",
              color: "#38bdf8",
              borderRadius: "4px",
              padding: "6px 12px",
              fontSize: "11px",
              fontWeight: 700,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <PlusIcon size={12} color="#38bdf8" />
            Log Execution
          </button>

          {totalTrades === 0 && (
            <button
              onClick={handleSeedSampleTrades}
              disabled={isSubmitting}
              style={{
                background: "rgba(34, 197, 94, 0.12)",
                border: "1px solid rgba(34, 197, 94, 0.3)",
                color: "#22c55e",
                borderRadius: "4px",
                padding: "6px 12px",
                fontSize: "11px",
                fontWeight: 700,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              <ZapIcon size={12} color="#22c55e" />
              Load Sample Trades
            </button>
          )}

          {totalTrades > 0 && (
            <button
              onClick={handleClearJournal}
              style={{
                background: "rgba(239, 68, 68, 0.1)",
                border: "1px solid rgba(239, 68, 68, 0.25)",
                color: "#ef4444",
                borderRadius: "4px",
                padding: "6px 10px",
                fontSize: "11px",
                fontWeight: 600,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "4px",
              }}
            >
              <TrashIcon size={12} color="#ef4444" />
              Clear
            </button>
          )}

          <button
            onClick={handleExportCSV}
            disabled={totalTrades === 0}
            style={{
              background: "var(--bg-surface-elevated)",
              border: "1px solid var(--border-subtle)",
              color: totalTrades === 0 ? "var(--text-muted)" : "var(--text-main)",
              borderRadius: "4px",
              padding: "6px 12px",
              fontSize: "11px",
              fontWeight: 600,
              cursor: totalTrades === 0 ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              opacity: totalTrades === 0 ? 0.5 : 1,
            }}
          >
            <DownloadIcon size={12} color="var(--text-muted)" />
            Export CSV
          </button>
        </div>
      </div>

      {/* 4 Summary Metric Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: "8px", flexShrink: 0 }}>
        <div style={{ background: "var(--bg-surface-card)", border: "1px solid var(--border-subtle)", borderRadius: "6px", padding: "10px", textAlign: "center" }} className="tabular-nums">
          <span style={{ display: "block", fontSize: "10px", color: "var(--text-muted)", fontWeight: 600 }}>CUMULATIVE NET PNL</span>
          <span style={{ fontSize: "16px", fontWeight: 700, color: totalNetPnl >= 0 ? "var(--accent-green)" : "var(--accent-red)" }}>
            {totalNetPnl >= 0 ? "+" : ""}${totalNetPnl.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </div>
        <div style={{ background: "var(--bg-surface-card)", border: "1px solid var(--border-subtle)", borderRadius: "6px", padding: "10px", textAlign: "center" }} className="tabular-nums">
          <span style={{ display: "block", fontSize: "10px", color: "var(--text-muted)", fontWeight: 600 }}>WIN RATE</span>
          <span style={{ fontSize: "16px", fontWeight: 700, color: parseFloat(winRate) >= 60 ? "var(--accent-green)" : "var(--accent-blue)" }}>
            {winRate}% ({wins.length}W / {losses.length}L)
          </span>
        </div>
        <div style={{ background: "var(--bg-surface-card)", border: "1px solid var(--border-subtle)", borderRadius: "6px", padding: "10px", textAlign: "center" }} className="tabular-nums">
          <span style={{ display: "block", fontSize: "10px", color: "var(--text-muted)", fontWeight: 600 }}>PROFIT FACTOR</span>
          <span style={{ fontSize: "16px", fontWeight: 700, color: "var(--accent-blue)" }}>
            {profitFactor}
          </span>
        </div>
        <div style={{ background: "var(--bg-surface-card)", border: "1px solid var(--border-subtle)", borderRadius: "6px", padding: "10px", textAlign: "center" }} className="tabular-nums">
          <span style={{ display: "block", fontSize: "10px", color: "var(--text-muted)", fontWeight: 600 }}>ACCOUNT CAPITAL</span>
          <span style={{ fontSize: "16px", fontWeight: 700, color: "#fff" }}>
            ${balance.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </div>
      </div>

      {/* Middle: Cumulative Equity Curve SVG Graph */}
      <div
        style={{
          background: "var(--bg-surface-card)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "6px",
          padding: "10px 14px",
          display: "flex",
          flexDirection: "column",
          gap: "4px",
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "10px", color: "var(--text-muted)", fontWeight: 600 }}>
          <span>PORTFOLIO EQUITY CURVE (NET REALIZED GROWTH)</span>
          <span style={{ color: "var(--accent-green)", fontWeight: 600 }}>HIGH WATER MARK: ${maxEq.toLocaleString()}</span>
        </div>
        <div style={{ height: "100px", width: "100%", position: "relative" }}>
          {totalTrades === 0 ? (
            <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted)", fontSize: "11px" }}>
              Baseline Equity: ${balance.toLocaleString()} · No closed trades recorded yet
            </div>
          ) : (
            <svg width="100%" height="100%" viewBox={`0 0 ${svgW} ${svgH}`} preserveAspectRatio="none">
              <defs>
                <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--accent-green)" stopOpacity="0.2" />
                  <stop offset="100%" stopColor="var(--accent-green)" stopOpacity="0.0" />
                </linearGradient>
              </defs>
              <polyline
                fill="none"
                stroke="var(--accent-green)"
                strokeWidth="2"
                points={polylinePoints}
              />
            </svg>
          )}
        </div>
      </div>

      {/* Bottom: Filterable Trade Log Table */}
      <div
        style={{
          flex: 1,
          minHeight: 0,
          background: "var(--bg-surface-card)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "6px",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        {/* Table Filter Header */}
        <div
          style={{
            padding: "8px 12px",
            borderBottom: "1px solid var(--border-subtle)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            fontSize: "11px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div style={{ display: "flex", gap: "4px" }}>
              <button
                onClick={() => setJournalTab("executions")}
                style={{
                  background: journalTab === "executions" ? "var(--bg-surface-elevated)" : "transparent",
                  color: journalTab === "executions" ? "#fff" : "var(--text-muted)",
                  border: journalTab === "executions" ? "1px solid var(--border-medium)" : "1px solid transparent",
                  borderRadius: "4px",
                  padding: "3px 10px",
                  fontSize: "10px",
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                EXECUTIONS LOG
              </button>
              <button
                onClick={() => setJournalTab("chains")}
                style={{
                  background: journalTab === "chains" ? "var(--bg-surface-elevated)" : "transparent",
                  color: journalTab === "chains" ? "var(--accent-blue)" : "var(--text-muted)",
                  border: journalTab === "chains" ? "1px solid var(--accent-blue)" : "1px solid transparent",
                  borderRadius: "4px",
                  padding: "3px 10px",
                  fontSize: "10px",
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                AI DECISION CHAINS (7-STAGE)
              </button>
            </div>

            {journalTab === "executions" && (
              <div style={{ display: "flex", gap: "4px" }}>
                {(["ALL", "WINS", "LOSSES"] as const).map((fo) => (
                  <button
                    key={fo}
                    onClick={() => setFilterOutcome(fo)}
                    style={{
                      background: filterOutcome === fo ? "var(--bg-surface-elevated)" : "transparent",
                      color: filterOutcome === fo ? "#fff" : "var(--text-muted)",
                      border: filterOutcome === fo ? "1px solid var(--border-medium)" : "1px solid transparent",
                      borderRadius: "4px",
                      padding: "2px 8px",
                      fontSize: "10px",
                      fontWeight: 600,
                      cursor: "pointer",
                    }}
                  >
                    {fo}
                  </button>
                ))}
              </div>
            )}
          </div>
          <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>
            {journalTab === "executions" ? "Click tags to toggle classification" : "Audit trail: Market state → Result"}
          </span>
        </div>

        {/* Table Content */}
        <div style={{ flex: 1, overflowY: "auto" }}>
          {journalTab === "chains" ? (
            <div style={{ padding: "12px", display: "flex", flexDirection: "column", gap: "12px" }}>
              {decisionChains.map((c) => (
                <div
                  key={c.id}
                  style={{
                    background: "var(--bg-surface-elevated)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "6px",
                    padding: "12px 14px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "8px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span style={{ fontWeight: 800, color: "var(--accent-blue)", fontSize: "12px" }}>{c.id}</span>
                      <span style={{ fontWeight: 700, color: "#fff", fontSize: "12px" }}>{c.symbol}</span>
                      <span style={{ fontSize: "10px", fontWeight: 700, color: "var(--accent-green)", background: "rgba(34, 197, 94, 0.15)", padding: "1px 6px", borderRadius: "3px" }}>
                        {c.action}
                      </span>
                    </div>
                    <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>{c.time} UTC</span>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "4px", fontSize: "11px", color: "var(--text-secondary)" }}>
                    <div><strong style={{ color: "#60a5fa" }}>1. Market State:</strong> {c.market_state}</div>
                    <div><strong style={{ color: "#a78bfa" }}>2. Observations:</strong> {c.agent_observations}</div>
                    <div><strong style={{ color: "#f472b6" }}>3. Decision:</strong> {c.decision}</div>
                    <div><strong style={{ color: "#f87171" }}>4. Risk Assessment:</strong> {c.risk_assessment}</div>
                    <div><strong style={{ color: "#facc15" }}>5. User Approval:</strong> {c.user_approval}</div>
                    <div><strong style={{ color: "#4ade80" }}>6. Execution:</strong> {c.execution}</div>
                    <div><strong style={{ color: "#22d3ee" }}>7. Result:</strong> {c.result}</div>
                  </div>
                </div>
              ))}
            </div>
          ) : displayedTrades.length === 0 ? (
            <div style={{ height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "40px 20px", textAlign: "center" }}>
              <div style={{ width: "44px", height: "44px", borderRadius: "50%", background: "rgba(56, 189, 248, 0.1)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: "12px" }}>
                <ZapIcon size={20} color="#38bdf8" />
              </div>
              <div style={{ fontSize: "14px", fontWeight: 700, color: "#fff", marginBottom: "4px" }}>
                No Trade Executions Recorded Yet
              </div>
              <p style={{ fontSize: "12px", color: "var(--text-muted)", maxWidth: "420px", margin: "0 auto 16px" }}>
                When positions are filled and closed in the Cockpit or via Autonomous Agents, their trade post-mortem and behavioral metrics are automatically recorded here.
              </p>
              <div style={{ display: "flex", gap: "10px" }}>
                <button
                  onClick={handleSeedSampleTrades}
                  disabled={isSubmitting}
                  style={{
                    background: "rgba(34, 197, 94, 0.15)",
                    border: "1px solid rgba(34, 197, 94, 0.35)",
                    color: "#22c55e",
                    fontSize: "12px",
                    fontWeight: 700,
                    padding: "8px 16px",
                    borderRadius: "6px",
                    cursor: "pointer",
                  }}
                >
                  Load Sample Trades
                </button>
                <button
                  onClick={() => setIsLogModalOpen(true)}
                  style={{
                    background: "rgba(56, 189, 248, 0.15)",
                    border: "1px solid rgba(56, 189, 248, 0.35)",
                    color: "#38bdf8",
                    fontSize: "12px",
                    fontWeight: 700,
                    padding: "8px 16px",
                    borderRadius: "6px",
                    cursor: "pointer",
                  }}
                >
                  Log Manual Trade
                </button>
                {onNavigateToCockpit && (
                  <button
                    onClick={onNavigateToCockpit}
                    style={{
                      background: "var(--bg-surface-elevated)",
                      border: "1px solid var(--border-subtle)",
                      color: "var(--text-main)",
                      fontSize: "12px",
                      fontWeight: 600,
                      padding: "8px 16px",
                      borderRadius: "6px",
                      cursor: "pointer",
                    }}
                  >
                    Go to Cockpit
                  </button>
                )}
              </div>
            </div>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border-subtle)", color: "var(--text-muted)", textAlign: "left", fontSize: "9px" }}>
                  <th style={{ padding: "6px 12px" }}>TIME</th>
                  <th style={{ padding: "6px 12px" }}>SYMBOL</th>
                  <th style={{ padding: "6px 12px" }}>SIDE</th>
                  <th style={{ padding: "6px 12px" }}>SIZE</th>
                  <th style={{ padding: "6px 12px" }}>ENTRY</th>
                  <th style={{ padding: "6px 12px" }}>EXIT</th>
                  <th style={{ padding: "6px 12px" }}>PNL ($ / %)</th>
                  <th style={{ padding: "6px 12px" }}>STATUS</th>
                  <th style={{ padding: "6px 12px" }}>BEHAVIORAL TAGS</th>
                </tr>
              </thead>
              <tbody>
                {displayedTrades.map((t) => (
                  <tr key={t.id} style={{ borderBottom: "1px solid var(--border-subtle)" }} className="tabular-nums">
                    <td style={{ padding: "6px 12px", color: "var(--text-muted)" }}>{t.time}</td>
                    <td style={{ padding: "6px 12px", fontWeight: 600, color: "#fff" }}>{t.symbol}</td>
                    <td style={{ padding: "6px 12px", fontWeight: 700, color: t.side === "LONG" ? "var(--accent-green)" : "var(--accent-red)" }}>
                      {t.side}
                    </td>
                    <td style={{ padding: "6px 12px", color: "var(--text-main)" }}>{t.sizeStr}</td>
                    <td style={{ padding: "6px 12px", color: "var(--text-muted)" }}>${t.entryPrice.toLocaleString()}</td>
                    <td style={{ padding: "6px 12px", color: "var(--text-main)" }}>${t.exitPrice.toLocaleString()}</td>
                    <td
                      style={{
                        padding: "6px 12px",
                        fontWeight: 700,
                        color: t.pnlUsd >= 0 ? "var(--accent-green)" : "var(--accent-red)",
                      }}
                    >
                      {t.pnlUsd >= 0 ? "+" : ""}${t.pnlUsd.toFixed(2)} ({t.pnlPct >= 0 ? "+" : ""}{t.pnlPct.toFixed(2)}%)
                    </td>
                    <td style={{ padding: "6px 12px" }}>
                      <span
                        style={{
                          fontSize: "9px",
                          fontWeight: 600,
                          color: t.status === "CLOSED" ? "var(--accent-green)" : "var(--accent-blue)",
                          background: t.status === "CLOSED" ? "rgba(34, 197, 94, 0.1)" : "rgba(59, 130, 246, 0.1)",
                          border: `1px solid ${t.status === "CLOSED" ? "rgba(34, 197, 94, 0.2)" : "rgba(59, 130, 246, 0.2)"}`,
                          padding: "1px 5px",
                          borderRadius: "3px",
                        }}
                      >
                        {t.status}
                      </span>
                    </td>
                    <td style={{ padding: "6px 12px" }}>
                      <div style={{ display: "flex", gap: "4px", flexWrap: "wrap" }}>
                        {AVAILABLE_TAGS.map((tag) => {
                          const isSelected = t.tags.includes(tag);
                          return (
                            <span
                              key={tag}
                              onClick={() => toggleTag(t.id, tag)}
                              style={{
                                cursor: "pointer",
                                fontSize: "9px",
                                padding: "1px 6px",
                                borderRadius: "3px",
                                background: isSelected ? "rgba(59, 130, 246, 0.15)" : "var(--bg-surface-elevated)",
                                color: isSelected ? "var(--accent-blue)" : "var(--text-muted)",
                                border: isSelected ? "1px solid rgba(59, 130, 246, 0.4)" : "1px solid var(--border-subtle)",
                                userSelect: "none",
                              }}
                            >
                              {tag}
                            </span>
                          );
                        })}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Manual Trade Entry Modal */}
      {isLogModalOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.75)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
            padding: "16px",
          }}
          onClick={() => setIsLogModalOpen(false)}
        >
          <div
            style={{
              width: "480px",
              maxWidth: "100%",
              background: "var(--bg-surface)",
              border: "1px solid var(--border-medium)",
              borderRadius: "10px",
              padding: "20px",
              boxShadow: "var(--card-shadow)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <PlusIcon size={14} color="var(--accent-blue)" />
                <span style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)" }}>Log Execution to Journal</span>
              </div>
              <button
                onClick={() => setIsLogModalOpen(false)}
                style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
              >
                <CloseIcon size={14} color="currentColor" />
              </button>
            </div>

            <form onSubmit={handleSaveManualTrade} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "10px", fontWeight: 700, color: "var(--text-muted)", marginBottom: "4px" }}>
                    SYMBOL
                  </label>
                  <select
                    value={logSymbol}
                    onChange={(e) => setLogSymbol(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "8px 10px",
                      background: "var(--bg-surface-elevated)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "5px",
                      color: "var(--text-primary)",
                      fontSize: "12px",
                    }}
                  >
                    <option value="BTC/USDT">BTC/USDT</option>
                    <option value="ETH/USDT">ETH/USDT</option>
                    <option value="SOL/USDT">SOL/USDT</option>
                    <option value="BNB/USDT">BNB/USDT</option>
                    <option value="XRP/USDT">XRP/USDT</option>
                    <option value="EUR/USD">EUR/USD</option>
                    <option value="XAU/USD">XAU/USD</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "10px", fontWeight: 700, color: "var(--text-muted)", marginBottom: "4px" }}>
                    DIRECTION
                  </label>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px" }}>
                    <button
                      type="button"
                      onClick={() => setLogSide("LONG")}
                      style={{
                        padding: "8px",
                        background: logSide === "LONG" ? "rgba(34,197,94,0.15)" : "var(--bg-surface-elevated)",
                        border: logSide === "LONG" ? "1px solid #22c55e" : "1px solid var(--border-subtle)",
                        color: logSide === "LONG" ? "#22c55e" : "var(--text-secondary)",
                        borderRadius: "5px",
                        fontWeight: 700,
                        fontSize: "11px",
                        cursor: "pointer",
                      }}
                    >
                      LONG
                    </button>
                    <button
                      type="button"
                      onClick={() => setLogSide("SHORT")}
                      style={{
                        padding: "8px",
                        background: logSide === "SHORT" ? "rgba(239,68,68,0.15)" : "var(--bg-surface-elevated)",
                        border: logSide === "SHORT" ? "1px solid #ef4444" : "1px solid var(--border-subtle)",
                        color: logSide === "SHORT" ? "#ef4444" : "var(--text-secondary)",
                        borderRadius: "5px",
                        fontWeight: 700,
                        fontSize: "11px",
                        cursor: "pointer",
                      }}
                    >
                      SHORT
                    </button>
                  </div>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "10px", fontWeight: 700, color: "var(--text-muted)", marginBottom: "4px" }}>
                    ENTRY PRICE ($)
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={logEntryPrice}
                    onChange={(e) => setLogEntryPrice(e.target.value)}
                    required
                    style={{
                      width: "100%",
                      padding: "8px 10px",
                      background: "var(--bg-surface-elevated)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "5px",
                      color: "var(--text-primary)",
                      fontSize: "12px",
                    }}
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "10px", fontWeight: 700, color: "var(--text-muted)", marginBottom: "4px" }}>
                    EXIT PRICE ($)
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={logExitPrice}
                    onChange={(e) => setLogExitPrice(e.target.value)}
                    required
                    style={{
                      width: "100%",
                      padding: "8px 10px",
                      background: "var(--bg-surface-elevated)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "5px",
                      color: "var(--text-primary)",
                      fontSize: "12px",
                    }}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "10px", fontWeight: 700, color: "var(--text-muted)", marginBottom: "4px" }}>
                  POSITION SIZE
                </label>
                <input
                  type="text"
                  value={logSizeStr}
                  onChange={(e) => setLogSizeStr(e.target.value)}
                  placeholder="e.g. 0.25 BTC or 1.50 Lots"
                  required
                  style={{
                    width: "100%",
                    padding: "8px 10px",
                    background: "var(--bg-surface-elevated)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "5px",
                    color: "var(--text-primary)",
                    fontSize: "12px",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "10px", fontWeight: 700, color: "var(--text-muted)", marginBottom: "6px" }}>
                  BEHAVIORAL TAGS
                </label>
                <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                  {AVAILABLE_TAGS.map((tag) => {
                    const active = logTags.includes(tag);
                    return (
                      <button
                        type="button"
                        key={tag}
                        onClick={() => {
                          setLogTags((prev) =>
                            active ? prev.filter((t) => t !== tag) : [...prev, tag]
                          );
                        }}
                        style={{
                          fontSize: "10px",
                          padding: "3px 8px",
                          borderRadius: "4px",
                          background: active ? "rgba(56, 189, 248, 0.2)" : "var(--bg-surface-elevated)",
                          border: active ? "1px solid #38bdf8" : "1px solid var(--border-subtle)",
                          color: active ? "#38bdf8" : "var(--text-secondary)",
                          cursor: "pointer",
                        }}
                      >
                        {tag}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "8px" }}>
                <button
                  type="button"
                  onClick={() => setIsLogModalOpen(false)}
                  style={{
                    padding: "8px 14px",
                    background: "transparent",
                    border: "1px solid #253047",
                    color: "#94a3b8",
                    borderRadius: "5px",
                    fontSize: "12px",
                    cursor: "pointer",
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  style={{
                    padding: "8px 16px",
                    background: "#38bdf8",
                    border: "none",
                    color: "#000",
                    fontWeight: 700,
                    borderRadius: "5px",
                    fontSize: "12px",
                    cursor: "pointer",
                  }}
                >
                  {isSubmitting ? "Saving..." : "Save to Journal"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
