"use client";

import React, { useState } from "react";

export function TradingChartHUD() {
  const [activeTimeframe, setActiveTimeframe] = useState("15m");
  const timeframes = ["1m", "5m", "15m", "1h", "4h", "1D"];

  // 24 realistic candles (OHLCV)
  const candles = [
    { o: 61800, h: 62200, l: 61700, c: 62100, v: 50 },
    { o: 62100, h: 62300, l: 61950, c: 62050, v: 42 },
    { o: 62050, h: 62450, l: 61900, c: 62400, v: 65 },
    { o: 62400, h: 62700, l: 62300, c: 62650, v: 75 },
    { o: 62650, h: 62800, l: 62450, c: 62500, v: 48 },
    { o: 62500, h: 62600, l: 62200, c: 62300, v: 55 },
    { o: 62300, h: 62750, l: 62250, c: 62700, v: 70 },
    { o: 62700, h: 63100, l: 62600, c: 63000, v: 92 },
    { o: 63000, h: 63250, l: 62850, c: 63150, v: 80 },
    { o: 63150, h: 63400, l: 63000, c: 63050, v: 62 },
    { o: 63050, h: 63200, l: 62700, c: 62800, v: 74 },
    { o: 62800, h: 63100, l: 62650, c: 63000, v: 68 },
    { o: 63000, h: 63500, l: 62900, c: 63450, v: 110 },
    { o: 63450, h: 63800, l: 63300, c: 63700, v: 125 },
    { o: 63700, h: 63950, l: 63550, c: 63850, v: 105 },
    { o: 63850, h: 64100, l: 63650, c: 63700, v: 85 },
    { o: 63700, h: 63850, l: 63200, c: 63350, v: 95 },
    { o: 63350, h: 63600, l: 63100, c: 63250, v: 72 },
    { o: 63250, h: 63550, l: 63050, c: 63480, v: 84 },
    { o: 63480, h: 63900, l: 63400, c: 63820, v: 115 },
    { o: 63820, h: 64200, l: 63750, c: 64150, v: 130 },
    { o: 64150, h: 64450, l: 63950, c: 64300, v: 140 },
    { o: 64300, h: 64500, l: 64100, c: 64250, v: 98 },
    { o: 64250, h: 64600, l: 64180, c: 64520, v: 118 },
  ];

  const minPrice = 61500;
  const maxPrice = 64800;
  const priceRange = maxPrice - minPrice;

  const svgWidth = 720;
  const svgHeight = 280;
  const chartWidth = svgWidth - 65; // 65px reserved for right price axis
  const candleSpacing = chartWidth / candles.length;
  const candleWidth = Math.max(candleSpacing * 0.65, 4);

  const getY = (price: number) => {
    return svgHeight - ((price - minPrice) / priceRange) * (svgHeight - 40) - 20;
  };

  // EMA-20 points
  const ema20 = candles
    .map((c, i) => `${i * candleSpacing + candleWidth / 2},${getY(c.c * 0.9985)}`)
    .join(" ");

  // Price levels
  const tp1Price = 64400;
  const entryPrice = 63250;
  const slPrice = 62100;

  const [isStaleSim, setIsStaleSim] = useState(false);
  const [quoteAge, setQuoteAge] = useState(0.3);

  return (
    <div className="panel" style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Chart Top Bar */}
      <div className="panel-header" style={{ flexWrap: "wrap", gap: "8px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: "6px" }}>
            <span style={{ color: "#fff", fontWeight: 700, fontSize: "12px" }}>BTC/USDT</span>
            <span className="tabular-nums" style={{ color: "var(--accent-green)", fontWeight: 600, fontSize: "11px" }}>
              $64,520.00 (+3.42%)
            </span>
          </div>

          {/* Timeframe Selector */}
          <div style={{ display: "flex", alignItems: "center", gap: "1px", background: "var(--bg-canvas)", borderRadius: "4px", padding: "2px" }}>
            {timeframes.map((tf) => (
              <button
                key={tf}
                onClick={() => setActiveTimeframe(tf)}
                style={{
                  background: activeTimeframe === tf ? "var(--border-medium)" : "transparent",
                  color: activeTimeframe === tf ? "#fff" : "var(--text-muted)",
                  border: "none",
                  borderRadius: "3px",
                  padding: "2px 6px",
                  fontSize: "10px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>

        {/* Freshness Badge, Venue & Session State (T057, FR-015, FR-018) */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "10px" }}>
          <span style={{ background: "rgba(255,255,255,0.05)", color: "var(--text-muted)", padding: "2px 6px", borderRadius: "3px" }}>
            VENUE: BINANCE
          </span>
          <span style={{ background: "rgba(16, 185, 129, 0.12)", color: "var(--accent-green)", padding: "2px 6px", borderRadius: "3px", fontWeight: 600 }}>
            SESSION: OPEN (24/7)
          </span>
          <span
            onClick={() => {
              setIsStaleSim(!isStaleSim);
              setQuoteAge(isStaleSim ? 0.3 : 14.2);
            }}
            title="Click to toggle simulated feed staleness"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "4px",
              padding: "2px 8px",
              borderRadius: "4px",
              fontSize: "10px",
              fontWeight: 700,
              cursor: "pointer",
              background: isStaleSim ? "rgba(239, 68, 68, 0.15)" : "rgba(16, 185, 129, 0.15)",
              color: isStaleSim ? "#ef4444" : "#10b981",
              border: `1px solid ${isStaleSim ? "rgba(239, 68, 68, 0.3)" : "rgba(16, 185, 129, 0.3)"}`,
            }}
          >
            <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: isStaleSim ? "#ef4444" : "#10b981" }} />
            {isStaleSim ? `STALE (${quoteAge}s · feed degraded)` : `LIVE (fresh · ${quoteAge}s)`}
          </span>
        </div>
      </div>

      {/* SVG Canvas Area */}
      <div style={{ position: "relative", flex: 1, minHeight: "220px", background: "var(--bg-canvas)" }}>
        <svg width="100%" height="100%" viewBox={`0 0 ${svgWidth} ${svgHeight}`} preserveAspectRatio="none">
          {/* Subtle Horizontal Grid lines */}
          {[62000, 62500, 63000, 63500, 64000, 64500].map((p) => {
            const y = getY(p);
            return (
              <g key={p}>
                <line x1="0" y1={y} x2={chartWidth} y2={y} stroke="var(--border-subtle)" strokeWidth="0.8" />
              </g>
            );
          })}

          {/* Right Axis Background */}
          <rect x={chartWidth} y="0" width={svgWidth - chartWidth} height={svgHeight} fill="var(--bg-surface)" />
          <line x1={chartWidth} y1="0" x2={chartWidth} y2={svgHeight} stroke="var(--border-subtle)" strokeWidth="1" />

          {/* Right Axis Price Labels */}
          {[62000, 62500, 63000, 63500, 64000, 64500].map((p) => {
            const y = getY(p);
            return (
              <text key={p} x={chartWidth + 8} y={y + 3} fill="var(--text-muted)" fontSize="9" fontFamily="monospace">
                {p}
              </text>
            );
          })}

          {/* Smart Stop: TP1 Level */}
          <line x1="0" y1={getY(tp1Price)} x2={chartWidth} y2={getY(tp1Price)} stroke="var(--accent-green)" strokeWidth="1" strokeDasharray="3,3" />
          <rect x={chartWidth} y={getY(tp1Price) - 8} width={svgWidth - chartWidth} height="16" fill="var(--accent-green-subtle)" />
          <text x={chartWidth + 6} y={getY(tp1Price) + 3} fill="var(--accent-green)" fontSize="8" fontWeight="700" fontFamily="monospace">
            TP 64.4k
          </text>

          {/* Entry Level */}
          <line x1="0" y1={getY(entryPrice)} x2={chartWidth} y2={getY(entryPrice)} stroke="#fff" strokeWidth="0.8" strokeDasharray="2,2" opacity="0.6" />
          <rect x={chartWidth} y={getY(entryPrice) - 7} width={svgWidth - chartWidth} height="14" fill="rgba(255,255,255,0.06)" />
          <text x={chartWidth + 6} y={getY(entryPrice) + 3} fill="#fff" fontSize="8" fontWeight="600" fontFamily="monospace">
            EN 63.2k
          </text>

          {/* Stop Loss Level */}
          <line x1="0" y1={getY(slPrice)} x2={chartWidth} y2={getY(slPrice)} stroke="var(--accent-red)" strokeWidth="1" strokeDasharray="3,3" />
          <rect x={chartWidth} y={getY(slPrice) - 8} width={svgWidth - chartWidth} height="16" fill="var(--accent-red-subtle)" />
          <text x={chartWidth + 6} y={getY(slPrice) + 3} fill="var(--accent-red)" fontSize="8" fontWeight="700" fontFamily="monospace">
            SL 62.1k
          </text>

          {/* EMA Curve */}
          <polyline fill="none" stroke="var(--accent-cyan)" strokeWidth="1.4" points={ema20} opacity="0.75" />

          {/* Candlesticks & Volume */}
          {candles.map((c, i) => {
            const isBullish = c.c >= c.o;
            const x = i * candleSpacing + (candleSpacing - candleWidth) / 2;
            const yHigh = getY(c.h);
            const yLow = getY(c.l);
            const yTop = getY(Math.max(c.o, c.c));
            const yBottom = getY(Math.min(c.o, c.c));
            const candleHeight = Math.max(yBottom - yTop, 2);
            const color = isBullish ? "var(--accent-green)" : "var(--accent-red)";

            // Volume bar
            const volH = (c.v / 150) * 40;
            const volY = svgHeight - volH;

            return (
              <g key={i}>
                {/* Volume at bottom */}
                <rect x={x} y={volY} width={candleWidth} height={volH} fill={color} opacity="0.18" rx="0.5" />
                {/* Wick */}
                <line x1={x + candleWidth / 2} y1={yHigh} x2={x + candleWidth / 2} y2={yLow} stroke={color} strokeWidth="1" />
                {/* Body */}
                <rect x={x} y={yTop} width={candleWidth} height={candleHeight} fill={color} rx="1" />
              </g>
            );
          })}

          {/* Current Live Price Marker */}
          <rect x={chartWidth} y={getY(64520) - 8} width={svgWidth - chartWidth} height="16" fill="var(--accent-green)" />
          <text x={chartWidth + 6} y={getY(64520) + 4} fill="#000" fontSize="9" fontWeight="800" fontFamily="monospace">
            64,520
          </text>
        </svg>
      </div>
    </div>
  );
}
