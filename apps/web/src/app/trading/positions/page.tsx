"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { ArrowLeftIcon, ShieldIcon, AlertTriangleIcon } from "../../../components/Icons";

export interface PositionItem {
  id: string;
  connection_id: string;
  venue_code: string;
  account_ref: string;
  symbol: string;
  side: "LONG" | "SHORT";
  quantity: string;
  avg_entry_price: string;
  current_price: string;
  unrealized_pnl: string;
  pnl_pct: string;
  stop_loss?: string;
  take_profit?: string;
  opened_externally: boolean;
  synced_at: string;
  age_seconds: number;
  view_state: "live" | "stale" | "unknown";
}

const INITIAL_POSITIONS: PositionItem[] = [
  {
    id: "pos-binance-01",
    connection_id: "conn-binance-01",
    venue_code: "BINANCE",
    account_ref: "Binance Main Spot/Margin",
    symbol: "BTC/USDT",
    side: "LONG",
    quantity: "1.25000",
    avg_entry_price: "63,250.00",
    current_price: "64,520.00",
    unrealized_pnl: "+$1,587.50",
    pnl_pct: "+2.01%",
    stop_loss: "62,100.00",
    take_profit: "66,000.00",
    opened_externally: false,
    synced_at: "2026-09-26T14:40:00Z",
    age_seconds: 2.4,
    view_state: "live",
  },
  {
    id: "pos-binance-02",
    connection_id: "conn-binance-01",
    venue_code: "BINANCE",
    account_ref: "Binance Main Spot/Margin",
    symbol: "SOL/USDT",
    side: "SHORT",
    quantity: "45.00",
    avg_entry_price: "122.50",
    current_price: "118.10",
    unrealized_pnl: "+$198.00",
    pnl_pct: "+3.59%",
    opened_externally: true, // Discovered from mobile/web directly (FR-017)
    synced_at: "2026-09-26T14:40:00Z",
    age_seconds: 2.4,
    view_state: "live",
  },
  {
    id: "pos-oanda-01",
    connection_id: "conn-oanda-01",
    venue_code: "OANDA",
    account_ref: "OANDA v20 Primary USD",
    symbol: "EUR/USD",
    side: "LONG",
    quantity: "100,000",
    avg_entry_price: "1.13950",
    current_price: "1.14170",
    unrealized_pnl: "+$220.00",
    pnl_pct: "+0.19%",
    stop_loss: "1.13600",
    take_profit: "1.14800",
    opened_externally: false,
    synced_at: "2026-09-26T14:38:40Z",
    age_seconds: 42.1,
    view_state: "stale", // Synced > 30s ago (FR-019)
  },
];

export default function PositionsPage() {
  const [positions, setPositions] = useState<PositionItem[]>(INITIAL_POSITIONS);
  const [selectedConnection, setSelectedConnection] = useState<string>("ALL");

  const connections = ["ALL", "conn-binance-01", "conn-oanda-01"];

  const filteredPositions = positions.filter(
    (p) => selectedConnection === "ALL" || p.connection_id === selectedConnection
  );

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg-canvas, #090d16)", color: "#f8fafc", fontFamily: "sans-serif" }}>
      {/* Top Header */}
      <header
        style={{
          borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
          background: "rgba(15, 23, 42, 0.75)",
          backdropFilter: "blur(12px)",
          padding: "14px 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <Link
            href="/"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              color: "#94a3b8",
              textDecoration: "none",
              fontSize: "12px",
              fontWeight: 500,
            }}
          >
            <ArrowLeftIcon size={14} />
            <span>Cockpit</span>
          </Link>
          <div style={{ height: "16px", width: "1px", background: "rgba(255,255,255,0.1)" }} />
          <h1 style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "#fff", display: "flex", alignItems: "center", gap: "8px" }}>
            <ShieldIcon size={16} color="#3b82f6" />
            <span>Authoritative Positions & Exposure</span>
          </h1>
        </div>

        {/* Global Connection Filter */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "11px", color: "#64748b" }}>Connection Filter:</span>
          <div style={{ display: "flex", background: "rgba(255,255,255,0.04)", borderRadius: "6px", padding: "2px", border: "1px solid rgba(255,255,255,0.08)" }}>
            {connections.map((c) => (
              <button
                key={c}
                onClick={() => setSelectedConnection(c)}
                style={{
                  background: selectedConnection === c ? "#2563eb" : "transparent",
                  color: selectedConnection === c ? "#fff" : "#94a3b8",
                  border: "none",
                  borderRadius: "4px",
                  padding: "4px 10px",
                  fontSize: "11px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                {c === "ALL" ? "All Venues" : c.replace("conn-", "").toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main style={{ maxWidth: "1280px", margin: "0 auto", padding: "24px" }}>
        {/* Exposure Summary Card */}
        <div
          style={{
            background: "linear-gradient(135deg, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.8))",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            borderRadius: "10px",
            padding: "16px 20px",
            marginBottom: "24px",
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "16px",
          }}
        >
          <div>
            <div style={{ fontSize: "11px", color: "#94a3b8", marginBottom: "4px" }}>Total Open Positions</div>
            <div style={{ fontSize: "20px", fontWeight: 700, color: "#fff" }}>{filteredPositions.length}</div>
          </div>
          <div>
            <div style={{ fontSize: "11px", color: "#94a3b8", marginBottom: "4px" }}>Unrealized P&L</div>
            <div style={{ fontSize: "20px", fontWeight: 700, color: "#10b981" }}>+$2,005.50</div>
          </div>
          <div>
            <div style={{ fontSize: "11px", color: "#94a3b8", marginBottom: "4px" }}>External Positions Discovered</div>
            <div style={{ fontSize: "20px", fontWeight: 700, color: "#f59e0b" }}>
              {filteredPositions.filter((p) => p.opened_externally).length}
            </div>
          </div>
          <div>
            <div style={{ fontSize: "11px", color: "#94a3b8", marginBottom: "4px" }}>Sync Status</div>
            <div style={{ fontSize: "12px", display: "flex", alignItems: "center", gap: "6px", fontWeight: 600 }}>
              <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#10b981" }} />
              <span style={{ color: "#10b981" }}>Active (streaming + snapshot)</span>
            </div>
          </div>
        </div>

        {/* Positions Table */}
        <div
          style={{
            background: "rgba(15, 23, 42, 0.6)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            borderRadius: "10px",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              padding: "12px 16px",
              borderBottom: "1px solid rgba(255, 255, 255, 0.06)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <h2 style={{ margin: 0, fontSize: "13px", fontWeight: 600, color: "#cbd5e1" }}>
              Active Venue Positions (FR-017, FR-020)
            </h2>
            <span style={{ fontSize: "10px", color: "#64748b" }}>Venue is Authoritative Source of Truth</span>
          </div>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px", textAlign: "left" }}>
              <thead>
                <tr style={{ background: "rgba(255, 255, 255, 0.02)", borderBottom: "1px solid rgba(255, 255, 255, 0.06)", color: "#64748b" }}>
                  <th style={{ padding: "10px 14px" }}>Instrument / Venue</th>
                  <th style={{ padding: "10px 14px" }}>Side</th>
                  <th style={{ padding: "10px 14px" }}>Quantity</th>
                  <th style={{ padding: "10px 14px" }}>Entry / Current</th>
                  <th style={{ padding: "10px 14px" }}>Unrealized P&L</th>
                  <th style={{ padding: "10px 14px" }}>Origin</th>
                  <th style={{ padding: "10px 14px" }}>Sync Freshness</th>
                </tr>
              </thead>
              <tbody>
                {filteredPositions.map((pos) => {
                  const isLong = pos.side === "LONG";
                  const isStale = pos.view_state === "stale";

                  return (
                    <tr
                      key={pos.id}
                      style={{
                        borderBottom: "1px solid rgba(255, 255, 255, 0.04)",
                        transition: "background 0.1s ease",
                      }}
                    >
                      <td style={{ padding: "12px 14px" }}>
                        <div style={{ fontWeight: 700, color: "#fff", fontSize: "12px" }}>{pos.symbol}</div>
                        <div style={{ fontSize: "9px", color: "#60a5fa", marginTop: "2px" }}>
                          {pos.venue_code} · {pos.account_ref}
                        </div>
                      </td>
                      <td style={{ padding: "12px 14px" }}>
                        <span
                          style={{
                            padding: "2px 6px",
                            borderRadius: "3px",
                            fontWeight: 700,
                            fontSize: "10px",
                            background: isLong ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)",
                            color: isLong ? "#10b981" : "#ef4444",
                          }}
                        >
                          {pos.side}
                        </span>
                      </td>
                      <td style={{ padding: "12px 14px", fontFamily: "monospace", fontWeight: 600, color: "#e2e8f0" }}>
                        {pos.quantity}
                      </td>
                      <td style={{ padding: "12px 14px", fontFamily: "monospace" }}>
                        <div style={{ color: "#94a3b8" }}>{pos.avg_entry_price}</div>
                        <div style={{ color: "#f8fafc", fontWeight: 600 }}>{pos.current_price}</div>
                      </td>
                      <td style={{ padding: "12px 14px", fontFamily: "monospace" }}>
                        <div style={{ color: "#10b981", fontWeight: 700 }}>{pos.unrealized_pnl}</div>
                        <div style={{ color: "#10b981", fontSize: "10px" }}>{pos.pnl_pct}</div>
                      </td>
                      <td style={{ padding: "12px 14px" }}>
                        {pos.opened_externally ? (
                          <span
                            title="Position was opened directly at venue or outside Atlas"
                            style={{
                              padding: "2px 6px",
                              borderRadius: "3px",
                              fontWeight: 700,
                              fontSize: "9px",
                              background: "rgba(245, 158, 11, 0.15)",
                              color: "#f59e0b",
                              border: "1px solid rgba(245, 158, 11, 0.3)",
                            }}
                          >
                            EXTERNAL (IMPORTED)
                          </span>
                        ) : (
                          <span
                            style={{
                              padding: "2px 6px",
                              borderRadius: "3px",
                              fontWeight: 600,
                              fontSize: "9px",
                              background: "rgba(255, 255, 255, 0.05)",
                              color: "#94a3b8",
                            }}
                          >
                            ATLAS MANDATE
                          </span>
                        )}
                      </td>
                      <td style={{ padding: "12px 14px" }}>
                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "4px",
                            padding: "2px 6px",
                            borderRadius: "3px",
                            fontWeight: 700,
                            fontSize: "10px",
                            background: isStale ? "rgba(239, 68, 68, 0.15)" : "rgba(16, 185, 129, 0.15)",
                            color: isStale ? "#ef4444" : "#10b981",
                            border: `1px solid ${isStale ? "rgba(239, 68, 68, 0.3)" : "rgba(16, 185, 129, 0.3)"}`,
                          }}
                        >
                          <span style={{ width: "5px", height: "5px", borderRadius: "50%", background: isStale ? "#ef4444" : "#10b981" }} />
                          {isStale ? `STALE (${pos.age_seconds}s ago)` : `LIVE (${pos.age_seconds}s ago)`}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}
