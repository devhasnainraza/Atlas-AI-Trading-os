"use client";

import React, { useState } from "react";
import { soundManager } from "../lib/soundEffects";
import { AssetDef } from "./MarketScanner";
import { BellIcon, VolumeIcon, CloseIcon, ZapIcon, TrashIcon } from "./Icons";

export interface TradingAlert {
  id: string;
  symbol: string;
  type: "PRICE_ABOVE" | "PRICE_BELOW" | "RSI_OVERSOLD" | "RSI_OVERBOUGHT" | "VOLUME_SPIKE";
  targetValue: number;
  currentValue?: number;
  note: string;
  status: "ACTIVE" | "TRIGGERED" | "PAUSED";
  createdAt: string;
  triggeredAt?: string;
  soundEnabled: boolean;
}

interface AlertsManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
  alerts: TradingAlert[];
  onAddAlert: (alert: Omit<TradingAlert, "id" | "createdAt" | "status">) => void;
  onToggleAlertStatus: (alertId: string) => void;
  onDeleteAlert: (alertId: string) => void;
  onTriggerTestAlert: (alertId: string) => void;
  activeAsset: AssetDef;
}

const AVAILABLE_SYMBOLS = [
  "BTC/USDT",
  "ETH/USDT",
  "SOL/USDT",
  "BNB/USDT",
  "XRP/USDT",
  "EUR/USD",
  "XAU/USD",
];

export function AlertsManagerModal({
  isOpen,
  onClose,
  alerts,
  onAddAlert,
  onToggleAlertStatus,
  onDeleteAlert,
  onTriggerTestAlert,
  activeAsset,
}: AlertsManagerModalProps) {
  const [activeTab, setActiveTab] = useState<"active" | "create" | "history">("active");
  const [newSymbol, setNewSymbol] = useState(activeAsset.symbol);
  const [newType, setNewType] = useState<TradingAlert["type"]>("PRICE_ABOVE");
  const [newTargetValue, setNewTargetValue] = useState<string>(
    (activeAsset.rawPrice * 1.015).toFixed(2)
  );
  const [newNote, setNewNote] = useState("Key breakout level / resistance test");
  const [soundEnabled, setSoundEnabled] = useState(true);

  if (!isOpen) return null;

  const handleCreateAlert = (e: React.FormEvent) => {
    e.preventDefault();
    soundManager.playClick();

    const val = parseFloat(newTargetValue);
    if (isNaN(val) || val <= 0) return;

    onAddAlert({
      symbol: newSymbol,
      type: newType,
      targetValue: val,
      note: newNote.trim() || "Manual price alert",
      soundEnabled,
    });

    setActiveTab("active");
  };

  const activeAlerts = alerts.filter((a) => a.status !== "TRIGGERED");
  const triggeredAlerts = alerts.filter((a) => a.status === "TRIGGERED");

  const getTypeLabel = (type: TradingAlert["type"], val: number) => {
    switch (type) {
      case "PRICE_ABOVE":
        return `Price crosses above $${val.toLocaleString()}`;
      case "PRICE_BELOW":
        return `Price drops below $${val.toLocaleString()}`;
      case "RSI_OVERSOLD":
        return `RSI 14 drops below ${val} (Oversold)`;
      case "RSI_OVERBOUGHT":
        return `RSI 14 spikes above ${val} (Overbought)`;
      case "VOLUME_SPIKE":
        return `Volume surges > ${val}x moving average`;
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(4, 6, 11, 0.78)",
        backdropFilter: "blur(12px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        padding: "20px",
        animation: "fadeIn 0.15s ease",
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: "740px",
          maxWidth: "96vw",
          height: "640px",
          maxHeight: "90vh",
          background: "var(--bg-surface)",
          border: "1px solid var(--border-medium)",
          borderRadius: "12px",
          boxShadow: "var(--card-shadow)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            height: "52px",
            padding: "0 16px",
            background: "var(--bg-surface-elevated)",
            borderBottom: "1px solid var(--border-subtle)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexShrink: 0,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div
              style={{
                width: "28px",
                height: "28px",
                borderRadius: "6px",
                background: "var(--bg-surface-card)",
                border: "1px solid var(--border-subtle)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--accent-blue)",
              }}
            >
              <BellIcon size={14} color="var(--accent-blue)" />
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)", letterSpacing: "0.2px" }}>
                  PRICE & TECHNICAL ALERTS
                </span>
                <span
                  style={{
                    fontSize: "9px",
                    fontFamily: "var(--font-mono)",
                    color: "var(--text-secondary)",
                    background: "var(--bg-surface-card)",
                    border: "1px solid var(--border-subtle)",
                    padding: "1px 6px",
                    borderRadius: "3px",
                  }}
                >
                  {activeAlerts.length} ARMED
                </span>
              </div>
              <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>
                Condition triggers with synthesized audio alarms and visual HUD notifications.
              </span>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <button
              onClick={() => {
                soundManager.playClick();
                setActiveTab((prev) => (prev === "create" ? "active" : "create"));
              }}
              style={{
                background: "var(--bg-surface-card)",
                border: "1px solid var(--border-subtle)",
                color: "var(--text-primary)",
                borderRadius: "4px",
                padding: "4px 10px",
                fontSize: "11px",
                fontWeight: 600,
                cursor: "pointer",
                transition: "border-color 0.15s ease",
              }}
            >
              {activeTab === "create" ? "View Alerts" : "+ New Alert"}
            </button>
            <button
              onClick={onClose}
              style={{
                background: "transparent",
                border: "none",
                color: "var(--text-muted)",
                cursor: "pointer",
                padding: "4px 8px",
                display: "flex",
                alignItems: "center",
              }}
            >
              <CloseIcon size={14} color="var(--text-muted)" />
            </button>
          </div>
        </div>

        {/* Tab Switcher */}
        <div
          style={{
            height: "36px",
            background: "var(--bg-surface-elevated)",
            borderBottom: "1px solid var(--border-subtle)",
            display: "flex",
            alignItems: "center",
            padding: "0 16px",
            gap: "6px",
            flexShrink: 0,
          }}
        >
          <button
            onClick={() => {
              soundManager.playClick();
              setActiveTab("active");
            }}
            style={{
              background: activeTab === "active" ? "var(--bg-surface-card)" : "transparent",
              color: activeTab === "active" ? "var(--text-primary)" : "var(--text-muted)",
              border: activeTab === "active" ? "1px solid var(--border-subtle)" : "1px solid transparent",
              borderRadius: "4px",
              padding: "3px 10px",
              fontSize: "11px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Active Triggers ({activeAlerts.length})
          </button>
          <button
            onClick={() => {
              soundManager.playClick();
              setActiveTab("history");
            }}
            style={{
              background: activeTab === "history" ? "var(--bg-surface-card)" : "transparent",
              color: activeTab === "history" ? "var(--text-primary)" : "var(--text-muted)",
              border: activeTab === "history" ? "1px solid var(--border-subtle)" : "1px solid transparent",
              borderRadius: "4px",
              padding: "3px 10px",
              fontSize: "11px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Triggered History ({triggeredAlerts.length})
          </button>
          <button
            onClick={() => {
              soundManager.playClick();
              setActiveTab("create");
            }}
            style={{
              background: activeTab === "create" ? "rgba(56, 189, 248, 0.15)" : "transparent",
              color: activeTab === "create" ? "#38bdf8" : "var(--text-muted)",
              border: activeTab === "create" ? "1px solid rgba(56, 189, 248, 0.3)" : "1px solid transparent",
              borderRadius: "4px",
              padding: "3px 10px",
              fontSize: "11px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            + Create Rule
          </button>
        </div>

        {/* Content Body */}
        <div style={{ flex: 1, overflowY: "auto", padding: "16px", display: "flex", flexDirection: "column", gap: "10px" }}>
          {/* View 1: Active Alerts List */}
          {activeTab === "active" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {activeAlerts.length === 0 ? (
                <div style={{ padding: "40px 0", textAlign: "center", color: "#64748b", fontSize: "12px" }}>
                  <span>No active alerts armed. Click "+ New Alert" to create one.</span>
                </div>
              ) : (
                activeAlerts.map((alt) => (
                  <div
                    key={alt.id}
                    style={{
                      background: "var(--bg-surface-elevated)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "8px",
                      padding: "12px 14px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: "12px",
                      opacity: alt.status === "ACTIVE" ? 1 : 0.6,
                    }}
                    className="tabular-nums"
                  >
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{ fontWeight: 700, color: "var(--text-primary)", fontSize: "12px" }}>{alt.symbol}</span>
                        <span
                          style={{
                            fontSize: "9px",
                            fontFamily: "var(--font-mono)",
                            padding: "1px 5px",
                            borderRadius: "3px",
                            background: alt.status === "ACTIVE" ? "rgba(34, 197, 94, 0.1)" : "var(--bg-surface-card)",
                            color: alt.status === "ACTIVE" ? "#22c55e" : "var(--text-muted)",
                            border: `1px solid ${alt.status === "ACTIVE" ? "rgba(34, 197, 94, 0.25)" : "var(--border-subtle)"}`,
                          }}
                        >
                          {alt.status}
                        </span>
                        {alt.soundEnabled && <VolumeIcon size={11} color="var(--text-muted)" />}
                      </div>

                      <span style={{ fontSize: "12px", color: "var(--text-primary)", fontWeight: 600, display: "block", marginTop: "2px" }}>
                        {getTypeLabel(alt.type, alt.targetValue)}
                      </span>
                      <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>Note: {alt.note} · Created {alt.createdAt}</span>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <button
                        onClick={() => onTriggerTestAlert(alt.id)}
                        style={{
                          background: "var(--bg-surface-card)",
                          border: "1px solid var(--border-subtle)",
                          color: "var(--text-secondary)",
                          borderRadius: "4px",
                          padding: "4px 8px",
                          fontSize: "10px",
                          fontWeight: 600,
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          gap: "4px",
                          transition: "border-color 0.15s ease",
                        }}
                        title="Simulate this alert firing right now with synthesized audio alarm"
                      >
                        <ZapIcon size={11} color="#cbd5e1" />
                        <span>Test Fire</span>
                      </button>

                      <button
                        onClick={() => {
                          soundManager.playClick();
                          onToggleAlertStatus(alt.id);
                        }}
                        style={{
                          background: "transparent",
                          border: "1px solid var(--border-subtle)",
                          color: "#94a3b8",
                          borderRadius: "4px",
                          padding: "4px 8px",
                          fontSize: "10px",
                          cursor: "pointer",
                        }}
                      >
                        {alt.status === "ACTIVE" ? "Pause" : "Resume"}
                      </button>

                      <button
                        onClick={() => {
                          soundManager.playClick();
                          onDeleteAlert(alt.id);
                        }}
                        style={{
                          background: "transparent",
                          border: "none",
                          color: "#64748b",
                          cursor: "pointer",
                          padding: "4px 6px",
                          display: "flex",
                          alignItems: "center",
                        }}
                        title="Delete alert"
                      >
                        <TrashIcon size={12} color="#64748b" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* View 2: Create New Alert Form */}
          {activeTab === "create" && (
            <form onSubmit={handleCreateAlert} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div style={{ background: "var(--bg-surface-elevated)", border: "1px solid var(--border-subtle)", borderRadius: "8px", padding: "14px", display: "flex", flexDirection: "column", gap: "12px" }}>
                <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-primary)" }}>Configure Alert Rule</span>

                {/* Instrument Selector */}
                <div>
                  <label style={{ fontSize: "10px", color: "var(--text-muted)", display: "block", marginBottom: "4px" }}>TARGET INSTRUMENT</label>
                  <select
                    value={newSymbol}
                    onChange={(e) => setNewSymbol(e.target.value)}
                    style={{
                      width: "100%",
                      background: "var(--bg-surface-card)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "5px",
                      color: "var(--text-primary)",
                      padding: "6px 10px",
                      fontSize: "12px",
                      outline: "none",
                    }}
                  >
                    {AVAILABLE_SYMBOLS.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Condition Type */}
                <div>
                  <label style={{ fontSize: "10px", color: "var(--text-muted)", display: "block", marginBottom: "4px" }}>CONDITION TYPE</label>
                  <select
                    value={newType}
                    onChange={(e) => setNewType(e.target.value as any)}
                    style={{
                      width: "100%",
                      background: "var(--bg-surface-card)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "5px",
                      color: "var(--text-primary)",
                      padding: "6px 10px",
                      fontSize: "12px",
                      outline: "none",
                    }}
                  >
                    <option value="PRICE_ABOVE">Price Crosses Above ($)</option>
                    <option value="PRICE_BELOW">Price Drops Below ($)</option>
                    <option value="RSI_OVERSOLD">RSI 14 Drops Below (e.g. 30)</option>
                    <option value="RSI_OVERBOUGHT">RSI 14 Spikes Above (e.g. 70)</option>
                    <option value="VOLUME_SPIKE">Volume Surge Factor (e.g. 2.0x)</option>
                  </select>
                </div>

                {/* Target Value Input */}
                <div>
                  <label style={{ fontSize: "10px", color: "var(--text-muted)", display: "block", marginBottom: "4px" }}>TARGET THRESHOLD</label>
                  <input
                    type="number"
                    step="any"
                    value={newTargetValue}
                    onChange={(e) => setNewTargetValue(e.target.value)}
                    style={{
                      width: "100%",
                      background: "var(--bg-surface-card)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "5px",
                      color: "var(--text-primary)",
                      padding: "6px 10px",
                      fontSize: "12px",
                      outline: "none",
                    }}
                    required
                  />
                </div>

                {/* Custom Note */}
                <div>
                  <label style={{ fontSize: "10px", color: "var(--text-muted)", display: "block", marginBottom: "4px" }}>EXECUTION NOTE / TAG</label>
                  <input
                    type="text"
                    value={newNote}
                    onChange={(e) => setNewNote(e.target.value)}
                    placeholder="e.g. Look for FVG re-test long setup"
                    style={{
                      width: "100%",
                      background: "var(--bg-surface-card)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "5px",
                      color: "var(--text-primary)",
                      padding: "6px 10px",
                      fontSize: "12px",
                      outline: "none",
                    }}
                  />
                </div>

                {/* Sound Alarm Checkbox */}
                <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "11px", color: "var(--text-secondary)", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={soundEnabled}
                    onChange={(e) => setSoundEnabled(e.target.checked)}
                    style={{ accentColor: "#f59e0b" }}
                  />
                  <span>Play synthesized Web Audio alarm tone when triggered</span>
                </label>
              </div>

              <button
                type="submit"
                style={{
                  background: "#10b981",
                  border: "none",
                  borderRadius: "6px",
                  color: "#05160e",
                  fontWeight: 800,
                  padding: "10px 0",
                  fontSize: "12px",
                  cursor: "pointer",
                }}
              >
                ARM THIS ALERT
              </button>
            </form>
          )}

          {/* View 3: Triggered History */}
          {activeTab === "history" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              {triggeredAlerts.length === 0 ? (
                <div style={{ padding: "40px 0", textAlign: "center", color: "#64748b", fontSize: "12px" }}>
                  No alerts have fired yet. Test an alert from the Active tab.
                </div>
              ) : (
                triggeredAlerts.map((alt) => (
                  <div
                    key={alt.id}
                    style={{
                      background: "var(--bg-surface-elevated)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "6px",
                      padding: "10px 12px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                    }}
                    className="tabular-nums"
                  >
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <span style={{ fontWeight: 800, color: "var(--text-primary)", fontSize: "12px" }}>{alt.symbol}</span>
                        <span style={{ fontSize: "9px", color: "#f59e0b", background: "rgba(245, 158, 11, 0.12)", padding: "1px 5px", borderRadius: "3px" }}>
                          TRIGGERED
                        </span>
                      </div>
                      <span style={{ fontSize: "11px", color: "var(--text-secondary)" }}>{getTypeLabel(alt.type, alt.targetValue)}</span>
                      <span style={{ fontSize: "10px", color: "var(--text-muted)", display: "block" }}>
                        Fired at: {alt.triggeredAt || "Just now"} · Note: {alt.note}
                      </span>
                    </div>

                    <button
                      onClick={() => {
                        soundManager.playClick();
                        onDeleteAlert(alt.id);
                      }}
                      style={{
                        background: "transparent",
                        border: "none",
                        color: "var(--text-muted)",
                        cursor: "pointer",
                        padding: "4px 6px",
                        display: "flex",
                        alignItems: "center",
                      }}
                      title="Delete alert"
                    >
                      <TrashIcon size={12} color="currentColor" />
                    </button>
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            height: "40px",
            background: "var(--bg-surface-elevated)",
            borderTop: "1px solid var(--border-subtle)",
            padding: "0 16px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            fontSize: "10px",
            color: "var(--text-muted)",
            flexShrink: 0,
          }}
        >
          <span>Real-time price feed: <strong style={{ color: "var(--accent-green)" }}>Live Binance WebSockets</strong></span>
          <span>[Esc] Close Manager</span>
        </div>
      </div>
    </div>
  );
}
