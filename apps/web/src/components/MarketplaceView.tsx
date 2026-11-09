"use client";

import React, { useState } from "react";
import { StrategyBacktestModal, TradingStrategyDef } from "./StrategyBacktestModal";
import { ZapIcon, CloseIcon } from "./Icons";

export function MarketplaceView() {
  const [strategies, setStrategies] = useState<TradingStrategyDef[]>([
    {
      id: "strat-deep-momentum",
      name: "Deep Momentum Alpha",
      category: "MOMENTUM",
      author: "Atlas Core Labs",
      version: "v4.2.1",
      sharpeRatio: 2.84,
      winRatePct: 68.4,
      maxDrawdownPct: 4.2,
      return30dPct: 18.2,
      activePairs: ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
      executionMode: "LIVE",
      allocatedCapitalUsd: 25000,
      status: "ACTIVE",
      description: "High-frequency momentum and trend-continuation engine with dynamic volatility trailing stop-loss.",
      logicSummary: [
        "Entry: 15m volume surge > 1.8x moving average + EMA 20/50 bullish alignment.",
        "Exit: Parabolic SAR flip or structural trailing stop breach.",
        "Risk: 1.5% capital budget per execution with dynamic 1.5x ATR stops.",
      ],
    },
    {
      id: "strat-smc-hunter",
      name: "SMC Liquidity Hunter",
      category: "SMC",
      author: "Quantitative Institutional Desk",
      version: "v2.8.0",
      sharpeRatio: 3.12,
      winRatePct: 72.0,
      maxDrawdownPct: 3.8,
      return30dPct: 24.5,
      activePairs: ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
      executionMode: "LIVE",
      allocatedCapitalUsd: 35000,
      status: "ACTIVE",
      description: "Identifies Fair Value Gaps (FVG), order blocks, and institutional liquidity sweeps during London/NY sessions.",
      logicSummary: [
        "Entry: Sweeps of Asian session high/low followed by 15m Fair Value Gap (FVG) retest.",
        "Target: Opposing pool of uncollected buy/sell side liquidity (minimum 1:2.8 R:R).",
        "Risk: Strict invalidation beyond the sweep wick origin.",
      ],
    },
    {
      id: "strat-stat-arb",
      name: "Statistical Arbitrage Sentinel",
      category: "ARBITRAGE",
      author: "High-Frequency Signals Group",
      version: "v3.1.5",
      sharpeRatio: 4.20,
      winRatePct: 91.5,
      maxDrawdownPct: 1.1,
      return30dPct: 11.8,
      activePairs: ["BTC/USDT", "ETH/USDT", "BNB/USDT"],
      executionMode: "PAPER",
      allocatedCapitalUsd: 20000,
      status: "ACTIVE",
      description: "Captures basis spreads between spot order books and perpetual swap funding rate disparities.",
      logicSummary: [
        "Delta-neutral execution across Binance and Bybit order books.",
        "Collects 8-hour funding rates while holding perfectly hedged long spot / short perp.",
        "Immediate auto-unwind if spread diverges beyond 0.35%.",
      ],
    },
    {
      id: "strat-vol-grid",
      name: "Dynamic Volatility Grid",
      category: "GRID",
      author: "Atlas Core Labs",
      version: "v1.9.0",
      sharpeRatio: 2.15,
      winRatePct: 64.2,
      maxDrawdownPct: 5.5,
      return30dPct: 14.1,
      activePairs: ["SOL/USDT", "BNB/USDT", "XRP/USDT"],
      executionMode: "PAPER",
      allocatedCapitalUsd: 15000,
      status: "PAUSED",
      description: "Adaptive geometric grid bot that widens and tightens grid spacing dynamically according to ATR (Average True Range).",
      logicSummary: [
        "Dynamically recalibrates grid lines on 4h ATR shifts.",
        "Captures chop and oscillations in sideways market conditions.",
        "Hard circuit-breaker stop if market breaks outside the 2.5-sigma Bollinger Band.",
      ],
    },
  ]);

  const [inspectStrategy, setInspectStrategy] = useState<TradingStrategyDef | null>(null);
  const [backtestStrategy, setBacktestStrategy] = useState<TradingStrategyDef | null>(null);

  const toggleStatus = (id: string) => {
    setStrategies((prev) =>
      prev.map((s) => (s.id === id ? { ...s, status: s.status === "ACTIVE" ? "PAUSED" : "ACTIVE" } : s))
    );
  };

  const toggleMode = (id: string) => {
    setStrategies((prev) =>
      prev.map((s) => (s.id === id ? { ...s, executionMode: s.executionMode === "LIVE" ? "PAPER" : "LIVE" } : s))
    );
  };

  const handleDeployBacktestedStrategy = (strategyId: string, allocatedCapital: number) => {
    setStrategies((prev) =>
      prev.map((s) =>
        s.id === strategyId
          ? { ...s, status: "ACTIVE", allocatedCapitalUsd: allocatedCapital }
          : s
      )
    );
  };

  const totalAllocated = strategies.reduce((acc, s) => acc + (s.status === "ACTIVE" ? s.allocatedCapitalUsd : 0), 0);
  const activeCount = strategies.filter((s) => s.status === "ACTIVE").length;

  const getCategoryColor = (cat: string) => {
    switch (cat) {
      case "MOMENTUM":
        return { color: "#38bdf8", bg: "rgba(56, 189, 248, 0.12)", border: "rgba(56, 189, 248, 0.25)" };
      case "SMC":
        return { color: "#a855f7", bg: "rgba(168, 85, 247, 0.12)", border: "rgba(168, 85, 247, 0.25)" };
      case "ARBITRAGE":
        return { color: "#10b981", bg: "rgba(16, 185, 129, 0.12)", border: "rgba(16, 185, 129, 0.25)" };
      default:
        return { color: "#f59e0b", bg: "rgba(245, 158, 11, 0.12)", border: "rgba(245, 158, 11, 0.25)" };
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", gap: "8px", overflow: "hidden" }}>
      {/* Top Marketplace Telemetry Header */}
      <div
        style={{
          background: "var(--bg-surface)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "8px",
          padding: "10px 16px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexShrink: 0,
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "14px", fontWeight: 800, color: "var(--text-primary)", letterSpacing: "0.2px" }}>
              INSTITUTIONAL STRATEGY MARKETPLACE
            </span>
            <span
              style={{
                fontSize: "10px",
                fontWeight: 700,
                color: "#10b981",
                background: "rgba(16, 185, 129, 0.12)",
                border: "1px solid rgba(16, 185, 129, 0.25)",
                padding: "2px 8px",
                borderRadius: "4px",
              }}
            >
              4 ALGORITHMIC ENGINES
            </span>
          </div>
          <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
            Deploy autonomous algorithmic bots with real-time risk controls and verified Binance historical backtests.
          </span>
        </div>

        {/* Global Summary Stats & Fast Backtest Button */}
        <div style={{ display: "flex", alignItems: "center", gap: "18px", fontSize: "11px" }} className="tabular-nums">
          <div>
            <span style={{ color: "var(--text-muted)", display: "block", fontSize: "9px" }}>ACTIVE ENGINES</span>
            <span style={{ color: "#10b981", fontWeight: 800, fontSize: "14px" }}>
              {activeCount} / {strategies.length}
            </span>
          </div>
          <div>
            <span style={{ color: "var(--text-muted)", display: "block", fontSize: "9px" }}>TOTAL CAPITAL DEPLOYED</span>
            <span style={{ color: "var(--text-primary)", fontWeight: 800, fontSize: "14px" }}>
              ${totalAllocated.toLocaleString()}
            </span>
          </div>
          <div>
            <span style={{ color: "var(--text-muted)", display: "block", fontSize: "9px" }}>WEIGHTED SHARPE</span>
            <span style={{ color: "var(--accent-blue)", fontWeight: 800, fontSize: "14px" }}>
              3.15
            </span>
          </div>

          <button
            onClick={() => setBacktestStrategy(strategies[0]!)}
            style={{
              background: "var(--bg-surface-elevated)",
              border: "1px solid var(--border-subtle)",
              color: "var(--text-primary)",
              borderRadius: "4px",
              padding: "5px 12px",
              fontSize: "11px",
              fontWeight: 600,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              transition: "border-color 0.15s ease",
            }}
          >
            <ZapIcon size={12} color="var(--accent-blue)" />
            <span>Historical Backtester</span>
          </button>
        </div>
      </div>

      {/* Strategies Grid */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
          gap: "10px",
        }}
      >
        {strategies.map((strat) => {
          const catStyle = getCategoryColor(strat.category);

          return (
            <div
              key={strat.id}
              style={{
                background: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "8px",
                padding: "14px",
                display: "flex",
                flexDirection: "column",
                gap: "10px",
                opacity: strat.status === "ACTIVE" ? 1 : 0.75,
                transition: "all 0.2s ease",
              }}
            >
              {/* Header */}
              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{ fontSize: "13px", fontWeight: 800, color: "var(--text-primary)" }}>{strat.name}</span>
                    <span
                      style={{
                        fontSize: "9px",
                        fontFamily: "var(--font-mono)",
                        color: catStyle.color,
                        background: catStyle.bg,
                        border: `1px solid ${catStyle.border}`,
                        padding: "1px 5px",
                        borderRadius: "3px",
                      }}
                    >
                      {strat.category}
                    </span>
                    <span style={{ fontSize: "9px", color: "#64748b" }}>{strat.version}</span>
                  </div>
                  <span style={{ fontSize: "10px", color: "#64748b" }}>by {strat.author}</span>
                </div>

                {/* Status and Mode Pills */}
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <span
                    onClick={() => toggleMode(strat.id)}
                    title="Click to toggle Paper / Live"
                    style={{
                      fontSize: "9px",
                      fontWeight: 700,
                      color: strat.executionMode === "LIVE" ? "#10b981" : "#f59e0b",
                      background: strat.executionMode === "LIVE" ? "rgba(16, 185, 129, 0.12)" : "rgba(245, 158, 11, 0.12)",
                      border: `1px solid ${strat.executionMode === "LIVE" ? "rgba(16, 185, 129, 0.25)" : "rgba(245, 158, 11, 0.25)"}`,
                      padding: "2px 6px",
                      borderRadius: "3px",
                      cursor: "pointer",
                    }}
                  >
                    {strat.executionMode}
                  </span>

                  <button
                    onClick={() => toggleStatus(strat.id)}
                    style={{
                      background: strat.status === "ACTIVE" ? "var(--accent-green)" : "var(--bg-surface-elevated)",
                      color: strat.status === "ACTIVE" ? "#05160e" : "var(--text-muted)",
                      border: "none",
                      borderRadius: "3px",
                      padding: "2px 8px",
                      fontSize: "10px",
                      fontWeight: 800,
                      cursor: "pointer",
                    }}
                  >
                    {strat.status}
                  </button>
                </div>
              </div>

              {/* Description */}
              <div style={{ fontSize: "11px", color: "var(--text-secondary)", lineHeight: "16px" }}>
                {strat.description}
              </div>

              {/* Telemetry Metrics Grid */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr 1fr 1fr",
                  gap: "6px",
                  background: "var(--bg-surface-elevated)",
                  border: "1px solid var(--border-subtle)",
                  padding: "8px",
                  borderRadius: "6px",
                  textAlign: "center",
                }}
                className="tabular-nums"
              >
                <div>
                  <span style={{ display: "block", fontSize: "9px", color: "var(--text-muted)" }}>30D RETURN</span>
                  <span style={{ color: "var(--accent-green)", fontWeight: 800, fontSize: "12px" }}>+{strat.return30dPct}%</span>
                </div>
                <div>
                  <span style={{ display: "block", fontSize: "9px", color: "var(--text-muted)" }}>WIN RATE</span>
                  <span style={{ color: "var(--text-primary)", fontWeight: 700, fontSize: "12px" }}>{strat.winRatePct}%</span>
                </div>
                <div>
                  <span style={{ display: "block", fontSize: "9px", color: "var(--text-muted)" }}>SHARPE</span>
                  <span style={{ color: "var(--accent-blue)", fontWeight: 700, fontSize: "12px" }}>{strat.sharpeRatio}</span>
                </div>
                <div>
                  <span style={{ display: "block", fontSize: "9px", color: "var(--text-muted)" }}>MAX DD</span>
                  <span style={{ color: "var(--accent-red)", fontWeight: 700, fontSize: "12px" }}>-{strat.maxDrawdownPct}%</span>
                </div>
              </div>

              {/* Active Pairs */}
              <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "10px" }}>
                <span style={{ color: "var(--text-muted)" }}>Active Pools:</span>
                <div style={{ display: "flex", gap: "4px" }}>
                  {strat.activePairs.map((p) => (
                    <span
                      key={p}
                      style={{
                        background: "var(--bg-surface-elevated)",
                        border: "1px solid var(--border-subtle)",
                        color: "var(--text-secondary)",
                        padding: "1px 6px",
                        borderRadius: "3px",
                        fontFamily: "var(--font-mono)",
                        fontSize: "9px",
                      }}
                    >
                      {p}
                    </span>
                  ))}
                </div>
              </div>

              {/* Footer: Capital Allocation & Backtest / Inspect Buttons */}
              <div
                style={{
                  marginTop: "auto",
                  paddingTop: "8px",
                  borderTop: "1px solid var(--border-subtle)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <span style={{ fontSize: "10px", color: "var(--text-muted)" }} className="tabular-nums">
                  Allocated: <strong style={{ color: "var(--text-primary)" }}>${strat.allocatedCapitalUsd.toLocaleString()}</strong>
                </span>

                <div style={{ display: "flex", gap: "6px" }}>
                  <button
                    onClick={() => setInspectStrategy(strat)}
                    style={{
                      background: "transparent",
                      border: "1px solid var(--border-subtle)",
                      color: "var(--text-secondary)",
                      borderRadius: "4px",
                      padding: "3px 8px",
                      fontSize: "10px",
                      fontWeight: 600,
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.color = "#f8fafc")}
                    onMouseLeave={(e) => (e.currentTarget.style.color = "#94a3b8")}
                  >
                    Rules
                  </button>

                  <button
                    onClick={() => setBacktestStrategy(strat)}
                    style={{
                      background: "rgba(255, 255, 255, 0.04)",
                      border: "1px solid var(--border-subtle)",
                      color: "#cbd5e1",
                      borderRadius: "4px",
                      padding: "3px 8px",
                      fontSize: "10px",
                      fontWeight: 600,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "4px",
                    }}
                  >
                    <ZapIcon size={10} color="#cbd5e1" />
                    <span>Backtest</span>
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Inspect Strategy Rules Modal */}
      {inspectStrategy && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(4, 6, 11, 0.8)",
            backdropFilter: "blur(10px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
          }}
          onClick={() => setInspectStrategy(null)}
        >
          <div
            style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border-medium)",
              borderRadius: "10px",
              boxShadow: "var(--card-shadow)",
              padding: "18px",
              width: "500px",
              maxWidth: "92vw",
              display: "flex",
              flexDirection: "column",
              gap: "12px",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "14px", fontWeight: 800, color: "var(--text-primary)" }}>
                {inspectStrategy.name} ({inspectStrategy.version})
              </span>
              <button
                onClick={() => setInspectStrategy(null)}
                style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer", display: "flex", alignItems: "center" }}
              >
                <CloseIcon size={14} color="var(--text-muted)" />
              </button>
            </div>

            <div style={{ fontSize: "11px", color: "var(--text-secondary)", lineHeight: "16px" }}>
              {inspectStrategy.description}
            </div>

            <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--accent-blue)", marginTop: "4px" }}>
              CORE EXECUTION & RISK LOGIC
            </div>
            <ul style={{ margin: 0, paddingLeft: "16px", fontSize: "11px", color: "var(--text-primary)", lineHeight: "20px" }}>
              {inspectStrategy.logicSummary.map((rule, idx) => (
                <li key={idx}>{rule}</li>
              ))}
            </ul>

            <div style={{ display: "flex", gap: "8px", marginTop: "6px" }}>
              <button
                onClick={() => {
                  const s = inspectStrategy;
                  setInspectStrategy(null);
                  setBacktestStrategy(s);
                }}
                style={{
                  flex: 1,
                  background: "var(--bg-surface-elevated)",
                  border: "1px solid var(--border-subtle)",
                  color: "var(--text-primary)",
                  borderRadius: "4px",
                  padding: "8px 0",
                  fontSize: "11px",
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "6px",
                }}
              >
                <ZapIcon size={12} color="var(--accent-blue)" />
                <span>Run Real Binance Backtest</span>
              </button>
              <button
                onClick={() => setInspectStrategy(null)}
                style={{
                  background: "rgba(255, 255, 255, 0.04)",
                  border: "1px solid rgba(255, 255, 255, 0.08)",
                  color: "#94a3b8",
                  borderRadius: "5px",
                  padding: "8px 14px",
                  fontSize: "11px",
                  cursor: "pointer",
                }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Real Historical Strategy Backtester Modal */}
      {backtestStrategy && (
        <StrategyBacktestModal
          strategy={backtestStrategy}
          onClose={() => setBacktestStrategy(null)}
          onDeployStrategy={handleDeployBacktestedStrategy}
        />
      )}
    </div>
  );
}
