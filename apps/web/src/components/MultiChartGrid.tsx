"use client";

import React, { useState, useEffect } from "react";
import { AssetDef } from "./MarketScanner";
import { TradingViewChart } from "./TradingViewChart";
import { soundManager } from "../lib/soundEffects";
import { Layout1x1Icon, Layout1x2Icon, Layout2x1Icon, Layout2x2Icon, MaximizeIcon, MinimizeIcon, ZapIcon } from "./Icons";

function useIsMobile() {
  const [mobile, setMobile] = useState(false);
  useEffect(() => {
    const check = () => setMobile(window.innerWidth < 768);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);
  return mobile;
}

export type GridLayoutMode = "1x1" | "1x2" | "2x1" | "2x2";

interface ChartSlot {
  id: string;
  symbol: string;
  name: string;
  tvSymbol: string;
  interval: string;
}

interface MultiChartGridProps {
  primaryAsset: AssetDef;
  onSelectPrimaryAsset?: (asset: AssetDef) => void;
  theme?: "dark" | "light";
}

const DEFAULT_INSTRUMENTS = [
  { symbol: "BTC/USDT", name: "Bitcoin", tvSymbol: "BINANCE:BTCUSDT" },
  { symbol: "ETH/USDT", name: "Ethereum", tvSymbol: "BINANCE:ETHUSDT" },
  { symbol: "SOL/USDT", name: "Solana", tvSymbol: "BINANCE:SOLUSDT" },
  { symbol: "BNB/USDT", name: "Binance Coin", tvSymbol: "BINANCE:BNBUSDT" },
  { symbol: "XRP/USDT", name: "Ripple", tvSymbol: "BINANCE:XRPUSDT" },
  { symbol: "EUR/USD", name: "Euro / USD", tvSymbol: "FX:EURUSD" },
  { symbol: "XAU/USD", name: "Gold / USD", tvSymbol: "OANDA:XAUUSD" },
  { symbol: "US100", name: "Nasdaq 100", tvSymbol: "NASDAQ:NDX" },
];

const TIMEFRAMES = [
  { label: "1m", value: "1" },
  { label: "5m", value: "5" },
  { label: "15m", value: "15" },
  { label: "1h", value: "60" },
  { label: "4h", value: "240" },
  { label: "1D", value: "D" },
];

export function MultiChartGrid({ primaryAsset, onSelectPrimaryAsset, theme = "light" }: MultiChartGridProps) {
  const isMobile = useIsMobile();
  const [layoutMode, setLayoutMode] = useState<GridLayoutMode>("1x1");
  const [focusedSlotId, setFocusedSlotId] = useState<string | null>(null);
  const [globalEngine, setGlobalEngine] = useState<"native" | "tradingview">("native");

  const [slots, setSlots] = useState<ChartSlot[]>([
    {
      id: "slot-1",
      symbol: primaryAsset.symbol,
      name: primaryAsset.name,
      tvSymbol: primaryAsset.tvSymbol,
      interval: "15",
    },
    {
      id: "slot-2",
      symbol: "ETH/USDT",
      name: "Ethereum",
      tvSymbol: "BINANCE:ETHUSDT",
      interval: "15",
    },
    {
      id: "slot-3",
      symbol: "SOL/USDT",
      name: "Solana",
      tvSymbol: "BINANCE:SOLUSDT",
      interval: "15",
    },
    {
      id: "slot-4",
      symbol: "BNB/USDT",
      name: "Binance Coin",
      tvSymbol: "BINANCE:BNBUSDT",
      interval: "15",
    },
  ]);

  // Keep Slot 1 synced with primaryAsset
  useEffect(() => {
    setSlots((prev) =>
      prev.map((s, idx) =>
        idx === 0
          ? {
              ...s,
              symbol: primaryAsset.symbol,
              name: primaryAsset.name,
              tvSymbol: primaryAsset.tvSymbol,
            }
          : s
      )
    );
  }, [primaryAsset]);

  const handleUpdateSlotSymbol = (slotId: string, sym: string) => {
    soundManager.playClick();
    const inst = DEFAULT_INSTRUMENTS.find((x) => x.symbol === sym);
    if (!inst) return;

    setSlots((prev) =>
      prev.map((s) =>
        s.id === slotId
          ? { ...s, symbol: inst.symbol, name: inst.name, tvSymbol: inst.tvSymbol }
          : s
      )
    );
  };

  const handleUpdateSlotInterval = (slotId: string, intervalVal: string) => {
    soundManager.playClick();
    setSlots((prev) =>
      prev.map((s) => (s.id === slotId ? { ...s, interval: intervalVal } : s))
    );
  };

  const handleSetLayout = (mode: GridLayoutMode) => {
    soundManager.playClick();
    setLayoutMode(mode);
    setFocusedSlotId(null);
  };

  const handleApplyPreset = (presetType: "crypto" | "mtf" | "macro") => {
    soundManager.playClick();
    if (presetType === "crypto") {
      setLayoutMode("2x2");
      setFocusedSlotId(null);
      setSlots([
        { id: "slot-1", symbol: "BTC/USDT", name: "Bitcoin", tvSymbol: "BINANCE:BTCUSDT", interval: "15" },
        { id: "slot-2", symbol: "ETH/USDT", name: "Ethereum", tvSymbol: "BINANCE:ETHUSDT", interval: "15" },
        { id: "slot-3", symbol: "SOL/USDT", name: "Solana", tvSymbol: "BINANCE:SOLUSDT", interval: "15" },
        { id: "slot-4", symbol: "BNB/USDT", name: "Binance Coin", tvSymbol: "BINANCE:BNBUSDT", interval: "15" },
      ]);
    } else if (presetType === "mtf") {
      setLayoutMode("2x2");
      setFocusedSlotId(null);
      const curr = slots[0] || { symbol: "BTC/USDT", name: "Bitcoin", tvSymbol: "BINANCE:BTCUSDT" };
      setSlots([
        { id: "slot-1", symbol: curr.symbol, name: curr.name, tvSymbol: curr.tvSymbol, interval: "5" },
        { id: "slot-2", symbol: curr.symbol, name: curr.name, tvSymbol: curr.tvSymbol, interval: "15" },
        { id: "slot-3", symbol: curr.symbol, name: curr.name, tvSymbol: curr.tvSymbol, interval: "60" },
        { id: "slot-4", symbol: curr.symbol, name: curr.name, tvSymbol: curr.tvSymbol, interval: "240" },
      ]);
    } else if (presetType === "macro") {
      setLayoutMode("2x2");
      setFocusedSlotId(null);
      setSlots([
        { id: "slot-1", symbol: "BTC/USDT", name: "Bitcoin", tvSymbol: "BINANCE:BTCUSDT", interval: "15" },
        { id: "slot-2", symbol: "ETH/USDT", name: "Ethereum", tvSymbol: "BINANCE:ETHUSDT", interval: "15" },
        { id: "slot-3", symbol: "EUR/USD", name: "Euro", tvSymbol: "FX:EURUSD", interval: "60" },
        { id: "slot-4", symbol: "XAU/USD", name: "Gold", tvSymbol: "OANDA:XAUUSD", interval: "60" },
      ]);
    }
  };

  const getVisibleSlots = () => {
    if (focusedSlotId) {
      return slots.filter((s) => s.id === focusedSlotId);
    }
    switch (layoutMode) {
      case "1x1":
        return slots.slice(0, 1);
      case "1x2":
      case "2x1":
        return slots.slice(0, 2);
      case "2x2":
        return slots.slice(0, 4);
    }
  };

  const visibleSlots = getVisibleSlots();

  const getGridStyle = (): React.CSSProperties => {
    if (focusedSlotId || layoutMode === "1x1") {
      return {
        display: "grid",
        gridTemplateColumns: "1fr",
        gridTemplateRows: "1fr",
        gap: "4px",
        height: "100%",
        width: "100%",
      };
    }
    switch (layoutMode) {
      case "1x2":
        return {
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gridTemplateRows: "1fr",
          gap: "6px",
          height: "100%",
          width: "100%",
        };
      case "2x1":
        return {
          display: "grid",
          gridTemplateColumns: "1fr",
          gridTemplateRows: "1fr 1fr",
          gap: "6px",
          height: "100%",
          width: "100%",
        };
      case "2x2":
        return {
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gridTemplateRows: "1fr 1fr",
          gap: "6px",
          height: "100%",
          width: "100%",
        };
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", width: "100%", overflow: "hidden" }}>
      {/* Top Multi-Chart Layout Toolbar — responsive */}
      <div
        className="panel-header"
        style={{
          height: "auto",
          minHeight: isMobile ? "auto" : "34px",
          display: "flex",
          flexDirection: isMobile ? "column" : "row",
          alignItems: isMobile ? "stretch" : "center",
          justifyContent: "space-between",
          padding: isMobile ? "6px 8px" : "0 10px",
          gap: isMobile ? "6px" : "0",
          flexShrink: 0,
        }}
      >
        {/* Row 1 on mobile: Title + Maximize state */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span className="live-dot-green" />
            <span style={{ fontSize: isMobile ? "9.5px" : "10.5px", fontWeight: 700, color: "var(--text-primary)", letterSpacing: "0.04em" }}>
              CHART GRID
            </span>
            {focusedSlotId && (
              <span style={{ fontSize: "9px", fontFamily: "var(--font-mono)", color: "var(--accent-blue)", background: "var(--accent-blue-subtle)", border: "1px solid var(--accent-blue-border)", padding: "1px 6px", borderRadius: "3px" }}>
                MAXIMIZED
              </span>
            )}
          </div>

          {/* Layout icons — only on mobile right side */}
          {isMobile && (
            <div className="scroll-x" style={{ gap: "3px" }}>
              {(["1x1", "1x2", "2x1", "2x2"] as GridLayoutMode[]).map((m) => (
                <button
                  key={m}
                  onClick={() => handleSetLayout(m)}
                  style={{
                    background: layoutMode === m && !focusedSlotId ? "var(--bg-surface-elevated)" : "transparent",
                    border: `1px solid ${layoutMode === m && !focusedSlotId ? "var(--border-medium)" : "transparent"}`,
                    borderRadius: "3px",
                    padding: "3px 6px",
                    fontSize: "9.5px",
                    fontWeight: 600,
                    color: layoutMode === m && !focusedSlotId ? "#fff" : "var(--text-muted)",
                    cursor: "pointer",
                  }}
                >
                  {m}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Row 2 on mobile (or same row on desktop): Presets + Engine + Layout */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "6px" }}>
          {/* Presets & Engine Toggle */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
            <div className="scroll-x" style={{ gap: "4px" }}>
              <span style={{ fontSize: "9.5px", color: "var(--text-muted)", flexShrink: 0 }}>Presets:</span>
              {(["crypto", "mtf", "macro"] as const).map((p) => (
                <button
                  key={p}
                  onClick={() => handleApplyPreset(p)}
                  style={{
                    background: "var(--bg-surface-elevated)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "3px",
                    padding: "2px 7px",
                    fontSize: "9.5px",
                    color: "var(--text-secondary)",
                    cursor: "pointer",
                    flexShrink: 0,
                    whiteSpace: "nowrap",
                  }}
                >
                  {p === "crypto" ? "Crypto 4" : p === "mtf" ? "Multi-TF" : "Macro"}
                </button>
              ))}
            </div>

            {/* Engine Switcher */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "2px",
                background: "var(--bg-surface)",
                padding: "2px",
                borderRadius: "4px",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <button
                onClick={() => {
                  soundManager.playClick();
                  setGlobalEngine("native");
                }}
                style={{
                  background: globalEngine === "native" ? "rgba(56, 189, 248, 0.18)" : "transparent",
                  color: globalEngine === "native" ? "#38bdf8" : "var(--text-muted)",
                  border: globalEngine === "native" ? "1px solid rgba(56, 189, 248, 0.4)" : "1px solid transparent",
                  borderRadius: "3px",
                  padding: "2px 7px",
                  fontSize: "9.5px",
                  fontWeight: 700,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "4px",
                }}
                title="Direct high-speed WebSocket/REST tape (Zero DNS dependency, unblocked)"
              >
                <ZapIcon size={10} color={globalEngine === "native" ? "#38bdf8" : "currentColor"} />
                Atlas Native
              </button>
              <button
                onClick={() => {
                  soundManager.playClick();
                  setGlobalEngine("tradingview");
                }}
                style={{
                  background: globalEngine === "tradingview" ? "var(--bg-surface-elevated)" : "transparent",
                  color: globalEngine === "tradingview" ? "var(--text-primary)" : "var(--text-muted)",
                  border: globalEngine === "tradingview" ? "1px solid var(--border-medium)" : "1px solid transparent",
                  borderRadius: "3px",
                  padding: "2px 7px",
                  fontSize: "9.5px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
                title="TradingView Cloud Widget (Requires s.tradingview.com unblocked)"
              >
                TradingView
              </button>
            </div>
          </div>

          {/* Layout buttons — desktop only (already shown on mobile above) */}
          {!isMobile && (
            <div style={{ display: "flex", alignItems: "center", gap: "3px" }}>
              {([
                { mode: "1x1" as GridLayoutMode, Icon: Layout1x1Icon },
                { mode: "1x2" as GridLayoutMode, Icon: Layout1x2Icon },
                { mode: "2x1" as GridLayoutMode, Icon: Layout2x1Icon },
                { mode: "2x2" as GridLayoutMode, Icon: Layout2x2Icon },
              ]).map(({ mode, Icon }) => (
                <button
                  key={mode}
                  onClick={() => handleSetLayout(mode)}
                  style={{
                    background: layoutMode === mode && !focusedSlotId ? "var(--bg-surface-elevated)" : "transparent",
                    border: `1px solid ${layoutMode === mode && !focusedSlotId ? "var(--border-medium)" : "transparent"}`,
                    borderRadius: "3px",
                    padding: "2px 7px",
                    fontSize: "10px",
                    fontWeight: 600,
                    color: layoutMode === mode && !focusedSlotId ? "var(--text-primary)" : "var(--text-muted)",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "4px",
                  }}
                >
                  <Icon size={11} color="currentColor" />
                  <span>{mode}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Grid Container */}
      <div style={{ flex: 1, minHeight: 0, padding: "4px", background: "var(--bg-canvas)" }}>
        <div style={getGridStyle()}>
          {visibleSlots.map((slot) => {
            const isSlotFocused = focusedSlotId === slot.id;

            return (
              <div
                key={slot.id}
                style={{
                  background: "var(--bg-surface-card)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "5px",
                  display: "flex",
                  flexDirection: "column",
                  overflow: "hidden",
                  height: "100%",
                  minHeight: 0,
                  position: "relative",
                }}
              >
                {/* Per-Slot Header */}
                <div
                  style={{
                    height: "28px",
                    background: "var(--bg-surface-elevated)",
                    borderBottom: "1px solid var(--border-subtle)",
                    padding: "0 8px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    flexShrink: 0,
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    {/* Instrument Selector */}
                    <select
                      value={slot.symbol}
                      onChange={(e) => handleUpdateSlotSymbol(slot.id, e.target.value)}
                      style={{
                        background: "var(--bg-surface)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "3px",
                        color: "var(--text-primary)",
                        fontSize: "11px",
                        fontWeight: 600,
                        padding: "1px 4px",
                        outline: "none",
                        cursor: "pointer",
                      }}
                    >
                      {DEFAULT_INSTRUMENTS.map((inst) => (
                        <option key={inst.symbol} value={inst.symbol}>
                          {inst.symbol}
                        </option>
                      ))}
                    </select>

                    <span style={{ fontSize: "9px", color: "var(--text-muted)" }}>{slot.name}</span>
                  </div>

                  {/* Slot Controls (Timeframe & Maximize) */}
                  <div style={{ display: "flex", alignItems: "center", gap: "4px", flexShrink: 0 }}>
                    {/* Timeframe Chips — scroll-x on mobile */}
                    <div className="scroll-x" style={{ gap: "1px", maxWidth: isMobile ? "140px" : "none" }}>
                      {TIMEFRAMES.map((tf) => (
                        <button
                          key={tf.value}
                          onClick={() => handleUpdateSlotInterval(slot.id, tf.value)}
                          style={{
                            background: slot.interval === tf.value ? "var(--accent-blue-subtle)" : "transparent",
                            border: `1px solid ${slot.interval === tf.value ? "var(--accent-blue-border)" : "transparent"}`,
                            borderRadius: "2px",
                            padding: "1px 5px",
                            fontSize: "9px",
                            fontWeight: 600,
                            color: slot.interval === tf.value ? "var(--accent-blue)" : "var(--text-muted)",
                            cursor: "pointer",
                            flexShrink: 0,
                          }}
                        >
                          {tf.label}
                        </button>
                      ))}
                    </div>

                    {/* Maximize / Restore Button */}
                    <button
                      onClick={() => {
                        soundManager.playClick();
                        setFocusedSlotId(isSlotFocused ? null : slot.id);
                      }}
                      style={{
                        background: "var(--bg-surface)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "3px",
                        padding: isMobile ? "2px 5px" : "2px 6px",
                        fontSize: "9px",
                        color: "var(--text-secondary)",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: "3px",
                        flexShrink: 0,
                      }}
                      title={isSlotFocused ? "Restore Grid" : "Maximize this chart"}
                    >
                      {isSlotFocused ? (
                        <><MinimizeIcon size={10} color="currentColor" />{!isMobile && <span>Restore</span>}</>
                      ) : (
                        <><MaximizeIcon size={10} color="currentColor" />{!isMobile && <span>Focus</span>}</>
                      )}
                    </button>
                  </div>
                </div>

                {/* Chart Container */}
                <div style={{ flex: 1, minHeight: 0, position: "relative", overflow: "hidden" }}>
                  <TradingViewChart
                    key={`${slot.id}-${globalEngine}`}
                    symbol={slot.tvSymbol}
                    interval={slot.interval}
                    theme={theme}
                    minHeight="100%"
                    initialEngine={globalEngine}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
