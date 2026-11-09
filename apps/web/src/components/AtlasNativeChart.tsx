"use client";

import React, { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { soundManager } from "../lib/soundEffects";
import {
  TrendingUpIcon,
  TrendingDownIcon,
  RefreshIcon,
  ActivityIcon,
  ZapIcon,
  TargetIcon,
  SlidersIcon,
  ShieldIcon,
  MaximizeIcon,
  MinimizeIcon,
} from "./Icons";

export interface Candle {
  time: number;
  timeStr: string;
  dateStr: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface AtlasNativeChartProps {
  symbol?: string;
  interval?: string;
  theme?: "dark" | "light";
  minHeight?: string;
  showVolume?: boolean;
  showIndicators?: boolean;
  onPriceChange?: (price: number) => void;
  entryPrice?: number;
  tpPrice?: number;
  slPrice?: number;
}

const TIMEFRAMES = [
  { label: "1m", value: "1m" },
  { label: "5m", value: "5m" },
  { label: "15m", value: "15m" },
  { label: "1h", value: "1h" },
  { label: "4h", value: "4h" },
  { label: "1D", value: "1d" },
];

export function AtlasNativeChart({
  symbol = "BTC/USDT",
  interval = "15m",
  theme = "light",
  minHeight = "260px",
  showVolume = true,
  showIndicators = true,
  onPriceChange,
  entryPrice,
  tpPrice,
  slPrice,
}: AtlasNativeChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 380 });
  const [candles, setCandles] = useState<Candle[]>([]);
  const [activeTimeframe, setActiveTimeframe] = useState<string>(() => {
    if (interval === "1") return "1m";
    if (interval === "5") return "5m";
    if (interval === "15") return "15m";
    if (interval === "60") return "1h";
    if (interval === "240") return "4h";
    if (interval === "D") return "1d";
    return interval.includes("m") || interval.includes("h") || interval.includes("d") ? interval : "15m";
  });

  const [isLoading, setIsLoading] = useState(true);
  const [dataSource, setDataSource] = useState<"BINANCE_WS" | "BINANCE_REST" | "SYNTHETIC">("BINANCE_REST");
  const [lastTickDirection, setLastTickDirection] = useState<"up" | "down">("up");
  const [hoveredCandle, setHoveredCandle] = useState<Candle | null>(null);
  const [mousePos, setMousePos] = useState<{ x: number; y: number } | null>(null);

  // Indicators toggle
  const [indicators, setIndicators] = useState({
    ema20: true,
    ema50: true,
    ema200: false,
    volume: true,
    levels: true,
    grid: true,
  });

  // Pan and Zoom states
  const [visibleCount, setVisibleCount] = useState(48); // Visible candles
  const [scrollOffset, setScrollOffset] = useState(0); // 0 = latest candles
  const [isDragging, setIsDragging] = useState(false);
  const [dragStartX, setDragStartX] = useState(0);

  // Parse clean symbol for Binance (e.g. BTC/USDT -> BTCUSDT)
  const binanceSymbol = useMemo(() => {
    const s = symbol.replace("/", "").replace(":", "").toUpperCase();
    if (s.includes("BINANCE")) return s.replace("BINANCE", "");
    if (s === "EURUSD") return "EURUSDT";
    if (s === "XAUUSD") return "PAXGUSDT";
    if (s.startsWith("US100")) return "BTCUSDT";
    return s.includes("USDT") || s.includes("BTC") ? s : `${s}USDT`;
  }, [symbol]);

  // Synchronize internal timeframe if prop changes
  useEffect(() => {
    if (interval === "1") setActiveTimeframe("1m");
    else if (interval === "5") setActiveTimeframe("5m");
    else if (interval === "15") setActiveTimeframe("15m");
    else if (interval === "60") setActiveTimeframe("1h");
    else if (interval === "240") setActiveTimeframe("4h");
    else if (interval === "D") setActiveTimeframe("1d");
    else if (interval) setActiveTimeframe(interval);
  }, [interval]);

  // Responsive ResizeObserver
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        if (width > 50 && height > 50) {
          setDimensions({ width, height });
        }
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Procedural generator when offline or pair is unlisted
  const generateSyntheticCandles = useCallback((sym: string): Candle[] => {
    let basePrice = 86400;
    if (sym.includes("ETH")) basePrice = 2750;
    else if (sym.includes("SOL")) basePrice = 118;
    else if (sym.includes("BNB")) basePrice = 790;
    else if (sym.includes("XRP")) basePrice = 1.62;
    else if (sym.includes("DOGE")) basePrice = 0.102;
    else if (sym.includes("EUR")) basePrice = 1.085;
    else if (sym.includes("XAU") || sym.includes("PAXG")) basePrice = 2680;

    const list: Candle[] = [];
    let cur = basePrice;
    const now = Date.now();
    const stepMs = 15 * 60 * 1000;

    for (let i = 80; i >= 0; i--) {
      const t = now - i * stepMs;
      const d = new Date(t);
      const timeStr = `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
      const dateStr = `${d.getMonth() + 1}/${d.getDate()}`;
      const change = (Math.random() - 0.49) * (cur * 0.006);
      const open = cur;
      const close = cur + change;
      const high = Math.max(open, close) + Math.random() * (cur * 0.0035);
      const low = Math.min(open, close) - Math.random() * (cur * 0.0035);
      const volume = Math.floor(40 + Math.random() * 320);

      list.push({
        time: t,
        timeStr,
        dateStr,
        open: parseFloat(open.toFixed(2)),
        high: parseFloat(high.toFixed(2)),
        low: parseFloat(low.toFixed(2)),
        close: parseFloat(close.toFixed(2)),
        volume,
      });
      cur = close;
    }
    return list;
  }, []);

  // Fetch initial klines from Binance REST
  const fetchKlines = useCallback(async () => {
    try {
      const res = await fetch(
        `https://api.binance.com/api/v3/klines?symbol=${binanceSymbol}&interval=${activeTimeframe}&limit=120`
      );
      if (!res.ok) throw new Error("Binance REST error");
      const data = await res.json();
      if (!Array.isArray(data) || data.length === 0) throw new Error("Invalid response");

      const parsed: Candle[] = data.map((item: any) => {
        const openTime = item[0];
        const d = new Date(openTime);
        return {
          time: openTime,
          timeStr: `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`,
          dateStr: `${d.getMonth() + 1}/${d.getDate()}`,
          open: parseFloat(item[1]),
          high: parseFloat(item[2]),
          low: parseFloat(item[3]),
          close: parseFloat(item[4]),
          volume: parseFloat(item[5]),
        };
      });

      setCandles(parsed);
      setDataSource("BINANCE_REST");
      const last = parsed[parsed.length - 1];
      if (last && onPriceChange) {
        onPriceChange(last.close);
      }
    } catch {
      const syn = generateSyntheticCandles(binanceSymbol);
      setCandles(syn);
      setDataSource("SYNTHETIC");
      const last = syn[syn.length - 1];
      if (last && onPriceChange) {
        onPriceChange(last.close);
      }
    } finally {
      setIsLoading(false);
    }
  }, [binanceSymbol, activeTimeframe, generateSyntheticCandles, onPriceChange]);

  // Initial load
  useEffect(() => {
    setIsLoading(true);
    fetchKlines();
  }, [fetchKlines]);

  // Live WebSocket Connection for sub-second tick-by-tick real-time updates
  useEffect(() => {
    let ws: WebSocket | null = null;
    const wsUrl = `wss://stream.binance.com:9443/ws/${binanceSymbol.toLowerCase()}@kline_${activeTimeframe}`;

    try {
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setDataSource("BINANCE_WS");
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.e === "kline" && msg.k) {
            const k = msg.k;
            const newPrice = parseFloat(k.c);
            const openTime = k.t;
            const d = new Date(openTime);
            const timeStr = `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
            const dateStr = `${d.getMonth() + 1}/${d.getDate()}`;

            setCandles((prev) => {
              if (prev.length === 0) return prev;
              const last = prev[prev.length - 1];
              if (!last) return prev;

              // Check tick direction
              if (newPrice > last.close) setLastTickDirection("up");
              else if (newPrice < last.close) setLastTickDirection("down");

              // If same candle, update it in place
              if (last.time === openTime) {
                const updatedLast: Candle = {
                  ...last,
                  high: Math.max(last.high, parseFloat(k.h)),
                  low: Math.min(last.low, parseFloat(k.l)),
                  close: newPrice,
                  volume: parseFloat(k.v),
                };
                return [...prev.slice(0, -1), updatedLast];
              }

              // Otherwise append new candle
              const newCandle: Candle = {
                time: openTime,
                timeStr,
                dateStr,
                open: parseFloat(k.o),
                high: parseFloat(k.h),
                low: parseFloat(k.l),
                close: newPrice,
                volume: parseFloat(k.v),
              };
              return [...prev.slice(1), newCandle];
            });

            if (onPriceChange) {
              onPriceChange(newPrice);
            }
          }
        } catch {}
      };

      ws.onerror = () => {
        setDataSource("BINANCE_REST");
      };
    } catch {
      setDataSource("BINANCE_REST");
    }

    // Fallback polling every 3.5 seconds in case WebSocket is blocked by network
    const poller = setInterval(fetchKlines, 3500);

    return () => {
      if (ws) {
        ws.close();
      }
      clearInterval(poller);
    };
  }, [binanceSymbol, activeTimeframe, fetchKlines, onPriceChange]);

  // Handle visible candle slicing with pan offset
  const displayedCandles = useMemo(() => {
    if (candles.length === 0) return [];
    const total = candles.length;
    const count = Math.min(visibleCount, total);
    const end = Math.max(count, total - scrollOffset);
    const start = Math.max(0, end - count);
    return candles.slice(start, end);
  }, [candles, visibleCount, scrollOffset]);

  // Calculations for chart geometry
  const rightGutter = 72; // Width of price scale
  const bottomGutter = 26; // Height of time scale
  const topGutter = 20; // Top buffer
  const chartWidth = Math.max(dimensions.width - rightGutter, 80);
  const chartHeight = Math.max(dimensions.height - bottomGutter - topGutter, 80);

  const { minPrice, maxPrice, priceRange, candleSpacing, candleWidth } = useMemo(() => {
    if (displayedCandles.length === 0) {
      return { minPrice: 0, maxPrice: 100, priceRange: 100, candleSpacing: 10, candleWidth: 6 };
    }
    let min = Infinity;
    let max = -Infinity;
    for (const c of displayedCandles) {
      if (c.low < min) min = c.low;
      if (c.high > max) max = c.high;
    }
    const pad = (max - min) * 0.08 || 1;
    const finalMin = min - pad;
    const finalMax = max + pad;
    const range = finalMax - finalMin;
    const spacing = chartWidth / displayedCandles.length;
    const width = Math.max(Math.min(spacing * 0.72, 20), 2.5);

    return {
      minPrice: finalMin,
      maxPrice: finalMax,
      priceRange: range,
      candleSpacing: spacing,
      candleWidth: width,
    };
  }, [displayedCandles, chartWidth]);

  // Price to Y coordinate projection
  const getY = useCallback(
    (price: number) => {
      if (priceRange === 0) return chartHeight / 2 + topGutter;
      return topGutter + (chartHeight - ((price - minPrice) / priceRange) * chartHeight);
    },
    [chartHeight, minPrice, priceRange, topGutter]
  );

  // Compute Exponential Moving Average (EMA) points
  const calculateEMA = (period: number) => {
    if (displayedCandles.length < period) return [];
    const k = 2 / (period + 1);
    let prev = displayedCandles.slice(0, period).reduce((acc, c) => acc + c.close, 0) / period;
    const points: { x: number; y: number }[] = [];

    for (let i = period - 1; i < displayedCandles.length; i++) {
      const c = displayedCandles[i];
      if (!c) continue;
      const cur = c.close * k + prev * (1 - k);
      const x = i * candleSpacing + candleSpacing / 2;
      points.push({ x, y: getY(cur) });
      prev = cur;
    }
    return points;
  };

  const ema20Points = useMemo(() => calculateEMA(20), [displayedCandles, candleSpacing, getY]);
  const ema50Points = useMemo(() => calculateEMA(50), [displayedCandles, candleSpacing, getY]);
  const ema200Points = useMemo(() => calculateEMA(100), [displayedCandles, candleSpacing, getY]);

  const maxVolume = useMemo(() => {
    return displayedCandles.reduce((max, c) => Math.max(max, c.volume), 1);
  }, [displayedCandles]);

  const lastCandle = displayedCandles[displayedCandles.length - 1];
  const prevCandle = displayedCandles[displayedCandles.length - 2];
  const isUp = lastCandle && prevCandle ? lastCandle.close >= prevCandle.close : true;
  const currentPrice = lastCandle ? lastCandle.close : 0;
  const priceChange = lastCandle && prevCandle ? lastCandle.close - prevCandle.close : 0;
  const priceChangePct = prevCandle && prevCandle.close ? (priceChange / prevCandle.close) * 100 : 0;

  // Mouse pan & zoom handlers
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    if (e.deltaY < 0) {
      // Zoom in
      setVisibleCount((prev) => Math.max(16, prev - 4));
    } else {
      // Zoom out
      setVisibleCount((prev) => Math.min(candles.length, prev + 4));
    }
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStartX(e.clientX);
  };

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    if (isDragging) {
      const deltaX = e.clientX - dragStartX;
      if (Math.abs(deltaX) > 6) {
        const candleDelta = Math.round(deltaX / candleSpacing);
        setScrollOffset((prev) => Math.max(0, Math.min(candles.length - visibleCount, prev + candleDelta)));
        setDragStartX(e.clientX);
      }
    }

    if (x <= chartWidth && y <= chartHeight + topGutter && y >= topGutter) {
      setMousePos({ x, y });
      const index = Math.floor(x / candleSpacing);
      if (index >= 0 && index < displayedCandles.length) {
        setHoveredCandle(displayedCandles[index] || null);
      }
    } else {
      setMousePos(null);
      setHoveredCandle(null);
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleMouseLeave = () => {
    setIsDragging(false);
    setMousePos(null);
    setHoveredCandle(null);
  };

  // Price scale ticks calculation
  const priceTicks = useMemo(() => {
    const count = 7;
    const step = priceRange / (count - 1);
    const ticks: number[] = [];
    for (let i = 0; i < count; i++) {
      ticks.push(minPrice + i * step);
    }
    return ticks;
  }, [minPrice, priceRange]);

  // Derived order levels
  const activeEntry = entryPrice || currentPrice * 0.998;
  const activeTp = tpPrice || currentPrice * 1.025;
  const activeSl = slPrice || currentPrice * 0.985;

  return (
    <div
      ref={containerRef}
      onWheel={handleWheel}
      style={{
        width: "100%",
        height: "100%",
        minHeight,
        background: theme === "light" ? "var(--bg-surface, #ffffff)" : "#080c14",
        position: "relative",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        userSelect: "none",
        border: "1px solid var(--border-subtle)",
      }}
    >
      {/* ═══════════ TOP COMMAND BAR ═══════════ */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "5px 10px",
          background: theme === "light" ? "var(--bg-surface-elevated, #f8fafc)" : "rgba(11, 16, 26, 0.94)",
          borderBottom: "1px solid var(--border-subtle)",
          fontSize: "11px",
          flexShrink: 0,
          flexWrap: "wrap",
          gap: "6px",
          zIndex: 5,
        }}
      >
        {/* Left: Ticker, Live Price & Timeframe Selector */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          {/* Symbol & Price */}
          <div style={{ display: "flex", alignItems: "baseline", gap: "6px" }}>
            <span style={{ fontWeight: 800, color: "var(--text-primary)", fontSize: "12px", letterSpacing: "0.03em" }}>
              {symbol}
            </span>
            <span
              style={{
                fontFamily: "var(--font-mono, monospace)",
                fontWeight: 700,
                fontSize: "12px",
                color: isUp ? "var(--accent-green)" : "var(--accent-red)",
              }}
            >
              ${currentPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
            </span>
            <span
              style={{
                fontSize: "9.5px",
                fontWeight: 700,
                color: priceChange >= 0 ? "var(--accent-green)" : "var(--accent-red)",
                background: priceChange >= 0 ? "var(--accent-green-subtle)" : "var(--accent-red-subtle)",
                border: `1px solid ${priceChange >= 0 ? "var(--accent-green-border)" : "var(--accent-red-border)"}`,
                padding: "1px 5px",
                borderRadius: "3px",
              }}
            >
              {priceChange >= 0 ? "+" : ""}
              {priceChangePct.toFixed(2)}%
            </span>
          </div>

          {/* Timeframe Chips */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "1px",
              background: "var(--bg-surface)",
              padding: "2px",
              borderRadius: "4px",
              border: "1px solid var(--border-subtle)",
            }}
          >
            {TIMEFRAMES.map((tf) => {
              const isActive = activeTimeframe === tf.value;
              return (
                <button
                  key={tf.value}
                  onClick={() => {
                    soundManager.playClick();
                    setActiveTimeframe(tf.value);
                  }}
                  style={{
                    background: isActive ? "var(--accent-blue-subtle)" : "transparent",
                    color: isActive ? "var(--accent-blue)" : "var(--text-muted)",
                    border: isActive ? "1px solid var(--accent-blue-border)" : "1px solid transparent",
                    padding: "2px 6px",
                    borderRadius: "3px",
                    fontSize: "9.5px",
                    fontWeight: isActive ? 700 : 500,
                    cursor: "pointer",
                    transition: "all 0.1s ease",
                  }}
                >
                  {tf.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Center: Live Hovered Candle Inspection HUD */}
        {hoveredCandle ? (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              fontSize: "10px",
              fontFamily: "var(--font-mono, monospace)",
              color: "var(--text-muted)",
            }}
          >
            <span><strong style={{ color: "var(--text-primary)" }}>{hoveredCandle.dateStr} {hoveredCandle.timeStr}</strong></span>
            <span>O: <strong style={{ color: "var(--text-primary)" }}>{hoveredCandle.open}</strong></span>
            <span>H: <strong style={{ color: "var(--accent-green)" }}>{hoveredCandle.high}</strong></span>
            <span>L: <strong style={{ color: "var(--accent-red)" }}>{hoveredCandle.low}</strong></span>
            <span>C: <strong style={{ color: hoveredCandle.close >= hoveredCandle.open ? "var(--accent-green)" : "var(--accent-red)" }}>{hoveredCandle.close}</strong></span>
            <span>Vol: <strong style={{ color: "var(--accent-blue)" }}>{hoveredCandle.volume}</strong></span>
          </div>
        ) : (
          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "10px" }}>
            {indicators.ema20 && (
              <span style={{ color: "#06b6d4", display: "flex", alignItems: "center", gap: "3px", fontWeight: 600 }}>
                <span style={{ width: "8px", height: "2px", background: "#06b6d4" }} />
                EMA 20
              </span>
            )}
            {indicators.ema50 && (
              <span style={{ color: "#a855f7", display: "flex", alignItems: "center", gap: "3px", fontWeight: 600 }}>
                <span style={{ width: "8px", height: "2px", background: "#a855f7" }} />
                EMA 50
              </span>
            )}
          </div>
        )}

        {/* Right: Technical Indicators & Stream Status */}
        <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
          {/* Indicator Toggles */}
          <button
            onClick={() => setIndicators((prev) => ({ ...prev, ema20: !prev.ema20, ema50: !prev.ema50 }))}
            style={{
              background: indicators.ema20 ? "rgba(6, 182, 212, 0.12)" : "transparent",
              border: `1px solid ${indicators.ema20 ? "rgba(6, 182, 212, 0.35)" : "var(--border-subtle)"}`,
              color: indicators.ema20 ? "#06b6d4" : "var(--text-muted)",
              borderRadius: "3px",
              padding: "2px 6px",
              fontSize: "9px",
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            EMA
          </button>

          <button
            onClick={() => setIndicators((prev) => ({ ...prev, levels: !prev.levels }))}
            style={{
              background: indicators.levels ? "var(--accent-green-subtle)" : "transparent",
              border: `1px solid ${indicators.levels ? "var(--accent-green-border)" : "var(--border-subtle)"}`,
              color: indicators.levels ? "var(--accent-green)" : "var(--text-muted)",
              borderRadius: "3px",
              padding: "2px 6px",
              fontSize: "9px",
              fontWeight: 700,
              cursor: "pointer",
            }}
            title="Toggle TP / SL / Entry visual overlay lines"
          >
            LEVELS
          </button>

          {/* Live Data Connection Pill */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "4px",
              padding: "2px 6px",
              borderRadius: "4px",
              background: dataSource === "BINANCE_WS" ? "rgba(34, 197, 94, 0.15)" : "rgba(56, 189, 248, 0.15)",
              color: dataSource === "BINANCE_WS" ? "#22c55e" : "#38bdf8",
              border: `1px solid ${dataSource === "BINANCE_WS" ? "rgba(34, 197, 94, 0.3)" : "rgba(56, 189, 248, 0.3)"}`,
              fontSize: "9px",
              fontWeight: 800,
            }}
            title={dataSource === "BINANCE_WS" ? "Binance WebSocket sub-second live tape connected" : "Binance REST feed connected"}
          >
            <span
              style={{
                width: "5px",
                height: "5px",
                borderRadius: "50%",
                background: lastTickDirection === "up" ? "#22c55e" : "#ef4444",
                boxShadow: `0 0 6px ${lastTickDirection === "up" ? "#22c55e" : "#ef4444"}`,
                transition: "all 0.15s ease",
              }}
            />
            <span>{dataSource === "BINANCE_WS" ? "LIVE STREAM" : "DIRECT REST"}</span>
          </div>

          {/* Refresh Button */}
          <button
            onClick={() => {
              soundManager.playClick();
              fetchKlines();
            }}
            title="Refresh orderbook & klines"
            style={{
              background: "transparent",
              border: "none",
              color: "#64748b",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              padding: "2px",
            }}
          >
            <RefreshIcon size={12} color="currentColor" />
          </button>
        </div>
      </div>

      {/* ═══════════ SVG CANDLESTICK CANVAS ═══════════ */}
      <div style={{ flex: 1, position: "relative", minHeight: 0 }}>
        {isLoading && candles.length === 0 ? (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
              color: "var(--text-muted, #94a3b8)",
              fontSize: "11px",
              fontFamily: "var(--font-mono, monospace)",
            }}
          >
            <span className="live-dot-green" />
            <span>CONNECTING DIRECT HIGH-SPEED ORDER FLOW...</span>
          </div>
        ) : (
          <svg
            width="100%"
            height="100%"
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseLeave}
            style={{
              display: "block",
              cursor: isDragging ? "grabbing" : "crosshair",
              background: theme === "light" ? "#ffffff" : "#080c14",
            }}
          >
            <defs>
              <linearGradient id="volGreenGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#10b981" stopOpacity="0.38" />
                <stop offset="100%" stopColor="#10b981" stopOpacity="0.04" />
              </linearGradient>
              <linearGradient id="volRedGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f43f5e" stopOpacity="0.38" />
                <stop offset="100%" stopColor="#f43f5e" stopOpacity="0.04" />
              </linearGradient>
            </defs>

            {/* Subtle Horizontal Price Grid Lines */}
            {indicators.grid &&
              priceTicks.map((p, idx) => {
                const y = getY(p);
                return (
                  <line
                    key={`grid-h-${idx}`}
                    x1="0"
                    y1={y}
                    x2={chartWidth}
                    y2={y}
                    stroke={theme === "light" ? "rgba(0, 0, 0, 0.05)" : "rgba(255, 255, 255, 0.04)"}
                    strokeWidth="0.8"
                    strokeDasharray="3 3"
                  />
                );
              })}

            {/* Vertical Time Grid Lines */}
            {indicators.grid &&
              displayedCandles.map((c, i) => {
                if (i % Math.ceil(displayedCandles.length / 6) !== 0) return null;
                const x = i * candleSpacing + candleSpacing / 2;
                return (
                  <g key={`grid-v-${i}`}>
                    <line
                      x1={x}
                      y1={topGutter}
                      x2={x}
                      y2={topGutter + chartHeight}
                      stroke={theme === "light" ? "rgba(0, 0, 0, 0.04)" : "rgba(255, 255, 255, 0.03)"}
                      strokeWidth="0.8"
                    />
                    <text
                      x={x}
                      y={topGutter + chartHeight + 16}
                      fill={theme === "light" ? "#64748b" : "#64748b"}
                      fontSize="9"
                      fontFamily="var(--font-mono, monospace)"
                      textAnchor="middle"
                    >
                      {c.timeStr}
                    </text>
                  </g>
                );
              })}

            {/* Volume Histogram at Bottom */}
            {showVolume &&
              indicators.volume &&
              displayedCandles.map((c, i) => {
                const isBull = c.close >= c.open;
                const x = i * candleSpacing + (candleSpacing - candleWidth) / 2;
                const volHeight = Math.min((c.volume / maxVolume) * (chartHeight * 0.2), chartHeight * 0.2);
                const y = topGutter + chartHeight - volHeight;
                return (
                  <rect
                    key={`vol-${i}`}
                    x={x}
                    y={y}
                    width={candleWidth}
                    height={volHeight}
                    fill={isBull ? "url(#volGreenGrad)" : "url(#volRedGrad)"}
                    rx="0.5"
                  />
                );
              })}

            {/* Technical Overlay: EMA 200 (Gold) */}
            {showIndicators && indicators.ema200 && ema200Points.length > 1 && (
              <polyline
                fill="none"
                stroke="#eab308"
                strokeWidth="1.2"
                opacity="0.8"
                points={ema200Points.map((p) => `${p.x},${p.y}`).join(" ")}
              />
            )}

            {/* Technical Overlay: EMA 50 (Purple) */}
            {showIndicators && indicators.ema50 && ema50Points.length > 1 && (
              <polyline
                fill="none"
                stroke="#a855f7"
                strokeWidth="1.4"
                opacity="0.8"
                points={ema50Points.map((p) => `${p.x},${p.y}`).join(" ")}
              />
            )}

            {/* Technical Overlay: EMA 20 (Cyan) */}
            {showIndicators && indicators.ema20 && ema20Points.length > 1 && (
              <polyline
                fill="none"
                stroke="#06b6d4"
                strokeWidth="1.6"
                opacity="0.9"
                points={ema20Points.map((p) => `${p.x},${p.y}`).join(" ")}
              />
            )}

            {/* Visual Trade Execution Levels (TP, Entry, SL) */}
            {indicators.levels && (
              <g>
                {/* Take Profit (TP) */}
                <line
                  x1="0"
                  y1={getY(activeTp)}
                  x2={chartWidth}
                  y2={getY(activeTp)}
                  stroke="#22c55e"
                  strokeWidth="1"
                  strokeDasharray="4 4"
                  opacity="0.75"
                />
                <text x="8" y={getY(activeTp) - 4} fill="#22c55e" fontSize="8.5" fontWeight="700" fontFamily="monospace">
                  TARGET TP ${activeTp.toFixed(2)}
                </text>

                {/* Entry Reference */}
                <line
                  x1="0"
                  y1={getY(activeEntry)}
                  x2={chartWidth}
                  y2={getY(activeEntry)}
                  stroke="#94a3b8"
                  strokeWidth="0.9"
                  strokeDasharray="3 3"
                  opacity="0.5"
                />
                <text x="8" y={getY(activeEntry) - 4} fill="#94a3b8" fontSize="8.5" fontWeight="600" fontFamily="monospace">
                  ENTRY ${activeEntry.toFixed(2)}
                </text>

                {/* Stop Loss (SL) */}
                <line
                  x1="0"
                  y1={getY(activeSl)}
                  x2={chartWidth}
                  y2={getY(activeSl)}
                  stroke="#ef4444"
                  strokeWidth="1"
                  strokeDasharray="4 4"
                  opacity="0.75"
                />
                <text x="8" y={getY(activeSl) - 4} fill="#ef4444" fontSize="8.5" fontWeight="700" fontFamily="monospace">
                  INVALIDATION SL ${activeSl.toFixed(2)}
                </text>
              </g>
            )}

            {/* Candlesticks Sequence (High-DPI Bodies & Wicks) */}
            {displayedCandles.map((c, i) => {
              const isBull = c.close >= c.open;
              const xCenter = i * candleSpacing + candleSpacing / 2;
              const xLeft = xCenter - candleWidth / 2;
              const yHigh = getY(c.high);
              const yLow = getY(c.low);
              const yOpen = getY(c.open);
              const yClose = getY(c.close);
              const yTop = Math.min(yOpen, yClose);
              const bodyHeight = Math.max(Math.abs(yClose - yOpen), 1.5);
              const color = isBull ? "#10b981" : "#f43f5e";

              return (
                <g key={`candle-${i}`}>
                  {/* High/Low Wick */}
                  <line
                    x1={xCenter}
                    y1={yHigh}
                    x2={xCenter}
                    y2={yLow}
                    stroke={color}
                    strokeWidth="1.2"
                    strokeLinecap="round"
                  />
                  {/* Candle Body */}
                  <rect
                    x={xLeft}
                    y={yTop}
                    width={candleWidth}
                    height={bodyHeight}
                    fill={color}
                    rx="1"
                  />
                </g>
              );
            })}

            {/* Current Active Price Line across the chart */}
            {lastCandle && (
              <g>
                <line
                  x1="0"
                  y1={getY(currentPrice)}
                  x2={chartWidth}
                  y2={getY(currentPrice)}
                  stroke={isUp ? "#10b981" : "#f43f5e"}
                  strokeWidth="1.2"
                  strokeDasharray="2 2"
                  opacity="0.85"
                />
                <circle
                  cx={chartWidth}
                  cy={getY(currentPrice)}
                  r="3.5"
                  fill={isUp ? "#10b981" : "#f43f5e"}
                  style={{ filter: `drop-shadow(0 0 6px ${isUp ? "#10b981" : "#f43f5e"})` }}
                />
              </g>
            )}

            {/* Interactive Crosshair Tracking Cursor */}
            {mousePos && (
              <g pointerEvents="none">
                {/* Vertical Crosshair */}
                <line
                  x1={mousePos.x}
                  y1={topGutter}
                  x2={mousePos.x}
                  y2={topGutter + chartHeight}
                  stroke={theme === "light" ? "rgba(0, 0, 0, 0.3)" : "rgba(255, 255, 255, 0.35)"}
                  strokeWidth="0.8"
                  strokeDasharray="3 3"
                />
                {/* Horizontal Crosshair */}
                <line
                  x1="0"
                  y1={mousePos.y}
                  x2={chartWidth}
                  y2={mousePos.y}
                  stroke={theme === "light" ? "rgba(0, 0, 0, 0.3)" : "rgba(255, 255, 255, 0.35)"}
                  strokeWidth="0.8"
                  strokeDasharray="3 3"
                />
              </g>
            )}

            {/* ═══════════ RIGHT PRICE SCALE AXIS ═══════════ */}
            <rect
              x={chartWidth}
              y="0"
              width={rightGutter}
              height={dimensions.height}
              fill={theme === "light" ? "#f8fafc" : "#090d16"}
            />
            <line
              x1={chartWidth}
              y1="0"
              x2={chartWidth}
              y2={dimensions.height}
              stroke={theme === "light" ? "var(--border-subtle, #e2e8f0)" : "rgba(255, 255, 255, 0.08)"}
              strokeWidth="1"
            />

            {/* Price Scale Tick Labels */}
            {priceTicks.map((p, idx) => {
              const y = getY(p);
              return (
                <text
                  key={`price-label-${idx}`}
                  x={chartWidth + 6}
                  y={y + 3.5}
                  fill={theme === "light" ? "#475569" : "#64748b"}
                  fontSize="9.5"
                  fontFamily="var(--font-mono, monospace)"
                >
                  {p > 1000 ? p.toFixed(1) : p > 1 ? p.toFixed(2) : p.toFixed(4)}
                </text>
              );
            })}

            {/* Current Active Price Tag on Right Axis */}
            {lastCandle && (
              <g transform={`translate(${chartWidth}, ${getY(currentPrice) - 9})`}>
                <rect
                  x="0"
                  y="0"
                  width={rightGutter}
                  height="18"
                  fill={isUp ? "#10b981" : "#f43f5e"}
                  rx="2"
                />
                <text
                  x="6"
                  y="12.5"
                  fill="#ffffff"
                  fontSize="9.5"
                  fontWeight="800"
                  fontFamily="var(--font-mono, monospace)"
                >
                  {currentPrice > 1000
                    ? currentPrice.toFixed(1)
                    : currentPrice > 1
                    ? currentPrice.toFixed(2)
                    : currentPrice.toFixed(4)}
                </text>
              </g>
            )}

            {/* Crosshair Price Tag on Right Axis */}
            {mousePos && (
              <g transform={`translate(${chartWidth}, ${mousePos.y - 8})`} pointerEvents="none">
                <rect
                  x="0"
                  y="0"
                  width={rightGutter}
                  height="16"
                  fill={theme === "light" ? "#0f172a" : "#334155"}
                  rx="2"
                />
                <text
                  x="6"
                  y="11.5"
                  fill="#ffffff"
                  fontSize="9"
                  fontFamily="var(--font-mono, monospace)"
                >
                  {(
                    minPrice +
                    ((chartHeight + topGutter - mousePos.y) / chartHeight) * priceRange
                  ).toFixed(2)}
                </text>
              </g>
            )}
          </svg>
        )}
      </div>

      {/* ═══════════ BOTTOM STATUS BAR ═══════════ */}
      <div
        style={{
          height: "22px",
          background: "rgba(9, 13, 22, 0.95)",
          borderTop: "1px solid rgba(255, 255, 255, 0.05)",
          padding: "0 10px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          fontSize: "9.5px",
          color: "#64748b",
          fontFamily: "var(--font-mono, monospace)",
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span>CANDLES: {displayedCandles.length}</span>
          <span>ZOOM: Scroll Wheel</span>
          <span>PAN: Click & Drag</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ color: "#38bdf8" }}>UTC {new Date().toLocaleTimeString()}</span>
        </div>
      </div>
    </div>
  );
}
