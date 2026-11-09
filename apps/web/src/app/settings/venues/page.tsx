"use client";

import React, { useState } from "react";
import Link from "next/link";
import { BrokerVaultView } from "../../../components/BrokerVaultView";
import { ShieldIcon, ArrowLeftIcon, CheckIcon, AlertTriangleIcon } from "../../../components/Icons";

export default function SettingsVenuesPage() {
  const [activeTab, setActiveTab] = useState<"connections" | "vault">("connections");
  const [showMfaModal, setShowMfaModal] = useState(false);
  const [selectedEnv, setSelectedEnv] = useState<"paper" | "demo" | "live">("paper");
  const [mfaCode, setMfaCode] = useState("");
  const [mfaVerified, setMfaVerified] = useState(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  const mockConnections = [
    {
      id: "conn-paper-001",
      venue: "Paper Simulator",
      venueCode: "paper",
      environment: "paper",
      label: "Institutional Paper Engine",
      health: "healthy",
      healthDetail: "Verified deterministic execution book",
      lastContact: "Just now",
      capabilities: ["Market", "Limit", "Stop", "StopLimit", "ShortSelling", "TrailingStop"],
      routingHold: false,
    },
    {
      id: "conn-binance-001",
      venue: "Binance Spot",
      venueCode: "binance",
      environment: "live",
      label: "Binance Primary HFT",
      health: "healthy",
      healthDetail: "Weight quota 12/1000, server-time offset +2ms",
      lastContact: "1s ago",
      capabilities: ["Market", "Limit", "StreamingQuotes", "UserDataStream"],
      routingHold: false,
    },
    {
      id: "conn-bybit-001",
      venue: "Bybit Unified",
      venueCode: "bybit",
      environment: "demo",
      label: "Bybit Testnet Scalper",
      health: "degraded",
      healthDetail: "Elevated ping latency (185ms), feed degraded",
      lastContact: "14s ago",
      capabilities: ["Market", "Limit", "PostOnly", "StreamingQuotes"],
      routingHold: false,
    },
    {
      id: "conn-oanda-001",
      venue: "OANDA v20",
      venueCode: "oanda",
      environment: "demo",
      label: "Forex Practice Feed",
      health: "healthy",
      healthDetail: "Practice REST and Pricing Stream active",
      lastContact: "3s ago",
      capabilities: ["Market", "Limit", "Forex", "StreamingQuotes"],
      routingHold: false,
    },
    {
      id: "conn-mt5-001",
      venue: "MetaTrader 5",
      venueCode: "mt5",
      environment: "live",
      label: "MT5 Bridge Sidecar",
      health: "quarantined",
      healthDetail: "Quarantined: Credential rotation in progress via vault event",
      lastContact: "5m ago",
      capabilities: ["Forex", "CFD", "Indices"],
      routingHold: true,
    },
  ];

  const getHealthBadge = (health: string) => {
    switch (health) {
      case "healthy":
        return {
          label: "HEALTHY",
          bg: "rgba(34, 197, 94, 0.15)",
          color: "#4ade80",
          border: "rgba(34, 197, 94, 0.3)",
        };
      case "degraded":
        return {
          label: "DEGRADED",
          bg: "rgba(234, 179, 8, 0.15)",
          color: "#facc15",
          border: "rgba(234, 179, 8, 0.3)",
        };
      case "quarantined":
        return {
          label: "QUARANTINED",
          bg: "rgba(239, 68, 68, 0.15)",
          color: "#f87171",
          border: "rgba(239, 68, 68, 0.3)",
        };
      case "failed":
      default:
        return {
          label: "FAILED",
          bg: "rgba(239, 68, 68, 0.2)",
          color: "#ef4444",
          border: "rgba(239, 68, 68, 0.4)",
        };
    }
  };

  const handleVerifyLiveMfa = () => {
    if (mfaCode.trim().length === 6) {
      setMfaVerified(true);
      setShowMfaModal(false);
      setErrorBanner(null);
    } else {
      setErrorBanner("Invalid Step-Up TOTP Code. Please provide a valid 6-digit authenticator token.");
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--bg-canvas)",
        color: "var(--text-primary)",
        fontFamily: "'Inter', -apple-system, sans-serif",
        padding: "24px 32px",
      }}
    >
      {/* Top Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: "1px solid var(--border-subtle)",
          paddingBottom: "18px",
          marginBottom: "24px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <Link
            href="/"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 14px",
              borderRadius: "8px",
              background: "var(--bg-surface)",
              border: "1px solid var(--border-subtle)",
              color: "var(--text-secondary)",
              fontSize: "13px",
              fontWeight: 600,
              textDecoration: "none",
              transition: "all 0.15s ease",
            }}
          >
            ← Cockpit
          </Link>
          <div>
            <h1
              style={{
                fontSize: "20px",
                fontWeight: 700,
                letterSpacing: "-0.02em",
                color: "var(--text-primary)",
                margin: 0,
                display: "flex",
                alignItems: "center",
                gap: "10px",
              }}
            >
              <ShieldIcon size={20} color="var(--accent-blue)" />
              Venue & Broker Connections
              <span
                style={{
                  fontSize: "11px",
                  fontWeight: 600,
                  padding: "3px 8px",
                  borderRadius: "12px",
                  background: "var(--accent-blue-subtle)",
                  color: "var(--accent-blue)",
                  border: "1px solid var(--border-subtle)",
                }}
              >
                Spec 03 US1
              </span>
            </h1>
            <p style={{ margin: "4px 0 0", fontSize: "13px", color: "var(--text-muted)" }}>
              Manage institutional exchange connectivity, credential scoping, and real-time health verification.
            </p>
          </div>
        </div>

        {/* Tab switch */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "4px",
            background: "var(--bg-surface-elevated)",
            padding: "4px",
            borderRadius: "10px",
            border: "1px solid var(--border-subtle)",
          }}
        >
          <button
            onClick={() => setActiveTab("connections")}
            style={{
              padding: "7px 16px",
              borderRadius: "7px",
              border: activeTab === "connections" ? "1px solid var(--border-medium)" : "1px solid transparent",
              cursor: "pointer",
              fontSize: "12px",
              fontWeight: 600,
              background: activeTab === "connections" ? "var(--bg-surface-card)" : "transparent",
              color: activeTab === "connections" ? "var(--text-primary)" : "var(--text-muted)",
              transition: "all 0.15s ease",
            }}
          >
            Connections ({mockConnections.length})
          </button>
          <button
            onClick={() => setActiveTab("vault")}
            style={{
              padding: "7px 16px",
              borderRadius: "7px",
              border: activeTab === "vault" ? "1px solid var(--border-medium)" : "1px solid transparent",
              cursor: "pointer",
              fontSize: "12px",
              fontWeight: 600,
              background: activeTab === "vault" ? "var(--bg-surface-card)" : "transparent",
              color: activeTab === "vault" ? "var(--text-primary)" : "var(--text-muted)",
              transition: "all 0.15s ease",
            }}
          >
            Credential Vault
          </button>
        </div>
      </div>

      {/* Sanitized Error Banner */}
      {errorBanner && (
        <div
          style={{
            background: "var(--accent-red-subtle)",
            border: "1px solid var(--accent-red-border)",
            borderRadius: "8px",
            padding: "12px 16px",
            marginBottom: "20px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            color: "var(--accent-red)",
            fontSize: "13px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <AlertTriangleIcon size={16} color="var(--accent-red)" />
            <span>{errorBanner}</span>
          </div>
          <button
            onClick={() => setErrorBanner(null)}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
              fontSize: "14px",
            }}
          >
            ✕
          </button>
        </div>
      )}

      {activeTab === "connections" ? (
        <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "14px" }}>
          {mockConnections.map((conn) => {
            const badge = getHealthBadge(conn.health);
            return (
              <div
                key={conn.id}
                style={{
                  background: "var(--bg-surface)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "12px",
                  padding: "18px 22px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  boxShadow: "var(--card-shadow)",
                }}
              >
                <div style={{ display: "flex", alignItems: "flex-start", gap: "16px" }}>
                  <div
                    style={{
                      width: "42px",
                      height: "42px",
                      borderRadius: "10px",
                      background: "var(--accent-blue-subtle)",
                      border: "1px solid var(--border-subtle)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "var(--accent-blue)",
                      fontWeight: 700,
                      fontSize: "14px",
                    }}
                  >
                    {conn.venueCode.toUpperCase().slice(0, 3)}
                  </div>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                      <span style={{ fontSize: "15px", fontWeight: 700, color: "var(--text-primary)" }}>
                        {conn.venue}
                      </span>
                      <span
                        style={{
                          fontSize: "11px",
                          fontWeight: 600,
                          padding: "2px 7px",
                          borderRadius: "6px",
                          background:
                            conn.environment === "live"
                              ? "rgba(239, 68, 68, 0.15)"
                              : conn.environment === "demo"
                              ? "rgba(234, 179, 8, 0.15)"
                              : "rgba(56, 189, 248, 0.15)",
                          color:
                            conn.environment === "live"
                              ? "var(--accent-red)"
                              : conn.environment === "demo"
                              ? "#d97706"
                              : "var(--accent-blue)",
                          border: "1px solid var(--border-subtle)",
                          textTransform: "uppercase",
                        }}
                      >
                        {conn.environment}
                      </span>
                      <span
                        style={{
                          fontSize: "11px",
                          fontWeight: 700,
                          padding: "2px 8px",
                          borderRadius: "6px",
                          background: badge.bg,
                          color: badge.color,
                          border: `1px solid ${badge.border}`,
                          letterSpacing: "0.04em",
                        }}
                      >
                        {badge.label}
                      </span>
                      {conn.routingHold && (
                        <span
                          style={{
                            fontSize: "10px",
                            fontWeight: 700,
                            padding: "2px 6px",
                            borderRadius: "4px",
                            background: "rgba(239, 68, 68, 0.25)",
                            color: "var(--accent-red)",
                            border: "1px solid rgba(239, 68, 68, 0.4)",
                          }}
                        >
                          ROUTING HOLD
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "3px" }}>
                      {conn.label} · <span>ID: {conn.id}</span>
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "6px" }}>
                      {conn.healthDetail}
                    </div>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <button
                    onClick={() => {
                      if (conn.environment === "live" && !mfaVerified) {
                        setSelectedEnv("live");
                        setShowMfaModal(true);
                      } else {
                        alert(`Re-verified connection ${conn.id}. Health is verified.`);
                      }
                    }}
                    style={{
                      padding: "8px 14px",
                      borderRadius: "7px",
                      background: "var(--bg-surface-elevated)",
                      border: "1px solid var(--border-subtle)",
                      color: "var(--text-primary)",
                      fontSize: "12px",
                      fontWeight: 600,
                      cursor: "pointer",
                    }}
                  >
                    Verify Permissions
                  </button>
                  <button
                    onClick={() => alert(`Connection details for ${conn.id}`)}
                    style={{
                      padding: "8px 14px",
                      borderRadius: "7px",
                      background: "var(--accent-blue-subtle)",
                      border: "1px solid var(--border-subtle)",
                      color: "var(--accent-blue)",
                      fontSize: "12px",
                      fontWeight: 600,
                      cursor: "pointer",
                    }}
                  >
                    Manage
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <BrokerVaultView />
      )}

      {/* Step-Up MFA Modal for Live Environments */}
      {showMfaModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.6)",
            backdropFilter: "blur(8px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
          }}
        >
          <div
            style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border-medium)",
              borderRadius: "14px",
              padding: "26px",
              maxWidth: "420px",
              width: "100%",
              boxShadow: "var(--card-shadow)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "14px" }}>
              <ShieldIcon size={22} color="var(--accent-blue)" />
              <h2 style={{ fontSize: "17px", fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
                Step-Up MFA Verification
              </h2>
            </div>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: "1.5", margin: "0 0 16px" }}>
              Connecting or re-verifying a <strong>LIVE</strong> real-money exchange connection requires secondary
              TOTP authentication (Constitution VIII, SC-011).
            </p>
            <input
              type="text"
              placeholder="Enter 6-digit TOTP code"
              value={mfaCode}
              onChange={(e) => setMfaCode(e.target.value)}
              style={{
                width: "100%",
                padding: "10px 14px",
                borderRadius: "8px",
                background: "var(--bg-surface-elevated)",
                border: "1px solid var(--border-subtle)",
                color: "var(--text-primary)",
                fontSize: "15px",
                letterSpacing: "0.2em",
                textAlign: "center",
                marginBottom: "16px",
                boxSizing: "border-box",
              }}
              maxLength={6}
            />
            <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
              <button
                onClick={() => setShowMfaModal(false)}
                style={{
                  padding: "8px 16px",
                  borderRadius: "7px",
                  background: "transparent",
                  border: "1px solid var(--border-subtle)",
                  color: "var(--text-muted)",
                  fontSize: "13px",
                  cursor: "pointer",
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleVerifyLiveMfa}
                style={{
                  padding: "8px 18px",
                  borderRadius: "7px",
                  background: "var(--accent-blue)",
                  border: "none",
                  color: "#ffffff",
                  fontSize: "13px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Verify & Authorize
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
