"use client";

import React, { useState, useEffect } from "react";
import {
  TwapOrder,
  TwapSlice,
  GridBot,
  DcaBot,
  SmartExitMandate,
  INITIAL_TWAP_ORDERS,
  INITIAL_GRID_BOTS,
  INITIAL_DCA_BOTS,
  DEFAULT_SMART_MANDATE,
} from "../lib/tradingAutomation";
import { soundManager } from "../lib/soundEffects";
import {
  ZapIcon,
  ShieldIcon,
  PlayIcon,
  PauseIcon,
  TrashIcon,
  RefreshIcon,
  SlidersIcon,
  ActivityIcon,
  TargetIcon,
  ClockIcon,
  CheckIcon,
  TrendingUpIcon,
  AlertTriangleIcon,
} from "./Icons";

interface TradingAutomationViewProps {
  balance?: number;
  equity?: number;
}

export function TradingAutomationView({
  balance = 125480.0,
  equity = 126346.0,
}: TradingAutomationViewProps) {
  const [activeSubTab, setActiveSubTab] = useState<"twap" | "grid" | "dca" | "mandates">("twap");
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 1024);
    };
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // State
  const [twapOrders, setTwapOrders] = useState<TwapOrder[]>(INITIAL_TWAP_ORDERS);
  const [selectedTwapId, setSelectedTwapId] = useState<string>("twap-01");
  const [gridBots, setGridBots] = useState<GridBot[]>(INITIAL_GRID_BOTS);
  const [dcaBots, setDcaBots] = useState<DcaBot[]>(INITIAL_DCA_BOTS);
  const [mandate, setMandate] = useState<SmartExitMandate>(DEFAULT_SMART_MANDATE);
  const [mandateSavedToast, setMandateSavedToast] = useState(false);

  // Form State for new TWAP
  const [newTwapSymbol, setNewTwapSymbol] = useState("BTC/USDT");
  const [newTwapSide, setNewTwapSide] = useState<"BUY" | "SELL">("BUY");
  const [newTwapNotional, setNewTwapNotional] = useState(25000);
  const [newTwapDuration, setNewTwapDuration] = useState(15);
  const [newTwapSlices, setNewTwapSlices] = useState(10);
  const [newTwapAlgo, setNewTwapAlgo] = useState<"TWAP" | "VWAP">("TWAP");
  const [newTwapJitter, setNewTwapJitter] = useState(true);

  // Form State for new Grid Bot
  const [newGridSymbol, setNewGridSymbol] = useState("SOL/USDT");
  const [newGridLower, setNewGridLower] = useState(115.0);
  const [newGridUpper, setNewGridUpper] = useState(135.0);
  const [newGridLevels, setNewGridLevels] = useState(8);
  const [newGridCapital, setNewGridCapital] = useState(10000);

  // Form State for new DCA Bot
  const [newDcaSymbol, setNewDcaSymbol] = useState("ETH/USDT");
  const [newDcaBaseOrder, setNewDcaBaseOrder] = useState(1500);
  const [newDcaSafetyOrder, setNewDcaSafetyOrder] = useState(3000);
  const [newDcaMaxSafety, setNewDcaMaxSafety] = useState(4);
  const [newDcaDeviation, setNewDcaDeviation] = useState(2.0);
  const [newDcaTp, setNewDcaTp] = useState(2.5);

  // Simulated live execution slice ticker for running TWAPs
  useEffect(() => {
    const interval = setInterval(() => {
      setTwapOrders((prev) =>
        prev.map((order) => {
          if (order.status !== "RUNNING" || order.filledSlices >= order.totalSlices) {
            return order;
          }

          // Random slice execution chance
          const shouldExecuteSlice = Math.random() > 0.45;
          if (!shouldExecuteSlice) return order;

          const nextSliceNum = order.filledSlices + 1;
          const remainingQty = order.totalQuantity - order.filledQuantity;
          const remainingSlices = order.totalSlices - order.filledSlices;
          const sliceQty = parseFloat((remainingQty / remainingSlices).toFixed(4));
          const priceDrift = (Math.random() - 0.49) * (order.arrivalPrice * 0.0006);
          const slicePrice = parseFloat((order.arrivalPrice + priceDrift).toFixed(2));
          const sliceNotional = parseFloat((sliceQty * slicePrice).toFixed(2));

          const newSlice: TwapSlice = {
            sliceNumber: nextSliceNum,
            timestamp: new Date().toLocaleTimeString(),
            qty: sliceQty,
            price: slicePrice,
            notional: sliceNotional,
          };

          const newFilledQty = parseFloat((order.filledQuantity + sliceQty).toFixed(4));
          const newFilledNotional = parseFloat((order.filledNotional + sliceNotional).toFixed(2));
          const newAvgPrice = parseFloat((newFilledNotional / (newFilledQty || 1)).toFixed(2));
          const isDone = nextSliceNum >= order.totalSlices;

          return {
            ...order,
            filledSlices: nextSliceNum,
            filledQuantity: newFilledQty,
            filledNotional: newFilledNotional,
            avgPrice: newAvgPrice,
            status: isDone ? "COMPLETED" : "RUNNING",
            sliceHistory: [newSlice, ...order.sliceHistory],
          };
        })
      );
    }, 4500);

    return () => clearInterval(interval);
  }, []);

  // Handlers
  const handleDeployTwap = (e: React.FormEvent) => {
    e.preventDefault();
    soundManager.playOrderSent();

    const priceSeed = newTwapSymbol.startsWith("BTC")
      ? 86230
      : newTwapSymbol.startsWith("ETH")
      ? 2745
      : 122.5;
    const estQty = parseFloat((newTwapNotional / priceSeed).toFixed(4));

    const newOrder: TwapOrder = {
      id: "twap-" + Date.now().toString().slice(-4),
      symbol: newTwapSymbol,
      side: newTwapSide,
      totalNotional: newTwapNotional,
      totalQuantity: estQty,
      filledQuantity: 0,
      filledNotional: 0,
      durationMinutes: newTwapDuration,
      totalSlices: newTwapSlices,
      filledSlices: 0,
      avgPrice: priceSeed,
      arrivalPrice: priceSeed,
      status: "RUNNING",
      createdAt: new Date().toLocaleTimeString(),
      sliceHistory: [],
    };

    setTwapOrders([newOrder, ...twapOrders]);
    setSelectedTwapId(newOrder.id);
  };

  const handleToggleTwapStatus = (id: string) => {
    soundManager.playClick();
    setTwapOrders((prev) =>
      prev.map((o) => {
        if (o.id === id) {
          const next = o.status === "RUNNING" ? "PAUSED" : "RUNNING";
          return { ...o, status: next };
        }
        return o;
      })
    );
  };

  const handleDeleteTwap = (id: string) => {
    soundManager.playClick();
    setTwapOrders((prev) => prev.filter((o) => o.id !== id));
    if (selectedTwapId === id && twapOrders.length > 1) {
      const remaining = twapOrders.filter((o) => o.id !== id);
      setSelectedTwapId(remaining[0]?.id || "");
    }
  };

  const handleDeployGrid = (e: React.FormEvent) => {
    e.preventDefault();
    soundManager.playOrderSent();

    const step = (newGridUpper - newGridLower) / (newGridLevels - 1);
    const mockOrders = Array.from({ length: newGridLevels }).map((_, i) => {
      const price = parseFloat((newGridLower + i * step).toFixed(2));
      const mid = (newGridLower + newGridUpper) / 2;
      return {
        id: `g-${Date.now()}-${i}`,
        levelIndex: i + 1,
        price,
        side: (price < mid ? "BUY" : "SELL") as "BUY" | "SELL",
        status: (Math.random() > 0.6 ? "FILLED" : "PENDING") as "PENDING" | "FILLED",
      };
    });

    const newBot: GridBot = {
      id: "grid-" + Date.now().toString().slice(-4),
      symbol: newGridSymbol,
      lowerPrice: newGridLower,
      upperPrice: newGridUpper,
      gridLevels: newGridLevels,
      investmentUsd: newGridCapital,
      realizedProfitUsd: 0,
      unrealizedPnlUsd: 0,
      gridSpreadPct: parseFloat(((step / newGridLower) * 100).toFixed(2)),
      status: "RUNNING",
      createdAt: new Date().toLocaleTimeString(),
      orders: mockOrders,
    };

    setGridBots([newBot, ...gridBots]);
  };

  const handleToggleGridStatus = (id: string) => {
    soundManager.playClick();
    setGridBots((prev) =>
      prev.map((b) => (b.id === id ? { ...b, status: b.status === "RUNNING" ? "PAUSED" : "RUNNING" } : b))
    );
  };

  const handleDeleteGrid = (id: string) => {
    soundManager.playClick();
    setGridBots((prev) => prev.filter((b) => b.id !== id));
  };

  const handleDeployDca = (e: React.FormEvent) => {
    e.preventDefault();
    soundManager.playOrderSent();

    const priceSeed = newDcaSymbol.startsWith("BTC") ? 86200 : 2740;
    const newBot: DcaBot = {
      id: "dca-" + Date.now().toString().slice(-4),
      symbol: newDcaSymbol,
      baseOrderUsd: newDcaBaseOrder,
      safetyOrderUsd: newDcaSafetyOrder,
      maxSafetyOrders: newDcaMaxSafety,
      deviationPct: newDcaDeviation,
      tpPct: newDcaTp,
      avgEntryPrice: priceSeed,
      filledOrders: 1,
      totalInvested: newDcaBaseOrder,
      status: "RUNNING",
      createdAt: new Date().toLocaleTimeString(),
    };

    setDcaBots([newBot, ...dcaBots]);
  };

  const handleToggleDcaStatus = (id: string) => {
    soundManager.playClick();
    setDcaBots((prev) =>
      prev.map((b) => (b.id === id ? { ...b, status: b.status === "RUNNING" ? "PAUSED" : "RUNNING" } : b))
    );
  };

  const handleDeleteDca = (id: string) => {
    soundManager.playClick();
    setDcaBots((prev) => prev.filter((b) => b.id !== id));
  };

  const handleSaveMandates = () => {
    soundManager.playOrderFilled();
    setMandateSavedToast(true);
    setTimeout(() => setMandateSavedToast(false), 3000);
  };

  const selectedTwap = twapOrders.find((o) => o.id === selectedTwapId) || twapOrders[0];

  // Aggregated Telemetry
  const totalAlgoVolume = twapOrders.reduce((acc, o) => acc + o.filledNotional, 0) +
    gridBots.reduce((acc, b) => acc + b.investmentUsd, 0) +
    dcaBots.reduce((acc, d) => acc + d.totalInvested, 0);

  const activeBotCount = twapOrders.filter((o) => o.status === "RUNNING").length +
    gridBots.filter((b) => b.status === "RUNNING").length +
    dcaBots.filter((d) => d.status === "RUNNING").length;

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", gap: "8px", overflow: "hidden" }}>
      {/* Top Header Metrics Ribbon */}
      <div
        className="panel"
        style={{
          padding: isMobile ? "6px 10px" : "8px 14px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: isMobile ? "wrap" : "nowrap",
          gap: "8px",
          flexShrink: 0,
        }}
      >
        <div className="scroll-x" style={{ display: "flex", alignItems: "center", gap: "14px", flex: 1, minWidth: 0 }}>
          <div>
            <div style={{ fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Trading Automation Engine
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "2px" }}>
              <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)" }}>
                Institutional Algo Suite
              </span>
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "4px",
                  background: "var(--accent-green-subtle)",
                  border: "1px solid var(--accent-green-border)",
                  borderRadius: "4px",
                  padding: "1px 6px",
                  fontSize: "10px",
                  fontWeight: 600,
                  color: "var(--accent-green)",
                }}
              >
                <span className="live-dot-green" />
                {activeBotCount} ACTIVE ENGINES
              </span>
            </div>
          </div>

          <div style={{ height: "24px", width: "1px", background: "var(--border-subtle)" }} />

          {/* Metric 1: Total Algo Notional */}
          <div>
            <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>Total Algo Capital</div>
            <div className="tabular-nums" style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-primary)" }}>
              ${totalAlgoVolume.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </div>

          <div style={{ height: "24px", width: "1px", background: "var(--border-subtle)" }} />

          {/* Metric 2: Slippage Saved */}
          <div>
            <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>Est. Slippage Saved</div>
            <div className="tabular-nums" style={{ fontSize: "12px", fontWeight: 700, color: "var(--accent-green)" }}>
              +14.8 bps <span style={{ fontSize: "10px", color: "var(--text-muted)", fontWeight: 400 }}>($1,420.50)</span>
            </div>
          </div>

          <div style={{ height: "24px", width: "1px", background: "var(--border-subtle)" }} />

          {/* Metric 3: Smart Mandates Active */}
          <div>
            <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>Risk Mandates Status</div>
            <div style={{ fontSize: "11px", fontWeight: 600, color: mandate.isActive ? "var(--accent-green)" : "var(--text-muted)", display: "flex", alignItems: "center", gap: "5px" }}>
              <ShieldIcon size={11} color={mandate.isActive ? "var(--accent-green)" : "var(--text-muted)"} />
              <span>{mandate.isActive ? "Auto-BE & 1.5x ATR ARMED" : "DISARMED"}</span>
            </div>
          </div>
        </div>

        {/* Engine Subtabs */}
        <div
          className="scroll-x"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "2px",
            background: "var(--bg-surface-card)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "5px",
            padding: "2px",
            flexShrink: 0,
          }}
        >
          <button
            onClick={() => {
              soundManager.playClick();
              setActiveSubTab("twap");
            }}
            style={{
              background: activeSubTab === "twap" ? "var(--bg-surface-elevated)" : "transparent",
              color: activeSubTab === "twap" ? "var(--text-primary)" : "var(--text-secondary)",
              border: activeSubTab === "twap" ? "1px solid var(--border-medium)" : "1px solid transparent",
              borderRadius: "3px",
              padding: "4px 10px",
              fontSize: "11px",
              fontWeight: activeSubTab === "twap" ? 600 : 500,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "5px",
            }}
          >
            <ClockIcon size={12} color="currentColor" />
            <span>TWAP / VWAP Slicer</span>
          </button>

          <button
            onClick={() => {
              soundManager.playClick();
              setActiveSubTab("grid");
            }}
            style={{
              background: activeSubTab === "grid" ? "var(--bg-surface-elevated)" : "transparent",
              color: activeSubTab === "grid" ? "var(--text-primary)" : "var(--text-secondary)",
              border: activeSubTab === "grid" ? "1px solid var(--border-medium)" : "1px solid transparent",
              borderRadius: "3px",
              padding: "4px 10px",
              fontSize: "11px",
              fontWeight: activeSubTab === "grid" ? 600 : 500,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "5px",
            }}
          >
            <ActivityIcon size={12} color="currentColor" />
            <span>Grid Trading Bot</span>
          </button>

          <button
            onClick={() => {
              soundManager.playClick();
              setActiveSubTab("dca");
            }}
            style={{
              background: activeSubTab === "dca" ? "var(--bg-surface-elevated)" : "transparent",
              color: activeSubTab === "dca" ? "var(--text-primary)" : "var(--text-secondary)",
              border: activeSubTab === "dca" ? "1px solid var(--border-medium)" : "1px solid transparent",
              borderRadius: "3px",
              padding: "4px 10px",
              fontSize: "11px",
              fontWeight: activeSubTab === "dca" ? 600 : 500,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "5px",
            }}
          >
            <ZapIcon size={12} color="currentColor" />
            <span>Smart DCA Bot</span>
          </button>

          <button
            onClick={() => {
              soundManager.playClick();
              setActiveSubTab("mandates");
            }}
            style={{
              background: activeSubTab === "mandates" ? "var(--bg-surface-elevated)" : "transparent",
              color: activeSubTab === "mandates" ? "var(--text-primary)" : "var(--text-secondary)",
              border: activeSubTab === "mandates" ? "1px solid var(--border-medium)" : "1px solid transparent",
              borderRadius: "3px",
              padding: "4px 10px",
              fontSize: "11px",
              fontWeight: activeSubTab === "mandates" ? 600 : 500,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "5px",
            }}
          >
            <SlidersIcon size={12} color="currentColor" />
            <span>Smart Exit Mandates</span>
          </button>
        </div>
      </div>

      {/* Main Automation Engine Body */}
      <div style={{ flex: 1, minHeight: 0, overflow: "hidden" }}>
        {/* SUBTAB 1: TWAP / VWAP SLICER */}
        {activeSubTab === "twap" && (
          <div style={{ height: "100%", display: "grid", gridTemplateColumns: isMobile ? "1fr" : "310px 1fr 340px", gap: "8px", overflowY: isMobile ? "auto" : "hidden", overflowX: "hidden" }}>
            {/* Column 1: Order Deployer Form */}
            <div className="panel" style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}>
              <div className="panel-header">
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <ClockIcon size={12} color="var(--text-secondary)" />
                  <span style={{ fontWeight: 600, fontSize: "11px", color: "var(--text-primary)" }}>
                    Deploy Algorithmic Slicer
                  </span>
                </div>
                <span className="kbd-badge">{newTwapAlgo}</span>
              </div>

              <form onSubmit={handleDeployTwap} style={{ padding: "12px", display: "flex", flexDirection: "column", gap: "10px", overflowY: "auto", flex: 1 }}>
                <div>
                  <label style={{ fontSize: "10.5px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                    Target Asset
                  </label>
                  <select
                    value={newTwapSymbol}
                    onChange={(e) => setNewTwapSymbol(e.target.value)}
                    style={{
                      width: "100%",
                      background: "var(--bg-surface-elevated)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "4px",
                      color: "var(--text-primary)",
                      padding: "5px 8px",
                      fontSize: "11px",
                    }}
                  >
                    <option value="BTC/USDT">BTC/USDT (Spot / Perp)</option>
                    <option value="ETH/USDT">ETH/USDT (Spot / Perp)</option>
                    <option value="SOL/USDT">SOL/USDT (Spot / Perp)</option>
                    <option value="NVDA">NVDA (Equity CFD)</option>
                  </select>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px" }}>
                  <button
                    type="button"
                    onClick={() => setNewTwapSide("BUY")}
                    style={{
                      background: newTwapSide === "BUY" ? "var(--accent-green)" : "var(--bg-surface-elevated)",
                      border: "1px solid var(--border-subtle)",
                      color: newTwapSide === "BUY" ? "#000" : "var(--text-secondary)",
                      borderRadius: "4px",
                      padding: "6px 0",
                      fontSize: "11px",
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    BUY / ACCUMULATE
                  </button>
                  <button
                    type="button"
                    onClick={() => setNewTwapSide("SELL")}
                    style={{
                      background: newTwapSide === "SELL" ? "var(--accent-red)" : "var(--bg-surface-elevated)",
                      border: "1px solid var(--border-subtle)",
                      color: newTwapSide === "SELL" ? "#fff" : "var(--text-secondary)",
                      borderRadius: "4px",
                      padding: "6px 0",
                      fontSize: "11px",
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    SELL / DISTRIBUTE
                  </button>
                </div>

                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                    <label style={{ fontSize: "10.5px", color: "var(--text-secondary)" }}>Total Notional ($)</label>
                    <span className="tabular-nums" style={{ fontSize: "10.5px", fontWeight: 600, color: "var(--text-primary)" }}>
                      ${newTwapNotional.toLocaleString()}
                    </span>
                  </div>
                  <input
                    type="number"
                    step="1000"
                    min="1000"
                    max="500000"
                    value={newTwapNotional}
                    onChange={(e) => setNewTwapNotional(Number(e.target.value))}
                    style={{
                      width: "100%",
                      background: "var(--bg-surface-elevated)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "4px",
                      color: "var(--text-primary)",
                      padding: "5px 8px",
                      fontSize: "11px",
                      fontFamily: "monospace",
                    }}
                  />
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                  <div>
                    <label style={{ fontSize: "10.5px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                      Execution Horizon
                    </label>
                    <select
                      value={newTwapDuration}
                      onChange={(e) => setNewTwapDuration(Number(e.target.value))}
                      style={{
                        width: "100%",
                        background: "var(--bg-surface-elevated)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "4px",
                        color: "var(--text-primary)",
                        padding: "5px 8px",
                        fontSize: "11px",
                      }}
                    >
                      <option value={5}>5 Minutes</option>
                      <option value={15}>15 Minutes</option>
                      <option value={30}>30 Minutes</option>
                      <option value={60}>1 Hour</option>
                      <option value={240}>4 Hours</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ fontSize: "10.5px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                      Slice Count
                    </label>
                    <input
                      type="number"
                      min="3"
                      max="40"
                      value={newTwapSlices}
                      onChange={(e) => setNewTwapSlices(Number(e.target.value))}
                      style={{
                        width: "100%",
                        background: "var(--bg-surface-elevated)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "4px",
                        color: "var(--text-primary)",
                        padding: "5px 8px",
                        fontSize: "11px",
                      }}
                    />
                  </div>
                </div>

                <div>
                  <label style={{ fontSize: "10.5px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                    Algorithm Model
                  </label>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px" }}>
                    <button
                      type="button"
                      onClick={() => setNewTwapAlgo("TWAP")}
                      style={{
                        background: newTwapAlgo === "TWAP" ? "var(--bg-surface-elevated)" : "transparent",
                        border: newTwapAlgo === "TWAP" ? "1px solid var(--border-medium)" : "1px solid var(--border-subtle)",
                        color: newTwapAlgo === "TWAP" ? "var(--text-primary)" : "var(--text-muted)",
                        borderRadius: "4px",
                        padding: "5px 0",
                        fontSize: "10.5px",
                        fontWeight: 600,
                        cursor: "pointer",
                      }}
                    >
                      TWAP (Linear)
                    </button>
                    <button
                      type="button"
                      onClick={() => setNewTwapAlgo("VWAP")}
                      style={{
                        background: newTwapAlgo === "VWAP" ? "var(--bg-surface-elevated)" : "transparent",
                        border: newTwapAlgo === "VWAP" ? "1px solid var(--border-medium)" : "1px solid var(--border-subtle)",
                        color: newTwapAlgo === "VWAP" ? "var(--text-primary)" : "var(--text-muted)",
                        borderRadius: "4px",
                        padding: "5px 0",
                        fontSize: "10.5px",
                        fontWeight: 600,
                        cursor: "pointer",
                      }}
                    >
                      VWAP (Volume Curve)
                    </button>
                  </div>
                </div>

                <div
                  style={{
                    background: "var(--bg-surface-elevated)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "4px",
                    padding: "8px 10px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <div>
                    <div style={{ fontSize: "10.5px", fontWeight: 600, color: "var(--text-primary)" }}>
                      Jitter / Anti-Frontrun
                    </div>
                    <div style={{ fontSize: "9.5px", color: "var(--text-muted)" }}>
                      Randomize slice size ±8% & interval
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={newTwapJitter}
                    onChange={(e) => setNewTwapJitter(e.target.checked)}
                    style={{ accentColor: "var(--accent-green)", cursor: "pointer" }}
                  />
                </div>

                <div style={{ marginTop: "auto", paddingTop: "8px" }}>
                  <button
                    type="submit"
                    style={{
                      width: "100%",
                      background: "var(--accent-green)",
                      border: "none",
                      color: "#05070a",
                      borderRadius: "4px",
                      padding: "8px 0",
                      fontSize: "11.5px",
                      fontWeight: 700,
                      cursor: "pointer",
                      letterSpacing: "0.02em",
                    }}
                  >
                    DEPLOY {newTwapAlgo} SLICER
                  </button>
                </div>
              </form>
            </div>

            {/* Column 2: Active Slicers List & Telemetry */}
            <div className="panel" style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}>
              <div className="panel-header">
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <ActivityIcon size={12} color="var(--text-secondary)" />
                  <span style={{ fontWeight: 600, fontSize: "11px", color: "var(--text-primary)" }}>
                    Active Algorithmic Execution Mandates ({twapOrders.length})
                  </span>
                </div>
                <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>Real-time Fill Feed</span>
              </div>

              <div style={{ flex: 1, overflowY: "auto", padding: "8px", display: "flex", flexDirection: "column", gap: "8px" }}>
                {twapOrders.map((order) => {
                  const progressPct = Math.round((order.filledSlices / order.totalSlices) * 100);
                  const isSelected = order.id === selectedTwapId;
                  const slippageBps = order.arrivalPrice
                    ? ((order.avgPrice - order.arrivalPrice) / order.arrivalPrice) * 10000
                    : 0;

                  return (
                    <div
                      key={order.id}
                      onClick={() => setSelectedTwapId(order.id)}
                      style={{
                        background: isSelected ? "var(--bg-surface-elevated)" : "var(--bg-surface-card)",
                        border: isSelected ? "1px solid var(--border-medium)" : "1px solid var(--border-subtle)",
                        borderRadius: "5px",
                        padding: "10px 12px",
                        cursor: "pointer",
                        display: "flex",
                        flexDirection: "column",
                        gap: "8px",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <span
                            style={{
                              background: order.side === "BUY" ? "var(--accent-green-subtle)" : "var(--accent-red-subtle)",
                              color: order.side === "BUY" ? "var(--accent-green)" : "var(--accent-red)",
                              border: `1px solid ${order.side === "BUY" ? "var(--accent-green-border)" : "var(--accent-red-border)"}`,
                              fontSize: "9.5px",
                              fontWeight: 700,
                              borderRadius: "3px",
                              padding: "1px 5px",
                            }}
                          >
                            {order.side}
                          </span>
                          <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-primary)" }}>
                            {order.symbol}
                          </span>
                          <span style={{ fontSize: "10.5px", color: "var(--text-muted)" }}>
                            ${order.totalNotional.toLocaleString()}
                          </span>
                        </div>

                        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                          <span
                            style={{
                              fontSize: "9.5px",
                              fontWeight: 600,
                              color: order.status === "RUNNING" ? "var(--accent-green)" : order.status === "COMPLETED" ? "var(--text-muted)" : "var(--accent-amber)",
                              display: "flex",
                              alignItems: "center",
                              gap: "4px",
                            }}
                          >
                            <span className={order.status === "RUNNING" ? "live-dot-green" : order.status === "COMPLETED" ? "" : "live-dot-amber"} />
                            {order.status}
                          </span>

                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleToggleTwapStatus(order.id);
                            }}
                            title={order.status === "RUNNING" ? "Pause Algo" : "Resume Algo"}
                            style={{
                              background: "transparent",
                              border: "1px solid var(--border-subtle)",
                              borderRadius: "3px",
                              padding: "2px 5px",
                              cursor: "pointer",
                              display: "inline-flex",
                              alignItems: "center",
                            }}
                          >
                            {order.status === "RUNNING" ? <PauseIcon size={10} color="var(--text-secondary)" /> : <PlayIcon size={10} color="var(--accent-green)" />}
                          </button>

                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteTwap(order.id);
                            }}
                            title="Cancel Algo"
                            style={{
                              background: "transparent",
                              border: "1px solid var(--border-subtle)",
                              borderRadius: "3px",
                              padding: "2px 5px",
                              cursor: "pointer",
                              display: "inline-flex",
                              alignItems: "center",
                            }}
                          >
                            <TrashIcon size={10} color="var(--accent-red)" />
                          </button>
                        </div>
                      </div>

                      {/* Progress Bar */}
                      <div>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "10px", color: "var(--text-muted)", marginBottom: "3px" }}>
                          <span>Slices: {order.filledSlices} / {order.totalSlices}</span>
                          <span className="tabular-nums">{progressPct}% filled</span>
                        </div>
                        <div style={{ height: "4px", background: "var(--border-subtle)", borderRadius: "2px", overflow: "hidden" }}>
                          <div
                            style={{
                              height: "100%",
                              width: `${progressPct}%`,
                              background: order.side === "BUY" ? "var(--accent-green)" : "var(--accent-red)",
                              transition: "width 0.3s ease",
                            }}
                          />
                        </div>
                      </div>

                      {/* Quant Metrics Grid */}
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "6px", fontSize: "10px", paddingTop: "2px" }}>
                        <div>
                          <div style={{ color: "var(--text-muted)" }}>Filled / Target</div>
                          <div className="tabular-nums" style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                            {order.filledQuantity} / {order.totalQuantity}
                          </div>
                        </div>
                        <div>
                          <div style={{ color: "var(--text-muted)" }}>Avg Price</div>
                          <div className="tabular-nums" style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                            ${order.avgPrice.toLocaleString()}
                          </div>
                        </div>
                        <div>
                          <div style={{ color: "var(--text-muted)" }}>Slippage vs Arr.</div>
                          <div className="tabular-nums" style={{ fontWeight: 600, color: slippageBps <= 0 ? "var(--accent-green)" : "var(--accent-red)" }}>
                            {slippageBps >= 0 ? "+" : ""}{slippageBps.toFixed(1)} bps
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Column 3: Live Slice Execution Tape for Selected Order */}
            <div className="panel" style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}>
              <div className="panel-header">
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <TrendingUpIcon size={12} color="var(--text-secondary)" />
                  <span style={{ fontWeight: 600, fontSize: "11px", color: "var(--text-primary)" }}>
                    Slice Execution Tape: {selectedTwap?.symbol}
                  </span>
                </div>
                <span className="kbd-badge">{selectedTwap?.sliceHistory.length} FILLS</span>
              </div>

              <div style={{ padding: "8px 12px", borderBottom: "1px solid var(--border-subtle)", background: "var(--bg-surface-card)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "10.5px" }}>
                  <span style={{ color: "var(--text-muted)" }}>Arrival Benchmark:</span>
                  <span className="tabular-nums" style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                    ${selectedTwap?.arrivalPrice.toLocaleString()}
                  </span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "10.5px", marginTop: "2px" }}>
                  <span style={{ color: "var(--text-muted)" }}>Filled Notional:</span>
                  <span className="tabular-nums" style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                    ${selectedTwap?.filledNotional.toLocaleString()}
                  </span>
                </div>
              </div>

              <div style={{ flex: 1, overflowY: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "10.5px" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border-subtle)", color: "var(--text-muted)", textAlign: "left" }}>
                      <th style={{ padding: "6px 10px", fontWeight: 600 }}>#</th>
                      <th style={{ padding: "6px 10px", fontWeight: 600 }}>TIME</th>
                      <th style={{ padding: "6px 10px", fontWeight: 600, textAlign: "right" }}>QTY</th>
                      <th style={{ padding: "6px 10px", fontWeight: 600, textAlign: "right" }}>PRICE</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedTwap?.sliceHistory.length === 0 ? (
                      <tr>
                        <td colSpan={4} style={{ padding: "24px 10px", textAlign: "center", color: "var(--text-muted)" }}>
                          No slices executed yet. Awaiting next timer interval...
                        </td>
                      </tr>
                    ) : (
                      selectedTwap?.sliceHistory.map((slice) => (
                        <tr
                          key={slice.sliceNumber}
                          style={{
                            borderBottom: "1px solid var(--border-subtle)",
                            background: "transparent",
                          }}
                        >
                          <td style={{ padding: "6px 10px", color: "var(--text-muted)", fontWeight: 600 }}>
                            #{slice.sliceNumber}
                          </td>
                          <td className="tabular-nums" style={{ padding: "6px 10px", color: "var(--text-secondary)" }}>
                            {slice.timestamp}
                          </td>
                          <td className="tabular-nums" style={{ padding: "6px 10px", textAlign: "right", color: "var(--text-primary)" }}>
                            {slice.qty}
                          </td>
                          <td className="tabular-nums" style={{ padding: "6px 10px", textAlign: "right", color: selectedTwap.side === "BUY" ? "var(--accent-green)" : "var(--accent-red)", fontWeight: 600 }}>
                            ${slice.price.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* SUBTAB 2: GRID TRADING BOT */}
        {activeSubTab === "grid" && (
          <div style={{ height: "100%", display: "grid", gridTemplateColumns: isMobile ? "1fr" : "310px 1fr", gap: "8px", overflowY: isMobile ? "auto" : "hidden", overflowX: "hidden" }}>
            {/* Deploy Grid Form */}
            <div className="panel" style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}>
              <div className="panel-header">
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <ActivityIcon size={12} color="var(--text-secondary)" />
                  <span style={{ fontWeight: 600, fontSize: "11px", color: "var(--text-primary)" }}>
                    Deploy Neutral / Long Grid
                  </span>
                </div>
                <span className="kbd-badge">ARITHMETIC</span>
              </div>

              <form onSubmit={handleDeployGrid} style={{ padding: "12px", display: "flex", flexDirection: "column", gap: "10px", overflowY: "auto", flex: 1 }}>
                <div>
                  <label style={{ fontSize: "10.5px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                    Market Pair
                  </label>
                  <select
                    value={newGridSymbol}
                    onChange={(e) => setNewGridSymbol(e.target.value)}
                    style={{
                      width: "100%",
                      background: "var(--bg-surface-elevated)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "4px",
                      color: "var(--text-primary)",
                      padding: "5px 8px",
                      fontSize: "11px",
                    }}
                  >
                    <option value="SOL/USDT">SOL/USDT (Volatile Range)</option>
                    <option value="BTC/USDT">BTC/USDT (High Liquidity)</option>
                    <option value="ETH/USDT">ETH/USDT (Consolidation)</option>
                  </select>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                  <div>
                    <label style={{ fontSize: "10.5px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                      Lower Bound ($)
                    </label>
                    <input
                      type="number"
                      value={newGridLower}
                      onChange={(e) => setNewGridLower(Number(e.target.value))}
                      style={{
                        width: "100%",
                        background: "var(--bg-surface-elevated)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "4px",
                        color: "var(--text-primary)",
                        padding: "5px 8px",
                        fontSize: "11px",
                      }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: "10.5px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                      Upper Bound ($)
                    </label>
                    <input
                      type="number"
                      value={newGridUpper}
                      onChange={(e) => setNewGridUpper(Number(e.target.value))}
                      style={{
                        width: "100%",
                        background: "var(--bg-surface-elevated)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "4px",
                        color: "var(--text-primary)",
                        padding: "5px 8px",
                        fontSize: "11px",
                      }}
                    />
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                  <div>
                    <label style={{ fontSize: "10.5px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                      Grid Levels (6-20)
                    </label>
                    <input
                      type="number"
                      min="4"
                      max="20"
                      value={newGridLevels}
                      onChange={(e) => setNewGridLevels(Number(e.target.value))}
                      style={{
                        width: "100%",
                        background: "var(--bg-surface-elevated)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "4px",
                        color: "var(--text-primary)",
                        padding: "5px 8px",
                        fontSize: "11px",
                      }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: "10.5px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                      Total Capital ($)
                    </label>
                    <input
                      type="number"
                      step="500"
                      value={newGridCapital}
                      onChange={(e) => setNewGridCapital(Number(e.target.value))}
                      style={{
                        width: "100%",
                        background: "var(--bg-surface-elevated)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "4px",
                        color: "var(--text-primary)",
                        padding: "5px 8px",
                        fontSize: "11px",
                      }}
                    />
                  </div>
                </div>

                <div
                  style={{
                    background: "var(--bg-surface-elevated)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "4px",
                    padding: "8px 10px",
                    fontSize: "10.5px",
                    color: "var(--text-secondary)",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span>Estimated Profit per Grid:</span>
                    <strong style={{ color: "var(--accent-green)" }}>
                      {(((newGridUpper - newGridLower) / (newGridLevels - 1) / newGridLower) * 100).toFixed(2)}%
                    </strong>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginTop: "3px" }}>
                    <span>Capital per Level:</span>
                    <strong style={{ color: "var(--text-primary)" }}>
                      ${(newGridCapital / newGridLevels).toFixed(2)}
                    </strong>
                  </div>
                </div>

                <div style={{ marginTop: "auto", paddingTop: "8px" }}>
                  <button
                    type="submit"
                    style={{
                      width: "100%",
                      background: "var(--accent-green)",
                      border: "none",
                      color: "#05070a",
                      borderRadius: "4px",
                      padding: "8px 0",
                      fontSize: "11.5px",
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    DEPLOY GRID STRATEGY
                  </button>
                </div>
              </form>
            </div>

            {/* Grid Bots Active Cards & Ladder */}
            <div className="panel" style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}>
              <div className="panel-header">
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <SlidersIcon size={12} color="var(--text-secondary)" />
                  <span style={{ fontWeight: 600, fontSize: "11px", color: "var(--text-primary)" }}>
                    Active Grid Automations & Ladder
                  </span>
                </div>
                <span className="kbd-badge">LIVE ORDERS</span>
              </div>

              <div style={{ flex: 1, overflowY: "auto", padding: "12px", display: "flex", flexDirection: "column", gap: "12px" }}>
                {gridBots.map((bot) => (
                  <div
                    key={bot.id}
                    style={{
                      background: "var(--bg-surface-card)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "6px",
                      padding: "12px",
                      display: "flex",
                      flexDirection: "column",
                      gap: "10px",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)" }}>
                          {bot.symbol}
                        </span>
                        <span className="kbd-badge">{bot.gridLevels} LEVELS</span>
                        <span style={{ fontSize: "10.5px", color: "var(--text-muted)" }}>
                          Range: ${bot.lowerPrice} - ${bot.upperPrice}
                        </span>
                      </div>

                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <button
                          onClick={() => handleToggleGridStatus(bot.id)}
                          style={{
                            background: "var(--bg-surface-elevated)",
                            border: "1px solid var(--border-subtle)",
                            borderRadius: "3px",
                            padding: "3px 7px",
                            fontSize: "10px",
                            color: bot.status === "RUNNING" ? "var(--accent-green)" : "var(--accent-amber)",
                            cursor: "pointer",
                          }}
                        >
                          {bot.status === "RUNNING" ? "PAUSE" : "RESUME"}
                        </button>
                        <button
                          onClick={() => handleDeleteGrid(bot.id)}
                          style={{
                            background: "transparent",
                            border: "1px solid var(--border-subtle)",
                            borderRadius: "3px",
                            padding: "3px 6px",
                            cursor: "pointer",
                          }}
                        >
                          <TrashIcon size={11} color="var(--accent-red)" />
                        </button>
                      </div>
                    </div>

                    {/* Stats Ribbon */}
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: "8px", background: "var(--bg-surface-elevated)", padding: "8px 10px", borderRadius: "4px" }}>
                      <div>
                        <div style={{ fontSize: "9.5px", color: "var(--text-muted)" }}>Allocated Capital</div>
                        <div className="tabular-nums" style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-primary)" }}>
                          ${bot.investmentUsd.toLocaleString()}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: "9.5px", color: "var(--text-muted)" }}>Realized Profit</div>
                        <div className="tabular-nums" style={{ fontSize: "11px", fontWeight: 700, color: "var(--accent-green)" }}>
                          +${bot.realizedProfitUsd.toFixed(2)}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: "9.5px", color: "var(--text-muted)" }}>Unrealized PnL</div>
                        <div className="tabular-nums" style={{ fontSize: "11px", fontWeight: 700, color: bot.unrealizedPnlUsd >= 0 ? "var(--accent-green)" : "var(--accent-red)" }}>
                          {bot.unrealizedPnlUsd >= 0 ? "+" : ""}${bot.unrealizedPnlUsd.toFixed(2)}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: "9.5px", color: "var(--text-muted)" }}>Spread / Grid</div>
                        <div className="tabular-nums" style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-primary)" }}>
                          {bot.gridSpreadPct}%
                        </div>
                      </div>
                    </div>

                    {/* Visual Grid Levels Ladder */}
                    <div>
                      <div style={{ fontSize: "10px", color: "var(--text-muted)", marginBottom: "4px" }}>
                        Ladder Order Depth
                      </div>
                      <div style={{ display: "grid", gridTemplateColumns: `repeat(${bot.orders.length}, 1fr)`, gap: "4px" }}>
                        {bot.orders.map((o) => (
                          <div
                            key={o.id}
                            style={{
                              background: o.side === "BUY" ? "var(--accent-green-subtle)" : "var(--accent-red-subtle)",
                              border: `1px solid ${o.side === "BUY" ? "var(--accent-green-border)" : "var(--accent-red-border)"}`,
                              borderRadius: "3px",
                              padding: "4px 2px",
                              textAlign: "center",
                            }}
                          >
                            <div style={{ fontSize: "8.5px", color: "var(--text-muted)" }}>L{o.levelIndex}</div>
                            <div style={{ fontSize: "9px", fontWeight: 700, color: o.side === "BUY" ? "var(--accent-green)" : "var(--accent-red)" }}>
                              ${o.price}
                            </div>
                            <div style={{ fontSize: "8px", color: o.status === "FILLED" ? "var(--text-primary)" : "var(--text-muted)", fontWeight: o.status === "FILLED" ? 700 : 400 }}>
                              {o.status}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* SUBTAB 3: SMART DCA BOT */}
        {activeSubTab === "dca" && (
          <div style={{ height: "100%", display: "grid", gridTemplateColumns: isMobile ? "1fr" : "310px 1fr", gap: "8px", overflowY: isMobile ? "auto" : "hidden", overflowX: "hidden" }}>
            {/* Deploy DCA Form */}
            <div className="panel" style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}>
              <div className="panel-header">
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <ZapIcon size={12} color="var(--text-secondary)" />
                  <span style={{ fontWeight: 600, fontSize: "11px", color: "var(--text-primary)" }}>
                    Deploy Smart DCA Accumulator
                  </span>
                </div>
                <span className="kbd-badge">MARTINGALE / STEP</span>
              </div>

              <form onSubmit={handleDeployDca} style={{ padding: "12px", display: "flex", flexDirection: "column", gap: "10px", overflowY: "auto", flex: 1 }}>
                <div>
                  <label style={{ fontSize: "10.5px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                    Accumulation Asset
                  </label>
                  <select
                    value={newDcaSymbol}
                    onChange={(e) => setNewDcaSymbol(e.target.value)}
                    style={{
                      width: "100%",
                      background: "var(--bg-surface-elevated)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "4px",
                      color: "var(--text-primary)",
                      padding: "5px 8px",
                      fontSize: "11px",
                    }}
                  >
                    <option value="ETH/USDT">ETH/USDT</option>
                    <option value="BTC/USDT">BTC/USDT</option>
                    <option value="SOL/USDT">SOL/USDT</option>
                  </select>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                  <div>
                    <label style={{ fontSize: "10.5px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                      Base Order ($)
                    </label>
                    <input
                      type="number"
                      value={newDcaBaseOrder}
                      onChange={(e) => setNewDcaBaseOrder(Number(e.target.value))}
                      style={{
                        width: "100%",
                        background: "var(--bg-surface-elevated)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "4px",
                        color: "var(--text-primary)",
                        padding: "5px 8px",
                        fontSize: "11px",
                      }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: "10.5px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                      Safety Order ($)
                    </label>
                    <input
                      type="number"
                      value={newDcaSafetyOrder}
                      onChange={(e) => setNewDcaSafetyOrder(Number(e.target.value))}
                      style={{
                        width: "100%",
                        background: "var(--bg-surface-elevated)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "4px",
                        color: "var(--text-primary)",
                        padding: "5px 8px",
                        fontSize: "11px",
                      }}
                    />
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                  <div>
                    <label style={{ fontSize: "10.5px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                      Price Deviation %
                    </label>
                    <input
                      type="number"
                      step="0.5"
                      value={newDcaDeviation}
                      onChange={(e) => setNewDcaDeviation(Number(e.target.value))}
                      style={{
                        width: "100%",
                        background: "var(--bg-surface-elevated)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "4px",
                        color: "var(--text-primary)",
                        padding: "5px 8px",
                        fontSize: "11px",
                      }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: "10.5px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                      Take Profit Target %
                    </label>
                    <input
                      type="number"
                      step="0.5"
                      value={newDcaTp}
                      onChange={(e) => setNewDcaTp(Number(e.target.value))}
                      style={{
                        width: "100%",
                        background: "var(--bg-surface-elevated)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "4px",
                        color: "var(--text-primary)",
                        padding: "5px 8px",
                        fontSize: "11px",
                      }}
                    />
                  </div>
                </div>

                <div style={{ marginTop: "auto", paddingTop: "8px" }}>
                  <button
                    type="submit"
                    style={{
                      width: "100%",
                      background: "var(--accent-green)",
                      border: "none",
                      color: "#05070a",
                      borderRadius: "4px",
                      padding: "8px 0",
                      fontSize: "11.5px",
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    DEPLOY SMART DCA BOT
                  </button>
                </div>
              </form>
            </div>

            {/* Active DCA Cards */}
            <div className="panel" style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}>
              <div className="panel-header">
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <TargetIcon size={12} color="var(--text-secondary)" />
                  <span style={{ fontWeight: 600, fontSize: "11px", color: "var(--text-primary)" }}>
                    Active DCA Accumulators
                  </span>
                </div>
                <span className="kbd-badge">{dcaBots.length} ACTIVE</span>
              </div>

              <div style={{ flex: 1, overflowY: "auto", padding: "12px", display: "flex", flexDirection: "column", gap: "10px" }}>
                {dcaBots.map((bot) => (
                  <div
                    key={bot.id}
                    style={{
                      background: "var(--bg-surface-card)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "6px",
                      padding: "12px",
                      display: "flex",
                      flexDirection: "column",
                      gap: "8px",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)" }}>
                          {bot.symbol}
                        </span>
                        <span className="kbd-badge">STEP: -{bot.deviationPct}%</span>
                        <span style={{ fontSize: "10.5px", color: "var(--accent-green)", fontWeight: 600 }}>
                          TP: +{bot.tpPct}%
                        </span>
                      </div>

                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <button
                          onClick={() => handleToggleDcaStatus(bot.id)}
                          style={{
                            background: "var(--bg-surface-elevated)",
                            border: "1px solid var(--border-subtle)",
                            borderRadius: "3px",
                            padding: "3px 7px",
                            fontSize: "10px",
                            color: bot.status === "RUNNING" ? "var(--accent-green)" : "var(--accent-amber)",
                            cursor: "pointer",
                          }}
                        >
                          {bot.status === "RUNNING" ? "PAUSE" : "RESUME"}
                        </button>
                        <button
                          onClick={() => handleDeleteDca(bot.id)}
                          style={{
                            background: "transparent",
                            border: "1px solid var(--border-subtle)",
                            borderRadius: "3px",
                            padding: "3px 6px",
                            cursor: "pointer",
                          }}
                        >
                          <TrashIcon size={11} color="var(--accent-red)" />
                        </button>
                      </div>
                    </div>

                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px", background: "var(--bg-surface-elevated)", padding: "8px 10px", borderRadius: "4px" }}>
                      <div>
                        <div style={{ fontSize: "9.5px", color: "var(--text-muted)" }}>Total Invested</div>
                        <div className="tabular-nums" style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-primary)" }}>
                          ${bot.totalInvested.toLocaleString()}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: "9.5px", color: "var(--text-muted)" }}>Avg Entry Price</div>
                        <div className="tabular-nums" style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-primary)" }}>
                          ${bot.avgEntryPrice.toLocaleString()}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: "9.5px", color: "var(--text-muted)" }}>Safety Fills</div>
                        <div className="tabular-nums" style={{ fontSize: "11px", fontWeight: 700, color: "var(--accent-green)" }}>
                          {bot.filledOrders} / {bot.maxSafetyOrders} orders
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* SUBTAB 4: SMART EXIT MANDATES (SPEC 06) */}
        {activeSubTab === "mandates" && (
          <div style={{ height: "100%", display: "grid", gridTemplateColumns: isMobile ? "1fr" : "1fr 340px", gap: "8px", overflowY: isMobile ? "auto" : "hidden", overflowX: "hidden" }}>
            <div className="panel" style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}>
              <div className="panel-header">
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <ShieldIcon size={12} color="var(--accent-green)" />
                  <span style={{ fontWeight: 600, fontSize: "11px", color: "var(--text-primary)" }}>
                    Spec 06: Multi-Tier TP/SL Scaling & Risk Guard Mandates
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <span className="live-dot-green" />
                  <span style={{ fontSize: "10px", color: "var(--accent-green)", fontWeight: 600 }}>ARMED & ACTIVE</span>
                </div>
              </div>

              <div style={{ flex: 1, overflowY: "auto", padding: "16px", display: "flex", flexDirection: "column", gap: "16px" }}>
                {mandateSavedToast && (
                  <div
                    style={{
                      background: "var(--accent-green-subtle)",
                      border: "1px solid var(--accent-green-border)",
                      color: "var(--accent-green)",
                      borderRadius: "4px",
                      padding: "8px 12px",
                      fontSize: "11px",
                      fontWeight: 600,
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                    }}
                  >
                    <CheckIcon size={12} color="var(--accent-green)" />
                    <span>Mandates successfully synchronized to Institutional Risk Gate.</span>
                  </div>
                )}

                {/* Tier 1 Rule */}
                <div
                  style={{
                    background: "var(--bg-surface-card)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "6px",
                    padding: "12px 14px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "8px",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <div>
                      <div style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-primary)" }}>
                        Tier 1 (TP1): Initial Profit Lock & Auto-Breakeven Move
                      </div>
                      <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>
                        When price achieves TP1, automatically de-risk position and move hard Stop Loss to Entry + Spread.
                      </div>
                    </div>
                    <span className="kbd-badge">STEP 1</span>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "10px", marginTop: "4px" }}>
                    <div>
                      <label style={{ fontSize: "10px", color: "var(--text-muted)", display: "block", marginBottom: "3px" }}>
                        TP1 Target (%)
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        value={mandate.tp1Pct}
                        onChange={(e) => setMandate({ ...mandate, tp1Pct: Number(e.target.value) })}
                        style={{
                          width: "100%",
                          background: "var(--bg-surface-elevated)",
                          border: "1px solid var(--border-subtle)",
                          borderRadius: "4px",
                          color: "var(--text-primary)",
                          padding: "5px 8px",
                          fontSize: "11px",
                        }}
                      />
                    </div>
                    <div>
                      <label style={{ fontSize: "10px", color: "var(--text-muted)", display: "block", marginBottom: "3px" }}>
                        Close Size (%)
                      </label>
                      <input
                        type="number"
                        value={mandate.tp1SizePct}
                        onChange={(e) => setMandate({ ...mandate, tp1SizePct: Number(e.target.value) })}
                        style={{
                          width: "100%",
                          background: "var(--bg-surface-elevated)",
                          border: "1px solid var(--border-subtle)",
                          borderRadius: "4px",
                          color: "var(--text-primary)",
                          padding: "5px 8px",
                          fontSize: "11px",
                        }}
                      />
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", justifyContent: "center" }}>
                      <label style={{ fontSize: "10px", color: "var(--text-muted)", display: "block", marginBottom: "3px" }}>
                        Move SL to Breakeven
                      </label>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <input
                          type="checkbox"
                          checked={mandate.autoBreakeven}
                          onChange={(e) => setMandate({ ...mandate, autoBreakeven: e.target.checked })}
                          style={{ accentColor: "var(--accent-green)", cursor: "pointer" }}
                        />
                        <span style={{ fontSize: "11px", color: "var(--text-secondary)", fontWeight: 500 }}>
                          Enabled
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Tier 2 Rule */}
                <div
                  style={{
                    background: "var(--bg-surface-card)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "6px",
                    padding: "12px 14px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "8px",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <div>
                      <div style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-primary)" }}>
                        Tier 2 (TP2): Secondary Expansion & Trail Lock
                      </div>
                      <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>
                        Close secondary tranche and lock trail at TP1 level to guarantee profit baseline.
                      </div>
                    </div>
                    <span className="kbd-badge">STEP 2</span>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginTop: "4px" }}>
                    <div>
                      <label style={{ fontSize: "10px", color: "var(--text-muted)", display: "block", marginBottom: "3px" }}>
                        TP2 Target (%)
                      </label>
                      <input
                        type="number"
                        step="0.5"
                        value={mandate.tp2Pct}
                        onChange={(e) => setMandate({ ...mandate, tp2Pct: Number(e.target.value) })}
                        style={{
                          width: "100%",
                          background: "var(--bg-surface-elevated)",
                          border: "1px solid var(--border-subtle)",
                          borderRadius: "4px",
                          color: "var(--text-primary)",
                          padding: "5px 8px",
                          fontSize: "11px",
                        }}
                      />
                    </div>
                    <div>
                      <label style={{ fontSize: "10px", color: "var(--text-muted)", display: "block", marginBottom: "3px" }}>
                        Close Size (%)
                      </label>
                      <input
                        type="number"
                        value={mandate.tp2SizePct}
                        onChange={(e) => setMandate({ ...mandate, tp2SizePct: Number(e.target.value) })}
                        style={{
                          width: "100%",
                          background: "var(--bg-surface-elevated)",
                          border: "1px solid var(--border-subtle)",
                          borderRadius: "4px",
                          color: "var(--text-primary)",
                          padding: "5px 8px",
                          fontSize: "11px",
                        }}
                      />
                    </div>
                  </div>
                </div>

                {/* Tier 3 Rule: ATR Dynamic Runner */}
                <div
                  style={{
                    background: "var(--bg-surface-card)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "6px",
                    padding: "12px 14px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "8px",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <div>
                      <div style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-primary)" }}>
                        Tier 3 (TP3): Remaining 25% Runner with ATR Trailing Stop
                      </div>
                      <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>
                        Remaining size is kept open to ride high-momentum trend extensions, trailing at dynamic ATR volatility bands.
                      </div>
                    </div>
                    <span className="kbd-badge">STEP 3</span>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginTop: "4px" }}>
                    <div>
                      <label style={{ fontSize: "10px", color: "var(--text-muted)", display: "block", marginBottom: "3px" }}>
                        ATR Trailing Multiplier
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        value={mandate.tp3AtrMultiplier}
                        onChange={(e) => setMandate({ ...mandate, tp3AtrMultiplier: Number(e.target.value) })}
                        style={{
                          width: "100%",
                          background: "var(--bg-surface-elevated)",
                          border: "1px solid var(--border-subtle)",
                          borderRadius: "4px",
                          color: "var(--text-primary)",
                          padding: "5px 8px",
                          fontSize: "11px",
                        }}
                      />
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", justifyContent: "center" }}>
                      <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>Runner Size Allocation</span>
                      <strong style={{ fontSize: "11px", color: "var(--accent-green)", marginTop: "3px" }}>
                        {100 - mandate.tp1SizePct - mandate.tp2SizePct}% of Position
                      </strong>
                    </div>
                  </div>
                </div>

                {/* Circuit Breaker & High-Impact Event Blackout */}
                <div
                  style={{
                    background: "var(--bg-surface-card)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "6px",
                    padding: "12px 14px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "10px",
                  }}
                >
                  <div style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-primary)" }}>
                    Automated Circuit Breaker & Safety Invariants
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                    <div>
                      <label style={{ fontSize: "10px", color: "var(--text-muted)", display: "block", marginBottom: "3px" }}>
                        Max Daily Drawdown Halt ($)
                      </label>
                      <input
                        type="number"
                        step="500"
                        value={mandate.maxDailyLossUsd}
                        onChange={(e) => setMandate({ ...mandate, maxDailyLossUsd: Number(e.target.value) })}
                        style={{
                          width: "100%",
                          background: "var(--bg-surface-elevated)",
                          border: "1px solid var(--border-subtle)",
                          borderRadius: "4px",
                          color: "var(--text-primary)",
                          padding: "5px 8px",
                          fontSize: "11px",
                        }}
                      />
                    </div>

                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", background: "var(--bg-surface-elevated)", padding: "6px 10px", borderRadius: "4px" }}>
                      <div>
                        <div style={{ fontSize: "10.5px", fontWeight: 600, color: "var(--text-primary)" }}>
                          News Blackout Shield
                        </div>
                        <div style={{ fontSize: "9.5px", color: "var(--text-muted)" }}>
                          Halt algos ±15m FOMC/CPI
                        </div>
                      </div>
                      <input
                        type="checkbox"
                        checked={mandate.newsBlackoutEnabled}
                        onChange={(e) => setMandate({ ...mandate, newsBlackoutEnabled: e.target.checked })}
                        style={{ accentColor: "var(--accent-green)", cursor: "pointer" }}
                      />
                    </div>
                  </div>
                </div>

                <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "4px" }}>
                  <button
                    onClick={handleSaveMandates}
                    style={{
                      background: "var(--accent-green)",
                      border: "none",
                      color: "#05070a",
                      borderRadius: "4px",
                      padding: "8px 18px",
                      fontSize: "11.5px",
                      fontWeight: 700,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                    }}
                  >
                    <CheckIcon size={12} color="#05070a" />
                    <span>SAVE & ARM MANDATES</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Right Guide & Spec 06 Invariants */}
            <div className="panel" style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}>
              <div className="panel-header">
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <ShieldIcon size={12} color="var(--text-secondary)" />
                  <span style={{ fontWeight: 600, fontSize: "11px", color: "var(--text-primary)" }}>
                    Rule Specification & Invariants
                  </span>
                </div>
              </div>

              <div style={{ padding: "14px", fontSize: "11px", color: "var(--text-secondary)", lineHeight: "18px", overflowY: "auto" }}>
                <div style={{ fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                  Deterministic Execution Flow:
                </div>
                <ol style={{ paddingLeft: "18px", margin: "0 0 14px 0", color: "var(--text-muted)", display: "flex", flexDirection: "column", gap: "6px" }}>
                  <li>
                    <strong>Order Entry:</strong> Limit or TWAP sliced filled across liquidity pools.
                  </li>
                  <li>
                    <strong>TP1 Trigger (+{mandate.tp1Pct}%):</strong> Market slicer liquidates {mandate.tp1SizePct}% of open notional. Instantly replaces original Stop-Loss order with a Breakeven Stop at (entry_price + fees).
                  </li>
                  <li>
                    <strong>TP2 Trigger (+{mandate.tp2Pct}%):</strong> Slices out {mandate.tp2SizePct}% more capital. Moves SL up to TP1 level.
                  </li>
                  <li>
                    <strong>TP3 Trend Runner:</strong> Remaining {100 - mandate.tp1SizePct - mandate.tp2SizePct}% floats with dynamic ATR trailing stop ({mandate.tp3AtrMultiplier}x multiplier).
                  </li>
                  <li>
                    <strong>Loss Floor Guard:</strong> If aggregate daily realized + unrealized drawdown hits ${mandate.maxDailyLossUsd.toLocaleString()}, the Risk Gate fires synchronous emergency kill switch.
                  </li>
                </ol>

                <div
                  style={{
                    background: "var(--bg-surface-elevated)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "4px",
                    padding: "10px",
                    display: "flex",
                    gap: "8px",
                  }}
                >
                  <AlertTriangleIcon size={14} color="var(--accent-amber)" />
                  <div style={{ fontSize: "10px", color: "var(--text-muted)", lineHeight: "14px" }}>
                    All automation mandates run asynchronous background threads with 0 network latency websocket feeds from Binance & Bybit.
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
