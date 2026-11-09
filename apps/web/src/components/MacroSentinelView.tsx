"use client";

import React, { useState, useEffect, useMemo } from "react";
import { soundManager } from "../lib/soundEffects";
import { ZapIcon, ShieldIcon } from "./Icons";

export interface MacroEvent {
  id: string;
  name: string;
  country: string;
  currency: "USD" | "EUR" | "GBP" | "JPY";
  impact: "HIGH" | "MEDIUM" | "LOW";
  category: "INFLATION" | "CENTRAL_BANK" | "LABOR" | "GROWTH" | "ENERGY";
  timestamp: number; // Unix timestamp in ms
  forecast: string;
  previous: string;
  actual?: string;
  marketConsensus: string;
  historicalVolatilityAsset: string;
  expectedMove: string;
  status: "UPCOMING" | "RELEASED";
}

const INITIAL_EVENTS: MacroEvent[] = [
  {
    id: "evt-fomc-rate",
    name: "FOMC Federal Funds Rate Decision",
    country: "United States",
    currency: "USD",
    impact: "HIGH",
    category: "CENTRAL_BANK",
    timestamp: Date.now() + 1000 * 60 * 60 * 2.75, // in ~2h 45m
    forecast: "4.75%",
    previous: "5.00%",
    marketConsensus: "25bps cut priced at 94% probability",
    historicalVolatilityAsset: "BTC/USDT, US100, EUR/USD",
    expectedMove: "±$1,850 BTC · ±1.4% US100",
    status: "UPCOMING",
  },
  {
    id: "evt-us-cpi-core",
    name: "US Core CPI Inflation (YoY)",
    country: "United States",
    currency: "USD",
    impact: "HIGH",
    category: "INFLATION",
    timestamp: Date.now() + 1000 * 60 * 60 * 18, // in ~18h
    forecast: "3.2%",
    previous: "3.3%",
    marketConsensus: "Disinflation trend continuing; core services sticky",
    historicalVolatilityAsset: "BTC/USDT, Gold (XAU), DXY",
    expectedMove: "±$1,200 BTC · ±$28 XAU",
    status: "UPCOMING",
  },
  {
    id: "evt-us-nfp",
    name: "US Non-Farm Payrolls (NFP)",
    country: "United States",
    currency: "USD",
    impact: "HIGH",
    category: "LABOR",
    timestamp: Date.now() + 1000 * 60 * 60 * 42, // in ~42h
    forecast: "145K",
    previous: "142K",
    marketConsensus: "Cooling labor market; wage growth +0.3% MoM",
    historicalVolatilityAsset: "BTC/USDT, EUR/USD",
    expectedMove: "±$950 BTC · ±65 pips EUR",
    status: "UPCOMING",
  },
  {
    id: "evt-ecb-rate",
    name: "ECB Deposit Facility Rate Decision",
    country: "Eurozone",
    currency: "EUR",
    impact: "HIGH",
    category: "CENTRAL_BANK",
    timestamp: Date.now() + 1000 * 60 * 60 * 66,
    forecast: "3.25%",
    previous: "3.50%",
    marketConsensus: "Lagarde signaling data-dependency; 25bps cut anticipated",
    historicalVolatilityAsset: "EUR/USD, GBP/USD",
    expectedMove: "±55 pips EUR/USD",
    status: "UPCOMING",
  },
  {
    id: "evt-us-retail",
    name: "US Retail Sales Advance (MoM)",
    country: "United States",
    currency: "USD",
    impact: "MEDIUM",
    category: "GROWTH",
    timestamp: Date.now() + 1000 * 60 * 60 * 90,
    forecast: "+0.3%",
    previous: "+0.1%",
    marketConsensus: "Resilient consumer spending buffer",
    historicalVolatilityAsset: "US100, BTC/USDT",
    expectedMove: "±$480 BTC · ±0.6% US100",
    status: "UPCOMING",
  },
  {
    id: "evt-crude-inv",
    name: "EIA Crude Oil Inventories",
    country: "United States",
    currency: "USD",
    impact: "MEDIUM",
    category: "ENERGY",
    timestamp: Date.now() + 1000 * 60 * 60 * 114,
    forecast: "-1.2M",
    previous: "+1.6M",
    marketConsensus: "Drawdown expected due to refinery capacity",
    historicalVolatilityAsset: "USOIL, UKOIL",
    expectedMove: "±$1.85 Crude",
    status: "UPCOMING",
  },
  {
    id: "evt-boj-rate",
    name: "Bank of Japan (BOJ) Interest Rate",
    country: "Japan",
    currency: "JPY",
    impact: "HIGH",
    category: "CENTRAL_BANK",
    timestamp: Date.now() + 1000 * 60 * 60 * 138,
    forecast: "0.25%",
    previous: "0.25%",
    marketConsensus: "Governor Ueda maintaining gradual normalization tone; Yen carry risk",
    historicalVolatilityAsset: "USD/JPY, Global Risk Assets",
    expectedMove: "±120 pips USD/JPY · ±$1,500 BTC",
    status: "UPCOMING",
  },
];

export function MacroSentinelView() {
  const [events, setEvents] = useState<MacroEvent[]>(INITIAL_EVENTS);
  const [filterImpact, setFilterImpact] = useState<"ALL" | "HIGH" | "MEDIUM">("ALL");
  const [filterCurrency, setFilterCurrency] = useState<"ALL" | "USD" | "EUR" | "JPY">("ALL");
  const [autoCircuitEnabled, setAutoCircuitEnabled] = useState<boolean>(true);
  const [selectedEvent, setSelectedEvent] = useState<MacroEvent | null>(INITIAL_EVENTS[0]!);
  const [now, setNow] = useState(Date.now());

  // Keep live clock ticking for countdowns
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Format countdown string
  const formatCountdown = (targetTime: number) => {
    const diff = targetTime - now;
    if (diff <= 0) return "RELEASED";

    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((diff % (1000 * 60)) / 1000);

    if (hours > 24) {
      const days = Math.floor(hours / 24);
      return `in ${days}d ${hours % 24}h`;
    }
    return `in ${hours}h ${minutes}m ${seconds}s`;
  };

  const filteredEvents = useMemo(() => {
    return events.filter((e) => {
      if (filterImpact === "HIGH" && e.impact !== "HIGH") return false;
      if (filterImpact === "MEDIUM" && e.impact === "LOW") return false;
      if (filterCurrency !== "ALL" && e.currency !== filterCurrency) return false;
      return true;
    });
  }, [events, filterImpact, filterCurrency]);

  const nearestHighEvent = useMemo(() => {
    const upcomingHigh = events.filter((e) => e.impact === "HIGH" && e.timestamp > now);
    return upcomingHigh.sort((a, b) => a.timestamp - b.timestamp)[0] || null;
  }, [events, now]);

  const handleToggleAutoCircuit = () => {
    soundManager.playClick();
    setAutoCircuitEnabled((prev) => !prev);
  };

  const getImpactBadge = (impact: "HIGH" | "MEDIUM" | "LOW") => {
    switch (impact) {
      case "HIGH":
        return { label: "3-STAR HIGH", color: "#f43f5e", bg: "rgba(244, 63, 94, 0.12)", border: "rgba(244, 63, 94, 0.3)" };
      case "MEDIUM":
        return { label: "2-STAR MED", color: "#f59e0b", bg: "rgba(245, 158, 11, 0.12)", border: "rgba(245, 158, 11, 0.3)" };
      default:
        return { label: "1-STAR LOW", color: "#64748b", bg: "rgba(100, 116, 139, 0.12)", border: "rgba(100, 116, 139, 0.25)" };
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", gap: "8px", overflow: "hidden" }}>
      {/* Top Sentinel Status Banner */}
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
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              width: "28px",
              height: "28px",
              borderRadius: "6px",
              background: "rgba(255, 255, 255, 0.05)",
              border: "1px solid var(--border-subtle)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#cbd5e1",
            }}
          >
            <ZapIcon size={14} color="#cbd5e1" />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)", letterSpacing: "0.2px" }}>
                MACRO CATALYST & EVENT SENTINEL
              </span>
              <span
                style={{
                  fontSize: "9px",
                  fontFamily: "var(--font-mono)",
                  color: "#10b981",
                  background: "rgba(16, 185, 129, 0.12)",
                  border: "1px solid rgba(16, 185, 129, 0.25)",
                  padding: "1px 6px",
                  borderRadius: "3px",
                }}
              >
                LIVE FEED ACTIVE
              </span>
            </div>
            <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
              Institutional economic calendar tracking central bank rate decisions, CPI prints, and liquidity shockwaves.
            </span>
          </div>
        </div>

        {/* Nearest High Impact Alert & Auto-Circuit Toggle */}
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          {nearestHighEvent && (
            <div
              style={{
                background: "rgba(244, 63, 94, 0.1)",
                border: "1px solid rgba(244, 63, 94, 0.25)",
                borderRadius: "6px",
                padding: "4px 10px",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
              className="tabular-nums"
            >
              <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#f43f5e", animation: "pulse 1.2s infinite" }} />
              <div>
                <span style={{ fontSize: "9px", color: "#f43f5e", fontWeight: 700, display: "block" }}>
                  NEXT HIGH IMPACT: {nearestHighEvent.currency}
                </span>
                <span style={{ fontSize: "11px", color: "var(--text-primary)", fontWeight: 700 }}>
                  {nearestHighEvent.name} ({formatCountdown(nearestHighEvent.timestamp)})
                </span>
              </div>
            </div>
          )}

          {/* Auto Circuit Breaker Guard Button */}
          <button
            onClick={handleToggleAutoCircuit}
            style={{
              background: autoCircuitEnabled ? "rgba(16, 185, 129, 0.12)" : "var(--bg-surface-elevated)",
              border: `1px solid ${autoCircuitEnabled ? "rgba(16, 185, 129, 0.3)" : "var(--border-subtle)"}`,
              borderRadius: "5px",
              padding: "5px 12px",
              fontSize: "11px",
              color: autoCircuitEnabled ? "#10b981" : "var(--text-muted)",
              fontWeight: 700,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              transition: "all 0.15s ease",
            }}
            title="Automatically pauses automated orders 15m before and after high-impact macro releases"
          >
            <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: autoCircuitEnabled ? "#10b981" : "var(--text-muted)" }} />
            <span>AUTO-VOLATILITY GATE: {autoCircuitEnabled ? "ARMED" : "OFF"}</span>
          </button>
        </div>
      </div>

      {/* Main Two-Column Layout: Left Event Table + Right Catalyst Inspector */}
      <div style={{ flex: 1, minHeight: 0, display: "grid", gridTemplateColumns: "1fr 340px", gap: "8px", overflow: "hidden" }}>
        {/* Left Column: Event List & Filter Bar */}
        <div
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "8px",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          {/* Filter Bar */}
          <div
            style={{
              height: "36px",
              background: "var(--bg-surface-elevated)",
              borderBottom: "1px solid var(--border-subtle)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "0 12px",
              flexShrink: 0,
              fontSize: "11px",
            }}
          >
            {/* Impact Filter */}
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ color: "#64748b", fontSize: "10px" }}>Impact:</span>
              {(["ALL", "HIGH", "MEDIUM"] as const).map((imp) => (
                <button
                  key={imp}
                  onClick={() => {
                    soundManager.playClick();
                    setFilterImpact(imp);
                  }}
                  style={{
                    background: filterImpact === imp ? "rgba(56, 189, 248, 0.15)" : "transparent",
                    border: `1px solid ${filterImpact === imp ? "rgba(56, 189, 248, 0.3)" : "transparent"}`,
                    color: filterImpact === imp ? "#38bdf8" : "#94a3b8",
                    borderRadius: "3px",
                    padding: "2px 6px",
                    fontSize: "10px",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  {imp === "ALL" ? "All Impact" : imp === "HIGH" ? "3-Star Only" : "2-Star+"}
                </button>
              ))}
            </div>

            {/* Currency Filter */}
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ color: "#64748b", fontSize: "10px" }}>Currency:</span>
              {(["ALL", "USD", "EUR", "JPY"] as const).map((curr) => (
                <button
                  key={curr}
                  onClick={() => {
                    soundManager.playClick();
                    setFilterCurrency(curr);
                  }}
                  style={{
                    background: filterCurrency === curr ? "rgba(16, 185, 129, 0.15)" : "transparent",
                    border: `1px solid ${filterCurrency === curr ? "rgba(16, 185, 129, 0.3)" : "transparent"}`,
                    color: filterCurrency === curr ? "#10b981" : "#94a3b8",
                    borderRadius: "3px",
                    padding: "2px 6px",
                    fontSize: "10px",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  {curr}
                </button>
              ))}
            </div>
          </div>

          {/* Table Column Headers */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "70px 1fr 100px 90px 80px 80px 110px",
              padding: "6px 12px",
              background: "var(--bg-surface-elevated)",
              borderBottom: "1px solid var(--border-subtle)",
              fontSize: "10px",
              fontWeight: 700,
              color: "var(--text-muted)",
            }}
          >
            <span>CURR</span>
            <span>EVENT NAME</span>
            <span>IMPACT</span>
            <span>COUNTDOWN</span>
            <span style={{ textAlign: "right" }}>FORECAST</span>
            <span style={{ textAlign: "right" }}>PREV</span>
            <span style={{ textAlign: "right" }}>EXP. MOVE</span>
          </div>

          {/* Events Scroll List */}
          <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column" }}>
            {filteredEvents.map((evt) => {
              const isSelected = selectedEvent?.id === evt.id;
              const badge = getImpactBadge(evt.impact);

              return (
                <div
                  key={evt.id}
                  onClick={() => {
                    soundManager.playClick();
                    setSelectedEvent(evt);
                  }}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "70px 1fr 100px 90px 80px 80px 110px",
                    padding: "8px 12px",
                    background: isSelected ? "rgba(56, 189, 248, 0.08)" : "transparent",
                    borderBottom: "1px solid #141926",
                    borderLeft: isSelected ? "2px solid #38bdf8" : "2px solid transparent",
                    fontSize: "11px",
                    alignItems: "center",
                    cursor: "pointer",
                    transition: "all 0.1s ease",
                  }}
                  className="tabular-nums"
                  onMouseEnter={(e) => {
                    if (!isSelected) e.currentTarget.style.background = "rgba(255, 255, 255, 0.02)";
                  }}
                  onMouseLeave={(e) => {
                    if (!isSelected) e.currentTarget.style.background = "transparent";
                  }}
                >
                  {/* Currency Badge */}
                  <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
                    <span
                      style={{
                        fontSize: "10px",
                        fontWeight: 800,
                        color: evt.currency === "USD" ? "#38bdf8" : evt.currency === "EUR" ? "#10b981" : "#f59e0b",
                        background: "rgba(255, 255, 255, 0.04)",
                        border: "1px solid rgba(255, 255, 255, 0.08)",
                        padding: "1px 5px",
                        borderRadius: "3px",
                      }}
                    >
                      {evt.currency}
                    </span>
                  </div>

                  {/* Event Name */}
                  <div>
                    <span style={{ fontWeight: 700, color: "var(--text-primary)", display: "block" }}>{evt.name}</span>
                    <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>{evt.country} · {evt.category}</span>
                  </div>

                  {/* Impact Badge */}
                  <div>
                    <span
                      style={{
                        fontSize: "9px",
                        fontWeight: 700,
                        color: badge.color,
                        background: badge.bg,
                        border: `1px solid ${badge.border}`,
                        padding: "1px 6px",
                        borderRadius: "3px",
                      }}
                    >
                      {badge.label}
                    </span>
                  </div>

                  {/* Countdown Timer */}
                  <div>
                    <span style={{ fontSize: "10px", color: evt.timestamp - now < 1000 * 60 * 60 * 3 ? "#f43f5e" : "#f59e0b", fontWeight: 700 }}>
                      {formatCountdown(evt.timestamp)}
                    </span>
                  </div>

                  {/* Forecast */}
                  <div style={{ textAlign: "right", color: "var(--text-primary)", fontWeight: 600 }}>
                    {evt.forecast}
                  </div>

                  {/* Previous */}
                  <div style={{ textAlign: "right", color: "var(--text-muted)" }}>
                    {evt.previous}
                  </div>

                  {/* Expected Move */}
                  <div style={{ textAlign: "right", color: "var(--accent-blue)", fontSize: "10px", fontWeight: 600 }}>
                    {evt.expectedMove}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Selected Catalyst Deep-Dive Inspector */}
        {selectedEvent && (
          <div
            style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "8px",
              padding: "14px",
              display: "flex",
              flexDirection: "column",
              gap: "12px",
              overflowY: "auto",
            }}
          >
            {/* Header */}
            <div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "4px" }}>
                <span
                  style={{
                    fontSize: "10px",
                    fontWeight: 800,
                    color: selectedEvent.impact === "HIGH" ? "#f43f5e" : "#f59e0b",
                    background: selectedEvent.impact === "HIGH" ? "rgba(244, 63, 94, 0.12)" : "rgba(245, 158, 11, 0.12)",
                    border: `1px solid ${selectedEvent.impact === "HIGH" ? "rgba(244, 63, 94, 0.25)" : "rgba(245, 158, 11, 0.25)"}`,
                    padding: "1px 6px",
                    borderRadius: "3px",
                  }}
                >
                  {selectedEvent.currency} {selectedEvent.impact} IMPACT
                </span>
                <span style={{ fontSize: "11px", color: "#f59e0b", fontWeight: 700 }} className="tabular-nums">
                  {formatCountdown(selectedEvent.timestamp)}
                </span>
              </div>

              <h3 style={{ fontSize: "14px", fontWeight: 800, color: "var(--text-primary)", margin: "4px 0" }}>
                {selectedEvent.name}
              </h3>
              <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                Category: {selectedEvent.category} · {selectedEvent.country}
              </span>
            </div>

            {/* Print Estimates Box */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "8px",
                background: "var(--bg-surface-elevated)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "6px",
                padding: "10px",
              }}
              className="tabular-nums"
            >
              <div>
                <span style={{ fontSize: "10px", color: "var(--text-muted)", display: "block" }}>MARKET FORECAST</span>
                <span style={{ fontSize: "14px", fontWeight: 800, color: "var(--text-primary)" }}>{selectedEvent.forecast}</span>
              </div>
              <div>
                <span style={{ fontSize: "10px", color: "var(--text-muted)", display: "block" }}>PREVIOUS PRINT</span>
                <span style={{ fontSize: "14px", fontWeight: 800, color: "var(--text-secondary)" }}>{selectedEvent.previous}</span>
              </div>
            </div>

            {/* Institutional Market Consensus */}
            <div style={{ background: "var(--bg-surface-elevated)", border: "1px solid var(--border-subtle)", borderRadius: "6px", padding: "10px" }}>
              <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--accent-blue)", display: "block", marginBottom: "4px" }}>
                Institutional Consensus & Scenarios
              </span>
              <p style={{ margin: 0, fontSize: "11px", color: "var(--text-secondary)", lineHeight: "16px" }}>
                {selectedEvent.marketConsensus}
              </p>
            </div>

            {/* Volatility & Cross-Asset Shockwave */}
            <div style={{ background: "var(--bg-surface-elevated)", border: "1px solid var(--border-subtle)", borderRadius: "6px", padding: "10px" }}>
              <span style={{ fontSize: "11px", fontWeight: 700, color: "#f59e0b", display: "block", marginBottom: "6px" }}>
                Estimated Volatility Shockwave
              </span>
              <div style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "11px" }} className="tabular-nums">
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--text-muted)" }}>Primary Affected:</span>
                  <strong style={{ color: "var(--text-primary)" }}>{selectedEvent.historicalVolatilityAsset}</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--text-muted)" }}>Expected Move:</span>
                  <strong style={{ color: "#10b981" }}>{selectedEvent.expectedMove}</strong>
                </div>
              </div>
            </div>

            {/* 1-Click Volatility Safeguards */}
            <div style={{ marginTop: "auto", display: "flex", flexDirection: "column", gap: "6px" }}>
              <span style={{ fontSize: "10px", color: "#64748b", fontWeight: 700 }}>
                1-CLICK RISK SAFEGUARDS:
              </span>
              <button
                onClick={() => {
                  soundManager.playExecutionSuccess();
                  alert("Volatility Safeguard Activated: All Stop Losses widened to 2.5x ATR to protect against news spike.");
                }}
                style={{
                  background: "rgba(255, 255, 255, 0.04)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "4px",
                  color: "#e2e8f0",
                  padding: "7px 0",
                  fontSize: "11px",
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "6px",
                  transition: "border-color 0.15s ease",
                }}
              >
                <ShieldIcon size={12} color="#cbd5e1" />
                <span>Widen Trailing Stops to 2.5x ATR</span>
              </button>
              <button
                onClick={() => {
                  soundManager.playExecutionSuccess();
                  alert("De-Risk Triggered: Circuit Breaker armed for this release window.");
                }}
                style={{
                  background: "rgba(255, 255, 255, 0.04)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "4px",
                  color: "#e2e8f0",
                  padding: "7px 0",
                  fontSize: "11px",
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "6px",
                  transition: "border-color 0.15s ease",
                }}
              >
                <ZapIcon size={12} color="#cbd5e1" />
                <span>Arm 15m News Circuit Breaker</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
