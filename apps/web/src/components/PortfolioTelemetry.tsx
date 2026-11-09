"use client";

import React, { useState } from "react";
import { ShieldIcon, LayersIcon, InboxIcon, CloseIcon } from "./Icons";

export interface ActivePosition {
  id: string;
  symbol: string;
  side: "LONG" | "SHORT";
  sizeStr: string;
  entryPrice: number;
  currentPrice: number;
  pnlUsd: number;
  pnlPct: number;
  tpPrice: number;
  slPrice: number;
  breakEven?: boolean;
  trailingStop?: boolean;
}

export interface OpenOrder {
  id: string;
  symbol: string;
  side: "BUY" | "SELL" | string;
  price: number;
  sizeStr: string;
  status: string;
  type: string;
  time: string;
}

export interface PortfolioTelemetryProps {
  balance?: number;
  equity?: number;
  positions?: ActivePosition[];
  openOrders?: OpenOrder[];
  onClosePosition?: (id: string) => void;
  onPartialClose?: (id: string, ratio: number) => void;
  onUpdateTpSl?: (id: string, tp: number, sl: number) => void;
  onSetBreakEven?: (id: string) => void;
  onToggleTrailingStop?: (id: string) => void;
  onCancelOrder?: (id: string) => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export function PortfolioTelemetry({
  balance = 125480,
  equity = 125480,
  positions = [],
  openOrders = [],
  onClosePosition = () => {},
  onPartialClose = () => {},
  onUpdateTpSl = () => {},
  onSetBreakEven = () => {},
  onToggleTrailingStop = () => {},
  onCancelOrder = () => {},
  isCollapsed = false,
  onToggleCollapse,
}: PortfolioTelemetryProps) {
  const [deskTab, setDeskTab] = useState<"POSITIONS" | "ORDERS">("POSITIONS");
  const [editingPos, setEditingPos] = useState<ActivePosition | null>(null);
  const [editTp, setEditTp] = useState("");
  const [editSl, setEditSl] = useState("");

  const safePositions = positions || [];
  const totalUnrealizedPnl = safePositions.reduce((acc, p) => acc + (p?.pnlUsd || 0), 0);
  const totalPnlPct = balance > 0 ? (totalUnrealizedPnl / balance) * 100 : 0;
  const isPnlPositive = totalUnrealizedPnl >= 0;

  const handleOpenEdit = (p: ActivePosition) => {
    setEditingPos(p);
    setEditTp(p.tpPrice.toString());
    setEditSl(p.slPrice.toString());
  };

  const handleSaveTpSl = () => {
    if (editingPos) {
      const tp = parseFloat(editTp);
      const sl = parseFloat(editSl);
      if (!isNaN(tp) && !isNaN(sl)) {
        onUpdateTpSl(editingPos.id, tp, sl);
      }
      setEditingPos(null);
    }
  };

  if (isCollapsed) {
    return (
      <div
        className="panel"
        style={{
          width: "36px",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          padding: "8px 0",
          gap: "12px",
          background: "var(--bg-surface)",
          borderLeft: "1px solid var(--border-subtle)",
          cursor: "pointer",
        }}
        onClick={onToggleCollapse}
        title="Expand Portfolio Telemetry (])"
      >
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggleCollapse?.();
          }}
          className="btn-sober"
          style={{ width: "24px", height: "24px", padding: 0, display: "flex", alignItems: "center", justifyContent: "center" }}
          title="Expand Portfolio Telemetry (])"
        >
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>

        <span className="live-dot-green" />

        <div
          style={{
            writingMode: "vertical-rl",
            transform: "rotate(180deg)",
            fontSize: "10px",
            fontWeight: 700,
            letterSpacing: "0.08em",
            color: "var(--text-secondary)",
            whiteSpace: "nowrap",
          }}
        >
          PORTFOLIO
        </div>

        <div
          style={{
            marginTop: "auto",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "4px",
          }}
        >
          <span
            style={{
              fontSize: "9px",
              fontFamily: "var(--font-mono)",
              fontWeight: 700,
              background: safePositions.length > 0 ? "var(--accent-green-subtle)" : "var(--bg-surface-elevated)",
              color: safePositions.length > 0 ? "var(--accent-green)" : "var(--text-muted)",
              padding: "2px 5px",
              borderRadius: "3px",
              border: `1px solid ${safePositions.length > 0 ? "var(--accent-green-border)" : "var(--border-subtle)"}`,
            }}
          >
            {safePositions.length}P
          </span>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px", height: "100%", overflow: "hidden" }}>
      {/* 1. Account Equity Card */}
      <div className="panel" style={{ display: "flex", flexDirection: "column", flexShrink: 0 }}>
        <div className="panel-header">
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span className="live-dot-green" />
            <span style={{ color: "var(--text-primary)", fontWeight: 700, letterSpacing: "0.04em" }}>
              PORTFOLIO ACCOUNT
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span
              style={{
                fontSize: "9px",
                fontFamily: "var(--font-mono)",
                color: "var(--accent-green)",
                fontWeight: 600,
                background: "var(--accent-green-subtle)",
                border: "1px solid var(--accent-green-border)",
                padding: "1px 5px",
                borderRadius: "3px",
              }}
            >
              CONNECTED
            </span>
            {onToggleCollapse && (
              <button
                onClick={onToggleCollapse}
                className="btn-sober"
                style={{ width: "20px", height: "20px", padding: 0, display: "flex", alignItems: "center", justifyContent: "center" }}
                title="Collapse Portfolio Telemetry (])"
              >
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <polyline points="9 18 15 12 9 6" />
                </svg>
              </button>
            )}
          </div>
        </div>

        <div style={{ padding: "10px 12px", display: "flex", flexDirection: "column", gap: "6px" }}>
          {/* Big Balance & PnL */}
          <div>
            <div style={{ fontSize: "17px", fontWeight: 700, color: "var(--text-primary)" }} className="tabular-nums">
              ${equity.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "10.5px", marginTop: "2px" }} className="tabular-nums">
              <span style={{ color: "var(--text-secondary)" }}>
                Bal: ${balance.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
              </span>
              <span style={{ color: isPnlPositive ? "var(--accent-green)" : "var(--accent-red)", fontWeight: 600 }}>
                {isPnlPositive ? "+" : ""}${totalUnrealizedPnl.toFixed(2)} ({isPnlPositive ? "+" : ""}{totalPnlPct.toFixed(2)}%)
              </span>
            </div>
          </div>

          {/* Daily Drawdown Meter */}
          <div style={{ marginTop: "2px", background: "var(--bg-surface-elevated)", padding: "6px 8px", borderRadius: "4px", border: "1px solid var(--border-subtle)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "9px" }}>
              <span style={{ color: "var(--text-secondary)", fontWeight: 500 }}>Daily Drawdown Guard</span>
              <span className="tabular-nums" style={{ color: "var(--accent-green)", fontWeight: 600 }}>
                0.8% / 4.0% Max
              </span>
            </div>
            <div style={{ height: "4px", background: "var(--bg-surface)", borderRadius: "2px", marginTop: "4px", overflow: "hidden" }}>
              <div style={{ width: "20%", height: "100%", background: "var(--accent-green)", borderRadius: "2px" }} />
            </div>
          </div>
        </div>
      </div>

      {/* 2. Active Positions & Open Orders Dual Desk */}
      <div className="panel" style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <div className="panel-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "4px 8px" }}>
          <div style={{ display: "flex", gap: "2px" }}>
            <button
              onClick={() => setDeskTab("POSITIONS")}
              style={{
                background: deskTab === "POSITIONS" ? "var(--bg-surface-elevated)" : "transparent",
                color: deskTab === "POSITIONS" ? "var(--text-primary)" : "var(--text-muted)",
                border: deskTab === "POSITIONS" ? "1px solid var(--border-medium)" : "1px solid transparent",
                borderRadius: "3px",
                padding: "2px 8px",
                fontSize: "10px",
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              POSITIONS ({positions.length})
            </button>
            <button
              onClick={() => setDeskTab("ORDERS")}
              style={{
                background: deskTab === "ORDERS" ? "var(--bg-surface-elevated)" : "transparent",
                color: deskTab === "ORDERS" ? "var(--accent-blue)" : "var(--text-muted)",
                border: deskTab === "ORDERS" ? "1px solid var(--accent-blue)" : "1px solid transparent",
                borderRadius: "3px",
                padding: "2px 8px",
                fontSize: "10px",
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              ORDERS ({openOrders.length})
            </button>
          </div>
          <span style={{ fontSize: "9px", fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>
            {deskTab === "POSITIONS" ? `${positions.length} OPEN` : `${openOrders.length} PENDING`}
          </span>
        </div>

        <div style={{ flex: 1, overflowY: "auto", padding: "6px", display: "flex", flexDirection: "column", gap: "6px" }}>
          {deskTab === "ORDERS" ? (
            openOrders.length === 0 ? (
              <div
                style={{
                  flex: 1,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  padding: "36px 16px",
                  textAlign: "center",
                  background: "rgba(255, 255, 255, 0.015)",
                  borderRadius: "6px",
                  border: "1px dashed var(--border-subtle)",
                  margin: "8px 4px",
                }}
              >
                <div
                  style={{
                    width: "36px",
                    height: "36px",
                    borderRadius: "50%",
                    background: "var(--bg-surface-elevated)",
                    border: "1px solid var(--border-medium)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    marginBottom: "10px",
                  }}
                >
                  <InboxIcon size={16} color="var(--text-muted)" />
                </div>
                <div style={{ fontSize: "11.5px", fontWeight: 600, color: "var(--text-primary)", marginBottom: "3px" }}>
                  No Pending Orders
                </div>
                <div style={{ fontSize: "10px", color: "var(--text-muted)", lineHeight: 1.4, maxWidth: "200px" }}>
                  Active broker exchange limit, stop, and take-profit orders will stream here.
                </div>
              </div>
            ) : (
              openOrders.map((ord) => (
                <div
                  key={ord.id}
                  style={{
                    background: "var(--bg-surface-elevated)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "5px",
                    padding: "8px 10px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "4px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
                      <span
                        style={{
                          fontSize: "8.5px",
                          fontWeight: 700,
                          background: ord.side === "BUY" ? "rgba(16, 185, 129, 0.1)" : "rgba(244, 63, 94, 0.1)",
                          color: ord.side === "BUY" ? "var(--accent-green)" : "var(--accent-red)",
                          border: `1px solid ${ord.side === "BUY" ? "var(--accent-green-border)" : "var(--accent-red-border)"}`,
                          padding: "1px 5px",
                          borderRadius: "3px",
                        }}
                      >
                        {ord.side}
                      </span>
                      <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-primary)" }}>{ord.symbol}</span>
                      <span style={{ fontSize: "8.5px", color: "var(--text-muted)" }}>{ord.type}</span>
                    </div>

                    <button
                      onClick={() => onCancelOrder(ord.id)}
                      style={{
                        background: "rgba(244, 63, 94, 0.08)",
                        border: "1px solid rgba(244, 63, 94, 0.25)",
                        color: "#f43f5e",
                        borderRadius: "3px",
                        padding: "1px 6px",
                        fontSize: "9px",
                        fontWeight: 600,
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}
                    >
                      Cancel
                    </button>
                  </div>

                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "9.5px", color: "var(--text-muted)" }}>
                    <span>Size: <strong style={{ color: "var(--text-primary)" }}>{ord.sizeStr}</strong></span>
                    <span>Price: <strong style={{ color: "var(--text-primary)" }}>${ord.price.toLocaleString()}</strong></span>
                  </div>

                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "8.5px", color: "var(--text-muted)" }}>
                    <span>Order #{ord.id}</span>
                    <span>{ord.time}</span>
                  </div>
                </div>
              ))
            )
          ) : (
            positions.length === 0 ? (
              <div
                style={{
                  flex: 1,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  padding: "36px 16px",
                  textAlign: "center",
                  background: "rgba(255, 255, 255, 0.015)",
                  borderRadius: "6px",
                  border: "1px dashed var(--border-subtle)",
                  margin: "8px 4px",
                }}
              >
                <div
                  style={{
                    width: "36px",
                    height: "36px",
                    borderRadius: "50%",
                    background: "var(--bg-surface-elevated)",
                    border: "1px solid var(--border-medium)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    marginBottom: "10px",
                  }}
                >
                  <LayersIcon size={16} color="var(--text-muted)" />
                </div>
                <div style={{ fontSize: "11.5px", fontWeight: 600, color: "var(--text-primary)", marginBottom: "3px" }}>
                  No Open Positions
                </div>
                <div style={{ fontSize: "10px", color: "var(--text-muted)", lineHeight: 1.4, maxWidth: "200px" }}>
                  Use BUY or SELL in Market Watch to open live positions with automated trailing stops.
                </div>
              </div>
            ) : (
              positions.map((p) => {
                const isPosPnl = p.pnlUsd >= 0;
                return (
                  <div
                    key={p.id}
                    style={{
                      background: "var(--bg-surface-elevated)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "5px",
                      padding: "9px 10px",
                      position: "relative",
                      display: "flex",
                      flexDirection: "column",
                      gap: "4px",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
                        <span
                          style={{
                            fontSize: "8.5px",
                            fontWeight: 700,
                            background: p.side === "LONG" ? "rgba(16, 185, 129, 0.1)" : "rgba(244, 63, 94, 0.1)",
                            color: p.side === "LONG" ? "var(--accent-green)" : "var(--accent-red)",
                            border: `1px solid ${p.side === "LONG" ? "var(--accent-green-border)" : "var(--accent-red-border)"}`,
                            padding: "1px 5px",
                            borderRadius: "3px",
                          }}
                        >
                          {p.side}
                        </span>
                        <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-primary)" }}>{p.symbol}</span>
                        {p.breakEven && (
                          <span
                            style={{
                              fontSize: "7.5px",
                              fontWeight: 700,
                              background: "rgba(56, 189, 248, 0.12)",
                              border: "1px solid rgba(56, 189, 248, 0.3)",
                              color: "#38bdf8",
                              padding: "1px 4px",
                              borderRadius: "2px",
                            }}
                          >
                            BE
                          </span>
                        )}
                        {p.trailingStop && (
                          <span
                            style={{
                              fontSize: "7.5px",
                              fontWeight: 700,
                              background: "rgba(16, 185, 129, 0.12)",
                              border: "1px solid var(--accent-green-border)",
                              color: "var(--accent-green)",
                              padding: "1px 4px",
                              borderRadius: "2px",
                            }}
                          >
                            TRAIL
                          </span>
                        )}
                      </div>

                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <span
                          className="tabular-nums"
                          style={{
                            fontSize: "11px",
                            fontWeight: 700,
                            color: isPosPnl ? "var(--accent-green)" : "var(--accent-red)",
                          }}
                        >
                          {isPosPnl ? "+" : ""}${p.pnlUsd.toFixed(2)}
                        </span>
                        <button
                          onClick={() => onClosePosition(p.id)}
                          title="Close Position"
                          style={{
                            background: "rgba(244, 63, 94, 0.08)",
                            border: "1px solid rgba(244, 63, 94, 0.25)",
                            color: "#f43f5e",
                            borderRadius: "3px",
                            cursor: "pointer",
                            fontSize: "9.5px",
                            fontWeight: 600,
                            padding: "1px 6px",
                            transition: "all 0.15s ease",
                          }}
                        >
                          Close
                        </button>
                      </div>
                    </div>

                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "9.5px", color: "var(--text-muted)", marginTop: "2px" }} className="tabular-nums">
                      <span>{p.sizeStr}</span>
                      <span>Entry: <strong style={{ color: "var(--text-secondary)" }}>${p.entryPrice.toLocaleString()}</strong></span>
                      <span>Mark: <strong style={{ color: "var(--text-primary)" }}>${p.currentPrice.toLocaleString()}</strong></span>
                    </div>

                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "9px", color: "var(--text-muted)", marginTop: "1px" }} className="tabular-nums">
                      <span>TP: <strong style={{ color: "var(--accent-green)" }}>${p.tpPrice.toLocaleString()}</strong></span>
                      <span>SL: <strong style={{ color: "var(--accent-red)" }}>${p.slPrice.toLocaleString()}</strong></span>
                    </div>

                    {/* Quick Action Buttons */}
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: "4px", marginTop: "5px", borderTop: "1px solid var(--border-subtle)", paddingTop: "5px" }}>
                      <button
                        onClick={() => onPartialClose(p.id, 0.5)}
                        style={{
                          background: "var(--bg-surface)",
                          border: "1px solid var(--border-subtle)",
                          color: "var(--text-secondary)",
                          borderRadius: "3px",
                          padding: "3px 0",
                          fontSize: "9px",
                          fontWeight: 500,
                          cursor: "pointer",
                          transition: "all 0.12s ease",
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.borderColor = "var(--border-medium)";
                          e.currentTarget.style.color = "var(--text-primary)";
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.borderColor = "var(--border-subtle)";
                          e.currentTarget.style.color = "var(--text-secondary)";
                        }}
                      >
                        50% Scale
                      </button>
                      <button
                        onClick={() => onSetBreakEven(p.id)}
                        title="Move Stop Loss to Entry ($0 Risk)"
                        style={{
                          background: p.breakEven ? "rgba(56, 189, 248, 0.12)" : "var(--bg-surface)",
                          border: `1px solid ${p.breakEven ? "rgba(56, 189, 248, 0.35)" : "var(--border-subtle)"}`,
                          color: p.breakEven ? "#38bdf8" : "var(--text-secondary)",
                          borderRadius: "3px",
                          padding: "3px 0",
                          fontSize: "9px",
                          fontWeight: p.breakEven ? 700 : 500,
                          cursor: "pointer",
                          transition: "all 0.12s ease",
                        }}
                      >
                        BE Lock
                      </button>
                      <button
                        onClick={() => onToggleTrailingStop(p.id)}
                        title="Dynamic Trailing Stop (1.5x ATR)"
                        style={{
                          background: p.trailingStop ? "var(--accent-green-subtle)" : "var(--bg-surface)",
                          border: `1px solid ${p.trailingStop ? "var(--accent-green-border)" : "var(--border-subtle)"}`,
                          color: p.trailingStop ? "var(--accent-green)" : "var(--text-secondary)",
                          borderRadius: "3px",
                          padding: "3px 0",
                          fontSize: "9px",
                          fontWeight: p.trailingStop ? 700 : 500,
                          cursor: "pointer",
                          transition: "all 0.12s ease",
                        }}
                      >
                        Trailing
                      </button>
                      <button
                        onClick={() => handleOpenEdit(p)}
                        style={{
                          background: "var(--bg-surface)",
                          border: "1px solid var(--border-subtle)",
                          color: "var(--text-primary)",
                          borderRadius: "3px",
                          padding: "3px 0",
                          fontSize: "9px",
                          fontWeight: 500,
                          cursor: "pointer",
                          transition: "all 0.12s ease",
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.borderColor = "var(--border-medium)";
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.borderColor = "var(--border-subtle)";
                        }}
                      >
                        TP/SL
                      </button>
                    </div>
                  </div>
                );
              })
            )
          )}
        </div>
      </div>

      {/* 3. Behavioral Guard Notice */}
      <div
        style={{
          background: "var(--bg-surface-elevated)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "4px",
          padding: "6px 10px",
          fontSize: "10px",
          color: "var(--text-secondary)",
          display: "flex",
          alignItems: "center",
          gap: "6px",
          flexShrink: 0,
        }}
      >
        <ShieldIcon size={12} color="var(--accent-blue)" />
        <span>Risk Guard: Max drawdown hard cap 4.0% active.</span>
      </div>

      {/* Edit TP/SL Modal */}
      {editingPos && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0, 0, 0, 0.7)",
            backdropFilter: "blur(6px)",
            WebkitBackdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
          }}
          onClick={() => setEditingPos(null)}
        >
          <div
            style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border-medium)",
              boxShadow: "var(--card-shadow)",
              borderRadius: "8px",
              padding: "16px 18px",
              width: "340px",
              display: "flex",
              flexDirection: "column",
              gap: "12px",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "12.5px", fontWeight: 700, color: "var(--text-primary)" }}>
                Edit Limits: {editingPos.symbol}
              </span>
              <button
                onClick={() => setEditingPos(null)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                  padding: "2px",
                  display: "inline-flex",
                  alignItems: "center",
                }}
              >
                <CloseIcon size={12} color="currentColor" />
              </button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              <div>
                <label style={{ display: "block", fontSize: "10px", color: "var(--text-muted)", marginBottom: "4px", fontWeight: 600 }}>
                  Take Profit Target (USD)
                </label>
                <input
                  type="number"
                  value={editTp}
                  onChange={(e) => setEditTp(e.target.value)}
                  style={{
                    width: "100%",
                    background: "var(--bg-surface-card)",
                    border: "1px solid var(--border-subtle)",
                    color: "var(--accent-green)",
                    borderRadius: "4px",
                    padding: "6px 8px",
                    fontSize: "12px",
                    fontFamily: "var(--font-mono)",
                    outline: "none",
                  }}
                  onFocus={(e) => (e.currentTarget.style.borderColor = "var(--accent-blue)")}
                  onBlur={(e) => (e.currentTarget.style.borderColor = "var(--border-subtle)")}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "10px", color: "var(--text-muted)", marginBottom: "4px", fontWeight: 600 }}>
                  Stop Loss Invalidation (USD)
                </label>
                <input
                  type="number"
                  value={editSl}
                  onChange={(e) => setEditSl(e.target.value)}
                  style={{
                    width: "100%",
                    background: "var(--bg-surface-card)",
                    border: "1px solid var(--border-subtle)",
                    color: "var(--accent-red)",
                    borderRadius: "4px",
                    padding: "6px 8px",
                    fontSize: "12px",
                    fontFamily: "var(--font-mono)",
                    outline: "none",
                  }}
                  onFocus={(e) => (e.currentTarget.style.borderColor = "var(--accent-blue)")}
                  onBlur={(e) => (e.currentTarget.style.borderColor = "var(--border-subtle)")}
                />
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", marginTop: "4px" }}>
              <button
                onClick={() => setEditingPos(null)}
                className="btn-sober"
                style={{ justifyContent: "center", padding: "6px 0" }}
              >
                Cancel
              </button>
              <button
                onClick={handleSaveTpSl}
                style={{
                  background: "var(--accent-blue)",
                  border: "none",
                  color: "#ffffff",
                  borderRadius: "4px",
                  padding: "6px 0",
                  fontSize: "11px",
                  fontWeight: 600,
                  cursor: "pointer",
                  transition: "opacity 0.15s ease",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.opacity = "0.9")}
                onMouseLeave={(e) => (e.currentTarget.style.opacity = "1")}
              >
                Save Limits
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
