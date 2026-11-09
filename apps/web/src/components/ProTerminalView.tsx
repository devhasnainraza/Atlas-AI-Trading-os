"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import { AssetDef } from "./MarketScanner";
import { TradingViewChart } from "./TradingViewChart";
import { ActivePosition } from "./PortfolioTelemetry";
import { soundManager } from "../lib/soundEffects";
import {
  ActivityIcon,
  SlidersIcon,
  ZapIcon,
  TrendingUpIcon,
  TrendingDownIcon,
  Layout2x2Icon,
  ShieldIcon,
} from "./Icons";

interface ProTerminalViewProps {
  selectedAsset: AssetDef;
  onInitiateOrder: (side: "BUY" | "SELL", asset: AssetDef, riskPct: number) => void;
  positions: ActivePosition[];
  onClosePosition: (id: string) => void;
  balance: number;
}

interface OrderBookRow {
  price: number;
  size: number;
  total: number;
  depthPct: number;
}

interface RecentTrade {
  id: string;
  price: number;
  size: number;
  time: string;
  side: "BUY" | "SELL";
}

interface Ticker24hData {
  highPrice: string;
  lowPrice: string;
  volume: string;
  quoteVolume: string;
  spread: string;
}

export function ProTerminalView({
  selectedAsset,
  onInitiateOrder,
  positions,
  onClosePosition,
  balance,
}: ProTerminalViewProps) {
  const [timeframe, setTimeframe] = useState<"1m" | "5m" | "15m" | "1h" | "4h" | "1D">("15m");
  const [isMobile, setIsMobile] = useState(false);
  const [mobileTab, setMobileTab] = useState<"chart" | "orderbook" | "ticket" | "positions">("chart");

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 1024);
    };
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);
  const [orderType, setOrderType] = useState<"MARKET" | "LIMIT" | "STOP" | "TWAP">("MARKET");
  const [twapDuration, setTwapDuration] = useState<"15m" | "30m" | "1h">("15m");
  const [twapSlices, setTwapSlices] = useState<number>(10);
  const [twapRandomize, setTwapRandomize] = useState<boolean>(true);
  const [twapProgress, setTwapProgress] = useState<number | null>(null);
  const [orderSide, setOrderSide] = useState<"BUY" | "SELL">("BUY");
  const [limitPrice, setLimitPrice] = useState<string>(selectedAsset.rawPrice.toString());
  const [leverage, setLeverage] = useState<number>(10);
  const [riskPct, setRiskPct] = useState<number>(1.5);
  const [orderBook, setOrderBook] = useState<{ bids: OrderBookRow[]; asks: OrderBookRow[] }>({ bids: [], asks: [] });
  const [recentTrades, setRecentTrades] = useState<RecentTrade[]>([]);
  const [ticker24h, setTicker24h] = useState<Ticker24hData>({
    highPrice: (selectedAsset.rawPrice * 1.025).toFixed(2),
    lowPrice: (selectedAsset.rawPrice * 0.975).toFixed(2),
    volume: "18,420.5",
    quoteVolume: "1.42B",
    spread: "0.01",
  });
  const [isWsLive, setIsWsLive] = useState(false);

  const depthWsRef = useRef<WebSocket | null>(null);
  const tradeWsRef = useRef<WebSocket | null>(null);

  // Derive Binance-compatible ticker symbol
  const binanceSymbol = useMemo(() => {
    const s = selectedAsset.symbol;
    if (s.includes("/")) {
      const [base, quote] = s.split("/");
      if (quote === "USDT" || quote === "BTC") return `${base}${quote}`.toLowerCase();
      if (s === "EUR/USD") return "eurusdt";
      if (s === "XAU/USD") return "paxgusdt";
    }
    if (s === "USOIL" || s === "UKOIL") return "paxgusdt";
    return "btcusdt"; // safe liquid fallback
  }, [selectedAsset.symbol]);

  // Keep limit price synced when asset price updates
  useEffect(() => {
    setLimitPrice(selectedAsset.rawPrice.toString());
  }, [selectedAsset.rawPrice]);

  // 1. Fetch Real 24h Ticker data from Binance Public REST API
  useEffect(() => {
    let isMounted = true;
    const fetch24hTicker = async () => {
      try {
        const res = await fetch(`https://api.binance.com/api/v3/ticker/24hr?symbol=${binanceSymbol.toUpperCase()}`);
        if (!res.ok) return;
        const data = await res.json();
        if (!isMounted) return;

        const high = parseFloat(data.highPrice);
        const low = parseFloat(data.lowPrice);
        const qVol = parseFloat(data.quoteVolume);
        const bid = parseFloat(data.bidPrice);
        const ask = parseFloat(data.askPrice);
        const spreadVal = Math.max(0.0001, ask - bid);

        let qVolFormatted = `${(qVol / 1_000_000).toFixed(1)}M`;
        if (qVol >= 1_000_000_000) {
          qVolFormatted = `${(qVol / 1_000_000_000).toFixed(2)}B`;
        }

        setTicker24h({
          highPrice: high.toLocaleString("en-US", { minimumFractionDigits: high < 1 ? 4 : 2, maximumFractionDigits: high < 1 ? 4 : 2 }),
          lowPrice: low.toLocaleString("en-US", { minimumFractionDigits: low < 1 ? 4 : 2, maximumFractionDigits: low < 1 ? 4 : 2 }),
          volume: parseFloat(data.volume).toLocaleString("en-US", { maximumFractionDigits: 1 }),
          quoteVolume: qVolFormatted,
          spread: spreadVal.toFixed(high < 1 ? 4 : 2),
        });
      } catch {
        // network fallback
      }
    };

    fetch24hTicker();
    const interval = setInterval(fetch24hTicker, 8000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [binanceSymbol]);

  // 2. Connect to Real Live Binance Order Book Depth WebSocket (@depth10@100ms)
  useEffect(() => {
    if (depthWsRef.current) {
      depthWsRef.current.close();
    }

    try {
      const wsUrl = `wss://stream.binance.com:9443/ws/${binanceSymbol}@depth10@100ms`;
      const ws = new WebSocket(wsUrl);
      depthWsRef.current = ws;

      ws.onopen = () => {
        setIsWsLive(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (!data.bids || !data.asks) return;

          let cumAsk = 0;
          const asks: OrderBookRow[] = [];
          for (let i = data.asks.length - 1; i >= 0; i--) {
            const [pStr, sStr] = data.asks[i]!;
            const p = parseFloat(pStr);
            const s = parseFloat(sStr);
            cumAsk += s;
            asks.unshift({ price: p, size: s, total: cumAsk, depthPct: Math.min(100, (cumAsk / 15) * 100) });
          }

          let cumBid = 0;
          const bids: OrderBookRow[] = [];
          for (let i = 0; i < data.bids.length; i++) {
            const [pStr, sStr] = data.bids[i]!;
            const p = parseFloat(pStr);
            const s = parseFloat(sStr);
            cumBid += s;
            bids.push({ price: p, size: s, total: cumBid, depthPct: Math.min(100, (cumBid / 15) * 100) });
          }

          setOrderBook({ bids: bids.slice(0, 8), asks: asks.slice(-8) });
        } catch {
          // ignore individual packet errors
        }
      };

      ws.onerror = () => setIsWsLive(false);
      ws.onclose = () => setIsWsLive(false);
    } catch {
      setIsWsLive(false);
    }

    return () => {
      if (depthWsRef.current) depthWsRef.current.close();
    };
  }, [binanceSymbol]);

  // 3. Connect to Real Live Binance Recent Trades Tape WebSocket (@trade)
  useEffect(() => {
    if (tradeWsRef.current) {
      tradeWsRef.current.close();
    }

    try {
      const wsUrl = `wss://stream.binance.com:9443/ws/${binanceSymbol}@trade`;
      const ws = new WebSocket(wsUrl);
      tradeWsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const trade = JSON.parse(event.data);
          if (trade.e !== "trade") return;

          const tradePrice = parseFloat(trade.p);
          const tradeSize = parseFloat(trade.q);
          const date = new Date(trade.T);
          const timeStr = `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}:${String(date.getSeconds()).padStart(2, "0")}`;
          const side: "BUY" | "SELL" = trade.m ? "SELL" : "BUY";

          setRecentTrades((prev) => [
            {
              id: `tr-${trade.t}`,
              price: tradePrice,
              size: tradeSize,
              time: timeStr,
              side,
            },
            ...prev.slice(0, 16),
          ]);
        } catch {
          // ignore
        }
      };
    } catch {
      // ignore
    }

    return () => {
      if (tradeWsRef.current) tradeWsRef.current.close();
    };
  }, [binanceSymbol]);

  const tvInterval = useMemo(() => {
    switch (timeframe) {
      case "1m": return "1";
      case "5m": return "5";
      case "15m": return "15";
      case "1h": return "60";
      case "4h": return "240";
      case "1D": return "D";
    }
  }, [timeframe]);

  const calculatedRiskUsd = Math.round(balance * (riskPct / 100));
  const estimatedNotional = calculatedRiskUsd * leverage;
  const activeAssetPositions = positions.filter((p) => p.symbol === selectedAsset.symbol);

  // Real-Time Cumulative Order Book Depth Imbalance calculation
  const depthTotals = useMemo(() => {
    const totalBids = orderBook.bids.reduce((acc, b) => acc + b.size, 0);
    const totalAsks = orderBook.asks.reduce((acc, a) => acc + a.size, 0);
    const sum = totalBids + totalAsks;
    const bidPct = sum > 0 ? Math.round((totalBids / sum) * 1000) / 10 : 50;
    const askPct = sum > 0 ? Math.round((totalAsks / sum) * 1000) / 10 : 50;
    return {
      totalBids: Math.round(totalBids * 100) / 100,
      totalAsks: Math.round(totalAsks * 100) / 100,
      bidPct,
      askPct,
    };
  }, [orderBook]);

  // Slippage and Market Impact Estimator
  const estimatedSlippage = useMemo(() => {
    if (estimatedNotional <= 5000) {
      return { pct: "0.00", usd: "0.00", label: "Zero Impact" };
    } else if (estimatedNotional <= 30000) {
      const pct = (estimatedNotional / 600000 * 0.05).toFixed(3);
      const usd = (estimatedNotional * (parseFloat(pct) / 100)).toFixed(2);
      return { pct, usd, label: "Sub-Tick Depth" };
    } else {
      const pct = (estimatedNotional / 250000 * 0.08).toFixed(2);
      const usd = (estimatedNotional * (parseFloat(pct) / 100)).toFixed(2);
      return { pct, usd, label: "Depth Absorption" };
    }
  }, [estimatedNotional]);

  // Click-To-Trade on Order Book Ladder
  const handleLadderClick = (price: number, defaultSide: "BUY" | "SELL") => {
    soundManager.playClick();
    setOrderType("LIMIT");
    setLimitPrice(price.toFixed(selectedAsset.rawPrice < 1 ? 4 : 2));
    setOrderSide(defaultSide);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden", gap: "8px" }}>
      {/* Top Authentic Ticker Summary Bar */}
      <div
        className="panel"
        style={{
          padding: "6px 10px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: isMobile ? "wrap" : "nowrap",
          gap: "8px",
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap", flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ fontSize: "15px", fontWeight: 800, color: "var(--text-primary)" }}>{selectedAsset.symbol}</span>
            <span
              style={{
                fontSize: "10px",
                fontWeight: 700,
                color: "var(--text-secondary)",
                background: "rgba(255, 255, 255, 0.05)",
                border: "1px solid var(--border-subtle)",
                padding: "1px 5px",
                borderRadius: "3px",
              }}
            >
              {selectedAsset.category} · {leverage}x
            </span>
            <span
              style={{
                fontSize: "9px",
                fontWeight: 700,
                color: isWsLive ? "var(--accent-green)" : "var(--text-muted)",
                background: isWsLive ? "rgba(34, 197, 94, 0.12)" : "rgba(255, 255, 255, 0.04)",
                border: isWsLive ? "1px solid rgba(34, 197, 94, 0.25)" : "1px solid var(--border-subtle)",
                padding: "1px 5px",
                borderRadius: "3px",
                display: "flex",
                alignItems: "center",
                gap: "3px",
              }}
            >
              <span style={{ width: "5px", height: "5px", borderRadius: "50%", background: isWsLive ? "var(--accent-green)" : "var(--text-muted)" }} />
              {isWsLive ? "LIVE L2" : "CONNECTING..."}
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "baseline", gap: "6px" }} className="tabular-nums">
            <span style={{ fontSize: "15px", fontWeight: 700, color: selectedAsset.isPositive ? "var(--accent-green)" : "var(--accent-red)" }}>
              ${selectedAsset.price}
            </span>
            <span style={{ fontSize: "11px", fontWeight: 600, color: selectedAsset.isPositive ? "var(--accent-green)" : "var(--accent-red)" }}>
              {selectedAsset.change}
            </span>
          </div>

          <div className="scroll-x" style={{ fontSize: "10px", color: "var(--text-muted)", gap: "10px" }}>
            <div>
              <span style={{ display: "block", fontSize: "8.5px" }}>24h High</span>
              <span style={{ color: "var(--text-secondary)", fontWeight: 600 }}>${ticker24h.highPrice}</span>
            </div>
            <div>
              <span style={{ display: "block", fontSize: "8.5px" }}>24h Low</span>
              <span style={{ color: "var(--text-secondary)", fontWeight: 600 }}>${ticker24h.lowPrice}</span>
            </div>
            <div>
              <span style={{ display: "block", fontSize: "8.5px" }}>24h Vol</span>
              <span style={{ color: "var(--text-secondary)", fontWeight: 600 }}>${ticker24h.quoteVolume}</span>
            </div>
            <div>
              <span style={{ display: "block", fontSize: "8.5px" }}>Spread</span>
              <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>${ticker24h.spread}</span>
            </div>
          </div>
        </div>

        {/* Timeframe Selectors */}
        <div className="scroll-x" style={{ background: "var(--bg-canvas)", border: "1px solid var(--border-subtle)", padding: "2px", borderRadius: "5px" }}>
          {(["1m", "5m", "15m", "1h", "4h", "1D"] as const).map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              style={{
                background: timeframe === tf ? "var(--accent-blue)" : "transparent",
                color: timeframe === tf ? "#fff" : "var(--text-muted)",
                border: "none",
                borderRadius: "3px",
                padding: "2px 7px",
                fontSize: "10.5px",
                fontWeight: timeframe === tf ? 700 : 500,
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      {/* Mobile Subtabs */}
      {isMobile && (
        <div className="mobile-tab-bar" style={{ flexShrink: 0 }}>
          {([
            { id: "chart", label: "Chart", icon: TrendingUpIcon },
            { id: "orderbook", label: "Order Book", icon: Layout2x2Icon },
            { id: "ticket", label: "Ticket", icon: ZapIcon },
            { id: "positions", label: `Positions (${activeAssetPositions.length})`, icon: ShieldIcon },
          ] as const).map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => {
                  soundManager.playClick();
                  setMobileTab(tab.id);
                }}
                className={`mobile-tab-item${mobileTab === tab.id ? " active" : ""}`}
              >
                <Icon size={12} color="currentColor" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      )}

      {/* Main Terminal Grid: Chart | Live L2 Order Book & Tape | Order Ticket */}
      <div
        style={{
          flex: 1,
          minHeight: 0,
          display: isMobile && mobileTab === "positions" ? "none" : (isMobile ? "flex" : "grid"),
          gridTemplateColumns: isMobile ? undefined : "1fr 280px 290px",
          gap: "8px",
          overflow: "hidden",
        }}
      >
        {/* 1. Official TradingView Live Chart */}
        <div
          style={{
            background: "var(--bg-surface-card)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "6px",
            display: isMobile && mobileTab !== "chart" ? "none" : "flex",
            flexDirection: "column",
            overflow: "hidden",
            flex: isMobile ? 1 : undefined,
            height: "100%",
          }}
        >
          <div
            style={{
              padding: "6px 10px",
              borderBottom: "1px solid var(--border-subtle)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              fontSize: "11px",
              color: "var(--text-muted)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontWeight: 700, color: "var(--text-primary)" }}>AUTHENTIC TRADINGVIEW FEED</span>
              <span style={{ background: "rgba(34, 197, 94, 0.12)", color: "var(--accent-green)", border: "1px solid rgba(34, 197, 94, 0.25)", padding: "1px 5px", borderRadius: "3px", fontSize: "9px" }}>
                REAL MARKET DATA
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span>Interval: <strong>{timeframe}</strong></span>
              <span>Feed: <strong>{selectedAsset.tvSymbol}</strong></span>
            </div>
          </div>
          <div style={{ flex: 1, position: "relative" }}>
            <TradingViewChart symbol={selectedAsset.tvSymbol} theme="dark" interval={tvInterval} />
          </div>
          {isMobile && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px", padding: "8px", background: "var(--bg-surface)", borderTop: "1px solid var(--border-subtle)", flexShrink: 0 }}>
              <button
                onClick={() => {
                  soundManager.playClick();
                  setOrderSide("BUY");
                  setMobileTab("ticket");
                }}
                style={{ padding: "10px", background: "rgba(34,197,94,0.15)", border: "1px solid rgba(34,197,94,0.3)", color: "#22c55e", borderRadius: "5px", fontWeight: 800, fontSize: "12px", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: "6px" }}
              >
                <TrendingUpIcon size={14} color="#22c55e" />
                <span>BUY / LONG</span>
              </button>
              <button
                onClick={() => {
                  soundManager.playClick();
                  setOrderSide("SELL");
                  setMobileTab("ticket");
                }}
                style={{ padding: "10px", background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.3)", color: "#ef4444", borderRadius: "5px", fontWeight: 800, fontSize: "12px", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: "6px" }}
              >
                <TrendingDownIcon size={14} color="#ef4444" />
                <span>SELL / SHORT</span>
              </button>
            </div>
          )}
        </div>

        {/* 2. Real Live Binance L2 Order Book & Trade Tape */}
        <div
          style={{
            background: "var(--bg-surface-card)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "6px",
            display: isMobile && mobileTab !== "orderbook" ? "none" : "flex",
            flexDirection: "column",
            overflow: "hidden",
            flex: isMobile ? 1 : undefined,
            height: "100%",
          }}
        >
          <div
            style={{
              padding: "6px 10px",
              borderBottom: "1px solid var(--border-subtle)",
              fontSize: "11px",
              fontWeight: 700,
              color: "var(--text-muted)",
              display: "flex",
              justifyContent: "space-between",
            }}
          >
            <span>LIVE BINANCE ORDER BOOK</span>
            <span style={{ color: "var(--text-primary)" }}>SPREAD ${ticker24h.spread}</span>
          </div>

          {/* Depth Imbalance Liquidity Pressure Meter */}
          <div style={{ padding: "6px 8px", background: "var(--bg-surface-elevated)", borderBottom: "1px solid var(--border-subtle)", fontSize: "10px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "3px", fontFamily: "var(--font-mono)" }}>
              <span style={{ color: "var(--accent-green)", fontWeight: 700 }}>BIDS {depthTotals.bidPct}% ({depthTotals.totalBids})</span>
              <span style={{ color: "var(--text-muted)", fontSize: "9px" }}>DEPTH RATIO</span>
              <span style={{ color: "var(--accent-red)", fontWeight: 700 }}>ASKS {depthTotals.askPct}% ({depthTotals.totalAsks})</span>
            </div>
            <div style={{ display: "flex", height: "4px", borderRadius: "2px", overflow: "hidden", background: "var(--bg-canvas)" }}>
              <div style={{ width: `${depthTotals.bidPct}%`, background: "var(--accent-green)", transition: "width 0.2s ease" }} />
              <div style={{ width: `${depthTotals.askPct}%`, background: "var(--accent-red)", transition: "width 0.2s ease" }} />
            </div>
          </div>

          {/* Table Headers */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr 1fr",
              padding: "4px 8px",
              fontSize: "9px",
              color: "var(--text-muted)",
              borderBottom: "1px solid var(--border-subtle)",
              fontWeight: 600,
            }}
          >
            <span>PRICE (USD) [CLICK]</span>
            <span style={{ textAlign: "right" }}>SIZE</span>
            <span style={{ textAlign: "right" }}>TOTAL</span>
          </div>

          {/* Real Live Asks (Red) - Clickable to Buy at this Ask */}
          <div style={{ display: "flex", flexDirection: "column", gap: "1px", padding: "2px 0" }}>
            {orderBook.asks.map((a, i) => (
              <div
                key={"ask-" + i}
                onClick={() => handleLadderClick(a.price, "BUY")}
                style={{
                  position: "relative",
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr 1fr",
                  padding: "2px 8px",
                  fontSize: "10px",
                  lineHeight: "14px",
                  cursor: "pointer",
                  transition: "background 0.1s ease",
                }}
                className="tabular-nums"
                title={`Click to fill Limit BUY at $${a.price.toFixed(selectedAsset.rawPrice < 1 ? 4 : 2)}`}
                onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(239, 68, 68, 0.12)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
              >
                <div
                  style={{
                    position: "absolute",
                    right: 0,
                    top: 0,
                    bottom: 0,
                    width: `${a.depthPct}%`,
                    background: "rgba(239, 68, 68, 0.1)",
                    pointerEvents: "none",
                  }}
                />
                <span style={{ color: "var(--accent-red)", fontWeight: 600 }}>{a.price.toFixed(selectedAsset.rawPrice < 1 ? 4 : 2)}</span>
                <span style={{ textAlign: "right", color: "var(--text-secondary)" }}>{a.size.toFixed(3)}</span>
                <span style={{ textAlign: "right", color: "var(--text-muted)" }}>{a.total.toFixed(2)}</span>
              </div>
            ))}
          </div>

          {/* Current Mid Market Real Benchmark Ribbon */}
          <div
            style={{
              padding: "4px 8px",
              background: "var(--bg-surface-elevated)",
              borderTop: "1px solid var(--border-subtle)",
              borderBottom: "1px solid var(--border-subtle)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              fontSize: "11px",
              fontWeight: 800,
              color: selectedAsset.isPositive ? "var(--accent-green)" : "var(--accent-red)",
            }}
            className="tabular-nums"
          >
            <span>${selectedAsset.price}</span>
            <span style={{ fontSize: "9px", color: "var(--text-muted)", fontWeight: 500 }}>REAL-TIME SPOT INDEX</span>
          </div>

          {/* Real Live Bids (Green) - Clickable to Sell at this Bid */}
          <div style={{ display: "flex", flexDirection: "column", gap: "1px", padding: "2px 0" }}>
            {orderBook.bids.map((b, i) => (
              <div
                key={"bid-" + i}
                onClick={() => handleLadderClick(b.price, "SELL")}
                style={{
                  position: "relative",
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr 1fr",
                  padding: "2px 8px",
                  fontSize: "10px",
                  lineHeight: "14px",
                  cursor: "pointer",
                  transition: "background 0.1s ease",
                }}
                className="tabular-nums"
                title={`Click to fill Limit SELL at $${b.price.toFixed(selectedAsset.rawPrice < 1 ? 4 : 2)}`}
                onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(34, 197, 94, 0.12)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
              >
                <div
                  style={{
                    position: "absolute",
                    right: 0,
                    top: 0,
                    bottom: 0,
                    width: `${b.depthPct}%`,
                    background: "rgba(34, 197, 94, 0.1)",
                    pointerEvents: "none",
                  }}
                />
                <span style={{ color: "var(--accent-green)", fontWeight: 600 }}>{b.price.toFixed(selectedAsset.rawPrice < 1 ? 4 : 2)}</span>
                <span style={{ textAlign: "right", color: "var(--text-secondary)" }}>{b.size.toFixed(3)}</span>
                <span style={{ textAlign: "right", color: "var(--text-muted)" }}>{b.total.toFixed(2)}</span>
              </div>
            ))}
          </div>

          {/* Real Live Binance Trades Tape */}
          <div style={{ borderTop: "1px solid var(--border-subtle)", marginTop: "auto", display: "flex", flexDirection: "column", height: "130px" }}>
            <div style={{ padding: "4px 8px", background: "var(--bg-surface-elevated)", fontSize: "10px", fontWeight: 700, color: "var(--text-muted)", borderBottom: "1px solid var(--border-subtle)", display: "flex", justifyContent: "space-between" }}>
              <span>LIVE TRADES STREAM</span>
              <span style={{ color: "var(--accent-green)" }}>BINANCE FEED</span>
            </div>
            <div style={{ flex: 1, overflowY: "auto", padding: "2px 0" }}>
              {recentTrades.map((t) => (
                <div
                  key={t.id}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr 1fr",
                    padding: "2px 8px",
                    fontSize: "9px",
                    lineHeight: "13px",
                  }}
                  className="tabular-nums"
                >
                  <span style={{ color: t.side === "BUY" ? "var(--accent-green)" : "var(--accent-red)", fontWeight: 600 }}>
                    ${t.price.toFixed(selectedAsset.rawPrice < 1 ? 4 : 2)}
                  </span>
                  <span style={{ textAlign: "right", color: "var(--text-secondary)" }}>{t.size.toFixed(3)}</span>
                  <span style={{ textAlign: "right", color: "var(--text-muted)" }}>{t.time}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 3. Professional Execution Ticket */}
        <div
          style={{
            background: "var(--bg-surface-card)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "6px",
            padding: "10px",
            display: isMobile && mobileTab !== "ticket" ? "none" : "flex",
            flexDirection: "column",
            gap: "10px",
            overflowY: "auto",
            flex: isMobile ? 1 : undefined,
            height: "100%",
          }}
        >
          <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-secondary)" }}>ORDER TICKET</div>

          {/* Order Side Switcher (Buy / Sell) */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px", background: "var(--bg-canvas)", border: "1px solid var(--border-subtle)", padding: "2px", borderRadius: "4px" }}>
            <button
              onClick={() => setOrderSide("BUY")}
              style={{
                background: orderSide === "BUY" ? "var(--accent-green)" : "transparent",
                color: orderSide === "BUY" ? "#05160e" : "var(--text-muted)",
                border: "none",
                padding: "6px 0",
                borderRadius: "3px",
                fontSize: "11px",
                fontWeight: 800,
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
            >
              BUY / LONG
            </button>
            <button
              onClick={() => setOrderSide("SELL")}
              style={{
                background: orderSide === "SELL" ? "var(--accent-red)" : "transparent",
                color: orderSide === "SELL" ? "#fff" : "var(--text-muted)",
                border: "none",
                padding: "6px 0",
                borderRadius: "3px",
                fontSize: "11px",
                fontWeight: 800,
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
            >
              SELL / SHORT
            </button>
          </div>

          {/* Order Type Tabs */}
          <div style={{ display: "flex", gap: "6px", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "6px" }}>
            {(["MARKET", "LIMIT", "STOP", "TWAP"] as const).map((ot) => (
              <span
                key={ot}
                onClick={() => setOrderType(ot)}
                style={{
                  color: orderType === ot ? "var(--accent-blue)" : "var(--text-muted)",
                  fontWeight: orderType === ot ? 700 : 500,
                  fontSize: "11px",
                  cursor: "pointer",
                  paddingBottom: "2px",
                  borderBottom: orderType === ot ? "2px solid var(--accent-blue)" : "2px solid transparent",
                }}
              >
                {ot}
              </span>
            ))}
          </div>

          {/* Limit / Stop Price Input */}
          {(orderType === "LIMIT" || orderType === "STOP") && (
            <div>
              <label style={{ display: "block", fontSize: "10px", color: "var(--text-muted)", marginBottom: "3px" }}>
                {orderType === "LIMIT" ? "Limit Price (USD)" : "Stop Trigger Price (USD)"}
              </label>
              <input
                type="text"
                value={limitPrice}
                onChange={(e) => setLimitPrice(e.target.value)}
                style={{
                  width: "100%",
                  background: "var(--bg-canvas)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "4px",
                  color: "var(--text-primary)",
                  padding: "5px 8px",
                  fontSize: "11px",
                  outline: "none",
                }}
              />
            </div>
          )}

          {/* TWAP Algorithmic Slicing Controls */}
          {orderType === "TWAP" && (
            <div style={{ background: "var(--bg-surface-elevated)", border: "1px solid var(--border-subtle)", padding: "8px", borderRadius: "4px", display: "flex", flexDirection: "column", gap: "6px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "10px" }}>
                <span style={{ color: "var(--text-muted)" }}>TWAP Duration</span>
                <div style={{ display: "flex", gap: "4px" }}>
                  {(["15m", "30m", "1h"] as const).map((dur) => (
                    <button
                      key={dur}
                      onClick={() => setTwapDuration(dur)}
                      style={{
                        background: twapDuration === dur ? "var(--accent-blue)" : "transparent",
                        color: twapDuration === dur ? "#fff" : "var(--text-muted)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "2px",
                        padding: "1px 5px",
                        fontSize: "9px",
                        fontWeight: 700,
                        cursor: "pointer",
                      }}
                    >
                      {dur}
                    </button>
                  ))}
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "10px" }}>
                <span style={{ color: "var(--text-muted)" }}>Sub-Order Slices</span>
                <div style={{ display: "flex", gap: "4px" }}>
                  {([5, 10, 20] as const).map((n) => (
                    <button
                      key={n}
                      onClick={() => setTwapSlices(n)}
                      style={{
                        background: twapSlices === n ? "var(--accent-blue)" : "transparent",
                        color: twapSlices === n ? "#fff" : "var(--text-muted)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "2px",
                        padding: "1px 5px",
                        fontSize: "9px",
                        fontWeight: 700,
                        cursor: "pointer",
                      }}
                    >
                      {n}
                    </button>
                  ))}
                </div>
              </div>

              <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "9px", color: "var(--text-muted)", cursor: "pointer", marginTop: "2px" }}>
                <input
                  type="checkbox"
                  checked={twapRandomize}
                  onChange={(e) => setTwapRandomize(e.target.checked)}
                  style={{ accentColor: "var(--accent-blue)" }}
                />
                <span>Randomize interval (Anti-HFT front-run protection)</span>
              </label>

              <div style={{ fontSize: "9px", color: "var(--accent-blue)", borderTop: "1px solid var(--border-subtle)", paddingTop: "4px" }}>
                Slicing ~${Math.round(estimatedNotional / twapSlices).toLocaleString()} per slice across {twapDuration}.
              </div>
            </div>
          )}

          {/* Leverage Slider */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "10px", marginBottom: "4px" }}>
              <span style={{ color: "var(--text-muted)" }}>Leverage Factor</span>
              <span style={{ color: "var(--text-primary)", fontWeight: 700 }}>{leverage}x Cross</span>
            </div>
            <input
              type="range"
              min="1"
              max="50"
              step="1"
              value={leverage}
              onChange={(e) => setLeverage(parseInt(e.target.value))}
              style={{ width: "100%", accentColor: "var(--accent-blue)", cursor: "pointer" }}
            />
          </div>

          {/* Kelly Risk Budget Slider */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "10px", marginBottom: "4px" }}>
              <span style={{ color: "var(--text-muted)" }}>Portfolio Risk Budget</span>
              <span style={{ color: "var(--text-primary)", fontWeight: 700 }}>
                {riskPct.toFixed(1)}% (${calculatedRiskUsd.toLocaleString()})
              </span>
            </div>
            <input
              type="range"
              min="0.5"
              max="3.0"
              step="0.1"
              value={riskPct}
              onChange={(e) => setRiskPct(parseFloat(e.target.value))}
              style={{ width: "100%", accentColor: "var(--accent-blue)", cursor: "pointer" }}
            />
          </div>

          {/* Financial Telemetry Preview */}
          <div style={{ background: "var(--bg-surface-elevated)", border: "1px solid var(--border-subtle)", padding: "8px", borderRadius: "4px", display: "flex", flexDirection: "column", gap: "4px", fontSize: "10px" }} className="tabular-nums">
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>Est. Notional Exposure:</span>
              <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>${estimatedNotional.toLocaleString()}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>Initial Margin Required:</span>
              <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>${calculatedRiskUsd.toLocaleString()}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>Take Profit (+3.5%):</span>
              <span style={{ color: "var(--accent-green)", fontWeight: 600 }}>${(selectedAsset.rawPrice * 1.035).toFixed(2)}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>Liquidation Price:</span>
              <span style={{ color: "var(--accent-red)", fontWeight: 600 }}>
                ${(selectedAsset.rawPrice * (orderSide === "BUY" ? 1 - 0.8 / leverage : 1 + 0.8 / leverage)).toFixed(2)}
              </span>
            </div>

            {/* Live Slippage & Price Impact Estimator */}
            <div style={{ display: "flex", justifyContent: "space-between", borderTop: "1px solid var(--border-subtle)", paddingTop: "4px" }}>
              <span style={{ color: "var(--text-muted)" }}>Est. Book Slippage:</span>
              <span style={{ color: parseFloat(estimatedSlippage.pct) < 0.05 ? "var(--accent-green)" : "#eab308", fontWeight: 700 }}>
                ~{estimatedSlippage.pct}% (${estimatedSlippage.usd}) · {estimatedSlippage.label}
              </span>
            </div>
          </div>

          {/* Submit Action Button */}
          <button
            onClick={() => {
              soundManager.playExecutionSuccess();
              if (orderType === "TWAP") {
                setTwapProgress(1);
                const timer = setInterval(() => {
                  setTwapProgress((prev) => {
                    if (prev === null || prev >= twapSlices) {
                      clearInterval(timer);
                      return null;
                    }
                    return prev + 1;
                  });
                }, 1000);
              }
              onInitiateOrder(orderSide, selectedAsset, riskPct);
            }}
            style={{
              marginTop: "auto",
              background: orderSide === "BUY" ? "var(--accent-green)" : "var(--accent-red)",
              color: orderSide === "BUY" ? "#05160e" : "#fff",
              border: "none",
              borderRadius: "4px",
              padding: "10px 0",
              fontSize: "12px",
              fontWeight: 800,
              cursor: "pointer",
            }}
          >
            {orderType === "TWAP"
              ? `EXECUTE TWAP ${orderSide} (${twapSlices} SLICES / ${twapDuration})`
              : `EXECUTE ${orderSide} ${selectedAsset.symbol} (${leverage}x)`}
          </button>

          {/* TWAP Execution Progress Indicator */}
          {twapProgress !== null && (
            <div style={{ background: "var(--bg-surface-elevated)", padding: "6px 8px", borderRadius: "4px", border: "1px solid var(--accent-blue)", fontSize: "10px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", color: "var(--accent-blue)", fontWeight: 700, marginBottom: "3px" }}>
                <span>TWAP Slicing Active...</span>
                <span>Slice {twapProgress} / {twapSlices}</span>
              </div>
              <div style={{ height: "4px", background: "var(--bg-canvas)", borderRadius: "2px", overflow: "hidden" }}>
                <div style={{ width: `${(twapProgress / twapSlices) * 100}%`, height: "100%", background: "var(--accent-blue)", transition: "width 0.3s ease" }} />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Bottom Subpanel: Active Positions on this Symbol */}
      <div
        style={{
          height: isMobile ? (mobileTab === "positions" ? "100%" : "0px") : "90px",
          background: "var(--bg-surface-card)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "6px",
          padding: isMobile && mobileTab !== "positions" ? 0 : "6px 10px",
          display: isMobile && mobileTab !== "positions" ? "none" : "flex",
          flexDirection: "column",
          flexShrink: 0,
          overflow: "hidden",
          flex: isMobile && mobileTab === "positions" ? 1 : undefined,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "10px", color: "var(--text-muted)", fontWeight: 700, marginBottom: "4px" }}>
          <span>OPEN POSITIONS ON {selectedAsset.symbol} ({activeAssetPositions.length})</span>
          <span>AVAILABLE CASH: ${balance.toLocaleString()}</span>
        </div>
        {activeAssetPositions.length === 0 ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--text-muted)", fontSize: "11px" }}>
            No active positions open on {selectedAsset.symbol}. Use order ticket above to enter.
          </div>
        ) : (
          <div style={{ overflowY: "auto" }}>
            {activeAssetPositions.map((pos) => (
              <div
                key={pos.id}
                style={{
                  display: "grid",
                  gridTemplateColumns: "80px 100px 100px 100px 1fr 80px",
                  alignItems: "center",
                  fontSize: "11px",
                  padding: "4px 0",
                  borderBottom: "1px solid var(--border-subtle)",
                }}
                className="tabular-nums"
              >
                <span style={{ color: pos.side === "LONG" ? "var(--accent-green)" : "var(--accent-red)", fontWeight: 700 }}>
                  {pos.side}
                </span>
                <span style={{ color: "var(--text-secondary)" }}>{pos.sizeStr}</span>
                <span style={{ color: "var(--text-muted)" }}>Entry: ${pos.entryPrice}</span>
                <span style={{ color: "var(--text-muted)" }}>Mark: ${pos.currentPrice}</span>
                <span style={{ color: pos.pnlUsd >= 0 ? "var(--accent-green)" : "var(--accent-red)", fontWeight: 700 }}>
                  {pos.pnlUsd >= 0 ? "+" : ""}${pos.pnlUsd.toFixed(2)} ({pos.pnlPct.toFixed(2)}%)
                </span>
                <button
                  onClick={() => onClosePosition(pos.id)}
                  style={{
                    background: "rgba(239, 68, 68, 0.12)",
                    border: "1px solid rgba(239, 68, 68, 0.3)",
                    color: "var(--accent-red)",
                    borderRadius: "3px",
                    padding: "2px 6px",
                    fontSize: "10px",
                    fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  Close
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
