"use client";

import React, { useState, useEffect } from "react";
import {
  ConnectedExchange,
  ATLAS_STATIC_IPS,
  INITIAL_SOCIAL_BROADCASTS,
  validateApiKey,
  SocialBroadcast,
} from "../lib/apiVault";
import { soundManager } from "../lib/soundEffects";
import {
  ShieldIcon,
  ZapIcon,
  CheckIcon,
  AlertTriangleIcon,
  RefreshIcon,
  TrashIcon,
  CloseIcon,
  SlidersIcon,
  ActivityIcon,
} from "./Icons";

interface BrokerVaultViewProps {
  onSyncTotalBalance?: (balance: number) => void;
  onSyncRealData?: (data: { balanceUsd: number; positions: any[]; openOrders: any[] }) => void;
  onOpenChannelSettings?: () => void;
}

export function BrokerVaultView({ onSyncTotalBalance, onSyncRealData, onOpenChannelSettings }: BrokerVaultViewProps) {
  const [activeVaultSection, setActiveVaultSection] = useState<"ACCOUNTS" | "AI_KEYS" | "CHANNELS">("ACCOUNTS");
  const [broadcasts, setBroadcasts] = useState<SocialBroadcast[]>(INITIAL_SOCIAL_BROADCASTS);
  const [isConnectModalOpen, setIsConnectModalOpen] = useState(false);
  const [activeConnectTab, setActiveConnectTab] = useState<"API_KEY" | "OAUTH" | "WEB3">("API_KEY");

  // Real Database Vault Credentials
  const [vaultCredentials, setVaultCredentials] = useState<any[]>([]);
  const [realPortfolio, setRealPortfolio] = useState<any | null>(null);
  const [isLoadingCredentials, setIsLoadingCredentials] = useState(false);
  const [isSyncingRealPortfolio, setIsSyncingRealPortfolio] = useState(false);

  // Form states for Broker
  const [selectedExchangeName, setSelectedExchangeName] = useState("Binance");
  const [inputApiKey, setInputApiKey] = useState("");
  const [inputApiSecret, setInputApiSecret] = useState("");
  const [isSavingBroker, setIsSavingBroker] = useState(false);
  const [brokerError, setBrokerError] = useState<string | null>(null);

  // Form states for AI Key
  const [aiProvider, setAiProvider] = useState<"groq" | "openai">("groq");
  const [inputAiKey, setInputAiKey] = useState("");
  const [isSavingAiKey, setIsSavingAiKey] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  const [copiedIp, setCopiedIp] = useState(false);
  const [successToast, setSuccessToast] = useState<string | null>(null);

  // Load user credentials and real portfolio from database on mount
  const loadCredentialsAndSync = async () => {
    setIsLoadingCredentials(true);
    try {
      // 1. Fetch encrypted credentials metadata
      const credRes = await fetch("/api/vault/credentials");
      if (credRes.ok) {
        const credData = await credRes.json();
        setVaultCredentials(credData.credentials || []);
      }

      // 2. Fetch real exchange portfolio
      setIsSyncingRealPortfolio(true);
      const portRes = await fetch("/api/broker/real-portfolio");
      if (portRes.ok) {
        const portData = await portRes.json();
        setRealPortfolio(portData);

        if (portData.connected && onSyncRealData) {
          onSyncRealData({
            balanceUsd: portData.totalBalanceUsd,
            positions: portData.positions || [],
            openOrders: portData.openOrders || [],
          });
        }
        if (portData.connected && onSyncTotalBalance) {
          onSyncTotalBalance(portData.totalBalanceUsd);
        }
      }
    } catch (err) {
      console.error("Failed to load vault credentials:", err);
    } finally {
      setIsLoadingCredentials(false);
      setIsSyncingRealPortfolio(false);
    }
  };

  useEffect(() => {
    loadCredentialsAndSync();
  }, []);

  const handleCopyIps = () => {
    navigator.clipboard?.writeText(ATLAS_STATIC_IPS.join(", "));
    setCopiedIp(true);
    soundManager.playClick();
    setTimeout(() => setCopiedIp(false), 2500);
  };

  // Save Personal AI Key to DB
  const handleSaveAiKey = async (e: React.FormEvent) => {
    e.preventDefault();
    setAiError(null);
    setIsSavingAiKey(true);
    soundManager.playClick();

    try {
      const res = await fetch("/api/vault/save-ai-key", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider: aiProvider,
          apiKey: inputAiKey,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        setAiError(data.error || "Failed to verify and save AI key");
        soundManager.playErrorBeep();
      } else {
        soundManager.playOrderFilled();
        setInputAiKey("");
        setSuccessToast(data.message || "AI API Key successfully encrypted in your private vault!");
        setTimeout(() => setSuccessToast(null), 4000);
        await loadCredentialsAndSync();
      }
    } catch (err: any) {
      setAiError(err.message || "Network error while saving AI key");
      soundManager.playErrorBeep();
    } finally {
      setIsSavingAiKey(false);
    }
  };

  // Save Real Broker Key to DB
  const handleSaveBrokerConnection = async (e: React.FormEvent) => {
    e.preventDefault();
    setBrokerError(null);
    setIsSavingBroker(true);
    soundManager.playClick();

    try {
      const res = await fetch("/api/vault/save-broker-key", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider: selectedExchangeName.toLowerCase(),
          apiKey: inputApiKey,
          apiSecret: inputApiSecret,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        setBrokerError(data.error || "Failed to connect broker");
        soundManager.playErrorBeep();
      } else {
        soundManager.playOrderFilled();
        setIsConnectModalOpen(false);
        setInputApiKey("");
        setInputApiSecret("");
        setSuccessToast(data.message || `Connected to ${selectedExchangeName} with AES-256-GCM encryption!`);
        setTimeout(() => setSuccessToast(null), 4000);
        await loadCredentialsAndSync();
      }
    } catch (err: any) {
      setBrokerError(err.message || "Network error while connecting broker");
      soundManager.playErrorBeep();
    } finally {
      setIsSavingBroker(false);
    }
  };

  // Delete Credential
  const handleDeleteCredential = async (provider: string) => {
    soundManager.playClick();
    if (!confirm(`Are you sure you want to revoke and delete your ${provider.toUpperCase()} credentials?`)) return;

    try {
      const res = await fetch("/api/vault/delete-credential", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider }),
      });
      if (res.ok) {
        soundManager.playOrderFilled();
        setSuccessToast(`Deleted ${provider.toUpperCase()} credential from vault.`);
        setTimeout(() => setSuccessToast(null), 3000);
        await loadCredentialsAndSync();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const connectedBrokerCreds = vaultCredentials.filter((c) => c.category === "BROKER");
  const connectedAiCreds = vaultCredentials.filter((c) => c.category === "AI");
  const isBrokerConnected = realPortfolio?.connected && connectedBrokerCreds.length > 0;
  const totalVaultBalance = isBrokerConnected ? (realPortfolio?.totalBalanceUsd || 0) : 0;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        width: "100%",
        background: "var(--bg-canvas)",
        color: "var(--text-primary)",
        overflow: "hidden",
      }}
    >
      {/* ═══════════ TOP COMMAND RIBBON ═══════════ */}
      <div
        style={{
          padding: "10px 16px",
          background: "var(--bg-surface-elevated)",
          borderBottom: "1px solid var(--border-subtle)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "10px",
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          {/* Desk Title & Status */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "13px", fontWeight: 800, letterSpacing: "-0.01em", color: "var(--text-primary)" }}>
              ATLAS <span style={{ color: "var(--accent-green)", fontWeight: 700 }}>ZERO-KNOWLEDGE VAULT</span>
            </span>
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
                background: "var(--accent-green-subtle)",
                border: "1px solid var(--accent-green-border)",
                borderRadius: "4px",
                padding: "1px 5px",
                fontSize: "9px",
                fontWeight: 600,
                color: "var(--accent-green)",
              }}
            >
              <ShieldIcon size={10} color="var(--accent-green)" />
              AES-256-GCM ENCRYPTED
            </span>
          </div>

          <div style={{ height: "20px", width: "1px", background: "var(--border-subtle)", flexShrink: 0 }} />

          {/* Metric 1: Total Real Vault Balance */}
          <div style={{ whiteSpace: "nowrap" }}>
            <div style={{ fontSize: "9.5px", color: "var(--text-muted)" }}>Real Exchange Capital</div>
            <div className="tabular-nums" style={{ fontSize: "12px", fontWeight: 700, color: isBrokerConnected ? "var(--accent-green)" : "var(--text-muted)" }}>
              ${totalVaultBalance.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </div>

          <div style={{ height: "20px", width: "1px", background: "var(--border-subtle)", flexShrink: 0 }} />

          {/* Metric 2: Active Connections */}
          <div style={{ whiteSpace: "nowrap" }}>
            <div style={{ fontSize: "9.5px", color: "var(--text-muted)" }}>Real Brokers</div>
            <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: "5px" }}>
              <span className={isBrokerConnected ? "live-dot-green" : "live-dot-amber"} />
              <span>{connectedBrokerCreds.length} Connected</span>
            </div>
          </div>

          <div style={{ height: "20px", width: "1px", background: "var(--border-subtle)", flexShrink: 0 }} />

          {/* Metric 3: AI Engine Status */}
          <div style={{ whiteSpace: "nowrap" }}>
            <div style={{ fontSize: "9.5px", color: "var(--text-muted)" }}>Personal AI Engine</div>
            <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: "5px" }}>
              <span className={connectedAiCreds.length > 0 ? "live-dot-green" : "live-dot-amber"} />
              <span>{connectedAiCreds.length > 0 ? `${connectedAiCreds[0].provider.toUpperCase()} Active` : "Not Configured"}</span>
            </div>
          </div>
        </div>

        {/* Resync Button */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <button
            onClick={() => {
              soundManager.playClick();
              loadCredentialsAndSync();
            }}
            disabled={isSyncingRealPortfolio}
            style={{
              background: "var(--bg-surface-elevated)",
              border: "1px solid var(--border-medium)",
              color: "var(--text-primary)",
              borderRadius: "4px",
              padding: "4px 8px",
              fontSize: "10.5px",
              fontWeight: 600,
              cursor: isSyncingRealPortfolio ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              gap: "5px",
            }}
          >
            <RefreshIcon size={12} color="currentColor" />
            <span>{isSyncingRealPortfolio ? "Syncing Real Balance..." : "Resync Real Exchange"}</span>
          </button>
        </div>
      </div>

      {/* ═══════════ NAVIGATION SUB-TABS ═══════════ */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "4px",
          padding: "6px 16px",
          background: "var(--bg-surface-card)",
          borderBottom: "1px solid var(--border-subtle)",
          flexShrink: 0,
        }}
      >
        <button
          onClick={() => {
            soundManager.playClick();
            setActiveVaultSection("ACCOUNTS");
          }}
          style={{
            background: activeVaultSection === "ACCOUNTS" ? "var(--bg-surface-elevated)" : "transparent",
            color: activeVaultSection === "ACCOUNTS" ? "var(--text-primary)" : "var(--text-secondary)",
            border: activeVaultSection === "ACCOUNTS" ? "1px solid var(--border-medium)" : "1px solid transparent",
            borderRadius: "4px",
            padding: "5px 12px",
            fontSize: "11px",
            fontWeight: activeVaultSection === "ACCOUNTS" ? 700 : 500,
            cursor: "pointer",
          }}
        >
          1. Broker & Exchange Gateways ({connectedBrokerCreds.length})
        </button>

        <button
          onClick={() => {
            soundManager.playClick();
            setActiveVaultSection("AI_KEYS");
          }}
          style={{
            background: activeVaultSection === "AI_KEYS" ? "var(--bg-surface-elevated)" : "transparent",
            color: activeVaultSection === "AI_KEYS" ? "var(--text-primary)" : "var(--text-secondary)",
            border: activeVaultSection === "AI_KEYS" ? "1px solid var(--border-medium)" : "1px solid transparent",
            borderRadius: "4px",
            padding: "5px 12px",
            fontSize: "11px",
            fontWeight: activeVaultSection === "AI_KEYS" ? 700 : 500,
            cursor: "pointer",
          }}
        >
          2. Personal AI API Keys ({connectedAiCreds.length})
        </button>

        <button
          onClick={() => {
            soundManager.playClick();
            setActiveVaultSection("CHANNELS");
          }}
          style={{
            background: activeVaultSection === "CHANNELS" ? "var(--bg-surface-elevated)" : "transparent",
            color: activeVaultSection === "CHANNELS" ? "var(--text-primary)" : "var(--text-secondary)",
            border: activeVaultSection === "CHANNELS" ? "1px solid var(--border-medium)" : "1px solid transparent",
            borderRadius: "4px",
            padding: "5px 12px",
            fontSize: "11px",
            fontWeight: activeVaultSection === "CHANNELS" ? 700 : 500,
            cursor: "pointer",
          }}
        >
          3. Mobile WhatsApp & Webhooks
        </button>
      </div>

      {/* ═══════════ MAIN CONTENT BODY ═══════════ */}
      <div style={{ flex: 1, overflowY: "auto", padding: "16px", display: "flex", flexDirection: "column", gap: "16px" }}>
        {/* Success Toast */}
        {successToast && (
          <div
            style={{
              padding: "10px 14px",
              background: "rgba(34, 197, 94, 0.15)",
              border: "1px solid rgba(34, 197, 94, 0.35)",
              borderRadius: "6px",
              color: "var(--accent-green)",
              fontSize: "12px",
              fontWeight: 600,
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <CheckIcon size={14} color="var(--accent-green)" />
            <span>{successToast}</span>
          </div>
        )}

        {/* ══════════ SECTION 1: BROKER GATEWAYS (STRICT REAL EXCHANGE ONLY) ══════════ */}
        {activeVaultSection === "ACCOUNTS" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            {/* Strict Real Exchange Alert Banner if not connected */}
            {!isBrokerConnected && (
              <div
                style={{
                  padding: "14px 18px",
                  borderRadius: "8px",
                  background: "rgba(245, 158, 11, 0.08)",
                  border: "1px solid rgba(245, 158, 11, 0.25)",
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "12px",
                }}
              >
                <AlertTriangleIcon size={18} color="#f59e0b" style={{ flexShrink: 0, marginTop: "2px" }} />
                <div>
                  <h4 style={{ margin: 0, fontSize: "13px", fontWeight: 700, color: "#f59e0b" }}>
                    Strict Real Exchange Enforcement Active
                  </h4>
                  <p style={{ margin: "4px 0 0 0", fontSize: "11.5px", color: "var(--text-muted)", lineHeight: 1.5 }}>
                    Atlas OS is running in strict user-specific mode. Your dashboard and orders will show <strong>only your real assets</strong>.
                    Connect your personal Binance or Bybit API Key below. All credentials are encrypted via AES-256-GCM in your isolated database record.
                  </p>
                </div>
              </div>
            )}

            {/* Header with Connect Button */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <h3 style={{ margin: 0, fontSize: "14px", fontWeight: 700, color: "var(--text-primary)" }}>
                  Connected Broker & Exchange Gateways
                </h3>
                <p style={{ margin: "2px 0 0 0", fontSize: "11px", color: "var(--text-muted)" }}>
                  Direct HMAC-signed execution gateways with zero file storage.
                </p>
              </div>
              <button
                onClick={() => {
                  soundManager.playClick();
                  setIsConnectModalOpen(true);
                }}
                style={{
                  background: "var(--accent-green)",
                  color: "#000000",
                  border: "none",
                  borderRadius: "5px",
                  padding: "6px 14px",
                  fontSize: "11px",
                  fontWeight: 700,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                <ZapIcon size={12} color="#000000" />
                <span>+ Connect Real Broker Key</span>
              </button>
            </div>

            {/* List of Connected Brokers */}
            {connectedBrokerCreds.length === 0 ? (
              <div
                style={{
                  padding: "36px 20px",
                  borderRadius: "8px",
                  border: "1px dashed var(--border-medium)",
                  background: "var(--bg-surface-card)",
                  textAlign: "center",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: "10px",
                }}
              >
                <div
                  style={{
                    width: "42px",
                    height: "42px",
                    borderRadius: "50%",
                    background: "rgba(255,255,255,0.05)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <ShieldIcon size={20} color="var(--text-muted)" />
                </div>
                <h4 style={{ margin: 0, fontSize: "13.5px", fontWeight: 700 }}>No Broker Accounts Connected</h4>
                <p style={{ margin: 0, fontSize: "11.5px", color: "var(--text-muted)", maxWidth: "420px" }}>
                  To view your real balance, active open orders, and trade telemetry in the Cockpit, add your Binance API Key and Secret.
                </p>
                <button
                  onClick={() => setIsConnectModalOpen(true)}
                  style={{
                    marginTop: "6px",
                    background: "rgba(56, 189, 248, 0.15)",
                    border: "1px solid rgba(56, 189, 248, 0.35)",
                    color: "#38bdf8",
                    padding: "6px 14px",
                    borderRadius: "5px",
                    fontSize: "11.5px",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Enter Binance / Bybit Key Now
                </button>
              </div>
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "12px" }}>
                {connectedBrokerCreds.map((cred) => (
                  <div
                    key={cred.id}
                    style={{
                      padding: "16px",
                      borderRadius: "8px",
                      background: "var(--bg-surface-elevated)",
                      border: "1px solid var(--border-subtle)",
                      display: "flex",
                      flexDirection: "column",
                      gap: "10px",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                      <div>
                        <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)" }}>
                          {cred.provider.toUpperCase()}
                        </div>
                        <div style={{ fontSize: "10.5px", color: "var(--accent-green)", fontWeight: 600, display: "flex", alignItems: "center", gap: "4px" }}>
                          <span className="live-dot-green" />
                          <span>Real Exchange Live Sync Active</span>
                        </div>
                      </div>
                      <button
                        onClick={() => handleDeleteCredential(cred.provider)}
                        style={{
                          background: "rgba(239, 68, 68, 0.1)",
                          border: "1px solid rgba(239, 68, 68, 0.25)",
                          color: "#f87171",
                          borderRadius: "4px",
                          padding: "3px 6px",
                          fontSize: "10px",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          gap: "4px",
                        }}
                      >
                        <TrashIcon size={10} color="#f87171" />
                        <span>Revoke</span>
                      </button>
                    </div>

                    <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 10px", background: "rgba(0,0,0,0.25)", borderRadius: "4px", fontSize: "11px" }}>
                      <span style={{ color: "var(--text-muted)" }}>Masked Key:</span>
                      <span style={{ fontFamily: "monospace", color: "var(--text-primary)" }}>{cred.masked_key}</span>
                    </div>

                    <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 10px", background: "rgba(0,0,0,0.25)", borderRadius: "4px", fontSize: "11px" }}>
                      <span style={{ color: "var(--text-muted)" }}>Real USD Capital:</span>
                      <span style={{ fontWeight: 700, color: "var(--accent-green)" }}>
                        ${totalVaultBalance.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </span>
                    </div>

                    <div style={{ fontSize: "9.5px", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "5px" }}>
                      <ShieldIcon size={10} color="var(--accent-green)" />
                      <span>AES-256-GCM encrypted in user database. Zero withdrawal permission verified.</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ══════════ SECTION 2: PERSONAL AI API KEYS ══════════ */}
        {activeVaultSection === "AI_KEYS" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div>
              <h3 style={{ margin: 0, fontSize: "14px", fontWeight: 700, color: "var(--text-primary)" }}>
                Personal AI Reasoning Engine Credentials
              </h3>
              <p style={{ margin: "3px 0 0 0", fontSize: "11.5px", color: "var(--text-muted)" }}>
                Har user apne personal AI accounts ki API key yahan save karega. All agents & Copilot will deliberate exclusively on your key.
              </p>
            </div>

            {/* Input Form for Personal AI Key */}
            <div
              style={{
                padding: "20px",
                borderRadius: "8px",
                background: "var(--bg-surface-elevated)",
                border: "1px solid var(--border-subtle)",
                maxWidth: "600px",
              }}
            >
              <form onSubmit={handleSaveAiKey} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                {aiError && (
                  <div
                    style={{
                      padding: "8px 12px",
                      borderRadius: "6px",
                      background: "rgba(239, 68, 68, 0.12)",
                      border: "1px solid rgba(239, 68, 68, 0.3)",
                      color: "#f87171",
                      fontSize: "11.5px",
                    }}
                  >
                    {aiError}
                  </div>
                )}

                <div>
                  <label style={{ display: "block", fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", marginBottom: "6px" }}>
                    AI Reasoning Provider
                  </label>
                  <select
                    value={aiProvider}
                    onChange={(e) => setAiProvider(e.target.value as any)}
                    style={{
                      width: "100%",
                      padding: "8px 10px",
                      borderRadius: "6px",
                      background: "var(--bg-surface-elevated)",
                      border: "1px solid var(--border-subtle)",
                      color: "var(--text-primary)",
                      fontSize: "12px",
                      outline: "none",
                    }}
                  >
                    <option value="groq">Groq LPU (Ultra-Low Latency 120ms • Recommended)</option>
                    <option value="openai">OpenAI (GPT-4o / O1 Reasoning)</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", marginBottom: "6px" }}>
                    Personal {aiProvider.toUpperCase()} API Key
                  </label>
                  <input
                    type="password"
                    required
                    placeholder={aiProvider === "groq" ? "gsk_••••••••••••••••••••••••••••••••" : "sk-••••••••••••••••••••••••••••••••"}
                    value={inputAiKey}
                    onChange={(e) => setInputAiKey(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "9px 12px",
                      borderRadius: "6px",
                      background: "var(--bg-surface-elevated)",
                      border: "1px solid var(--border-subtle)",
                      color: "var(--text-primary)",
                      fontSize: "12px",
                      outline: "none",
                      fontFamily: "monospace",
                    }}
                  />
                </div>

                <div
                  style={{
                    padding: "8px 12px",
                    borderRadius: "6px",
                    background: "rgba(168, 85, 247, 0.08)",
                    border: "1px solid rgba(168, 85, 247, 0.2)",
                    fontSize: "11px",
                    color: "var(--text-muted)",
                  }}
                >
                  <strong style={{ color: "#d8b4fe" }}>Database Encryption:</strong> Your key is verified live with {aiProvider.toUpperCase()}, then encrypted using AES-256-GCM. Decryption happens strictly in-memory during agent deliberation.
                </div>

                <button
                  type="submit"
                  disabled={isSavingAiKey}
                  style={{
                    background: "linear-gradient(135deg, #a855f7 0%, #7c3aed 100%)",
                    border: "none",
                    borderRadius: "6px",
                    padding: "9px 14px",
                    color: "#fff",
                    fontSize: "12px",
                    fontWeight: 700,
                    cursor: isSavingAiKey ? "not-allowed" : "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "6px",
                  }}
                >
                  {isSavingAiKey ? "Verifying & Encrypting..." : "Verify & Save Personal AI Key"}
                </button>
              </form>
            </div>

            {/* Display Active AI Credentials */}
            <div>
              <h4 style={{ margin: "0 0 10px 0", fontSize: "13px", fontWeight: 700 }}>Active Stored AI Keys</h4>
              {connectedAiCreds.length === 0 ? (
                <div style={{ fontSize: "11.5px", color: "var(--text-muted)" }}>
                  No AI key stored yet. Enter your Groq API key above to activate 24/7 AI Deliberation and Copilot.
                </div>
              ) : (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "10px" }}>
                  {connectedAiCreds.map((cred) => (
                    <div
                      key={cred.id}
                      style={{
                        padding: "14px",
                        borderRadius: "8px",
                        background: "var(--bg-surface-elevated)",
                        border: "1px solid var(--border-subtle)",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <div>
                        <div style={{ fontSize: "12.5px", fontWeight: 700 }}>{cred.provider.toUpperCase()} Engine</div>
                        <div style={{ fontSize: "11px", color: "var(--text-muted)", fontFamily: "monospace" }}>{cred.masked_key}</div>
                      </div>
                      <button
                        onClick={() => handleDeleteCredential(cred.provider)}
                        style={{
                          background: "rgba(239, 68, 68, 0.1)",
                          border: "1px solid rgba(239, 68, 68, 0.25)",
                          color: "#f87171",
                          borderRadius: "4px",
                          padding: "3px 8px",
                          fontSize: "10px",
                          cursor: "pointer",
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ══════════ SECTION 3: CHANNELS & BROADCASTS ══════════ */}
        {activeVaultSection === "CHANNELS" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <h3 style={{ margin: 0, fontSize: "14px", fontWeight: 700, color: "var(--text-primary)" }}>
                  Omnichannel Mobile Webhooks & Broadcasts
                </h3>
                <p style={{ margin: "2px 0 0 0", fontSize: "11px", color: "var(--text-muted)" }}>
                  Direct mobile phone notifications, trade approvals (reply YES/NO), and private group alerts.
                </p>
              </div>
              <button
                onClick={() => onOpenChannelSettings?.()}
                style={{
                  background: "var(--accent-green)",
                  color: "#000",
                  border: "none",
                  borderRadius: "4px",
                  padding: "6px 12px",
                  fontSize: "11px",
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                Configure WhatsApp Webhook
              </button>
            </div>

            <div
              style={{
                padding: "16px",
                borderRadius: "8px",
                background: "var(--bg-surface-elevated)",
                border: "1px solid var(--border-subtle)",
                display: "flex",
                flexDirection: "column",
                gap: "8px",
                fontSize: "11.5px",
                color: "var(--text-muted)",
              }}
            >
              <div><strong style={{ color: "var(--text-primary)" }}>Webhook URL:</strong> <code>https://your-domain/api/channels/whatsapp</code></div>
              <div><strong style={{ color: "var(--text-primary)" }}>Supported Actions on Mobile:</strong> Reply <code>YES</code> to execute trade, <code>NO</code> to cancel, <code>STATUS</code> for portfolio, <code>BTC</code> for price, or ask any question in Roman Urdu / English.</div>
            </div>
          </div>
        )}
      </div>

      {/* ═══════════ CONNECT BROKER MODAL ═══════════ */}
      {isConnectModalOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.6)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
            padding: "16px",
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget) setIsConnectModalOpen(false);
          }}
        >
          <div
            style={{
              width: "100%",
              maxWidth: "480px",
              background: "var(--bg-surface)",
              border: "1px solid var(--border-medium)",
              borderRadius: "10px",
              boxShadow: "var(--card-shadow)",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                padding: "14px 18px",
                borderBottom: "1px solid var(--border-subtle)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <ShieldIcon size={16} color="var(--accent-green)" />
                <span style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)" }}>Connect Real Exchange Account</span>
              </div>
              <button
                onClick={() => setIsConnectModalOpen(false)}
                style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
              >
                <CloseIcon size={16} />
              </button>
            </div>

            <form onSubmit={handleSaveBrokerConnection} style={{ padding: "18px", display: "flex", flexDirection: "column", gap: "12px" }}>
              {brokerError && (
                <div
                  style={{
                    padding: "8px 12px",
                    borderRadius: "6px",
                    background: "rgba(239, 68, 68, 0.12)",
                    border: "1px solid rgba(239, 68, 68, 0.3)",
                    color: "#f87171",
                    fontSize: "11.5px",
                  }}
                >
                  {brokerError}
                </div>
              )}

              <div>
                <label style={{ display: "block", fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", marginBottom: "4px" }}>
                  Exchange Platform
                </label>
                <select
                  value={selectedExchangeName}
                  onChange={(e) => setSelectedExchangeName(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 10px",
                    borderRadius: "6px",
                    background: "var(--bg-surface-elevated)",
                    border: "1px solid var(--border-subtle)",
                    color: "var(--text-primary)",
                    fontSize: "12px",
                    outline: "none",
                  }}
                >
                  <option value="Binance">Binance (Spot & US-M Futures • Real Live Sync)</option>
                  <option value="Bybit">Bybit (Unified Trading Account)</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", marginBottom: "4px" }}>
                  Exchange API Key
                </label>
                <input
                  type="password"
                  required
                  placeholder="Paste your exchange API key"
                  value={inputApiKey}
                  onChange={(e) => setInputApiKey(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "6px",
                    background: "var(--bg-surface-elevated)",
                    border: "1px solid var(--border-subtle)",
                    color: "var(--text-primary)",
                    fontSize: "12px",
                    outline: "none",
                    fontFamily: "monospace",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", marginBottom: "4px" }}>
                  Exchange API Secret
                </label>
                <input
                  type="password"
                  required
                  placeholder="Paste your exchange API secret"
                  value={inputApiSecret}
                  onChange={(e) => setInputApiSecret(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "6px",
                    background: "var(--bg-surface-elevated)",
                    border: "1px solid var(--border-subtle)",
                    color: "var(--text-primary)",
                    fontSize: "12px",
                    outline: "none",
                    fontFamily: "monospace",
                  }}
                />
              </div>

              <div
                style={{
                  padding: "8px 12px",
                  borderRadius: "6px",
                  background: "rgba(34, 197, 94, 0.08)",
                  border: "1px solid rgba(34, 197, 94, 0.2)",
                  fontSize: "10.5px",
                  color: "var(--text-muted)",
                }}
              >
                <strong style={{ color: "var(--accent-green)" }}>Safety Requirement:</strong> Ensure "Withdrawal" permission is <strong>UNCHECKED</strong> on your exchange API key. Enable only "Read" and "Spot/Futures Trading".
              </div>

              <button
                type="submit"
                disabled={isSavingBroker}
                style={{
                  marginTop: "6px",
                  background: "var(--accent-green)",
                  color: "#000",
                  border: "none",
                  borderRadius: "6px",
                  padding: "10px",
                  fontSize: "12px",
                  fontWeight: 700,
                  cursor: isSavingBroker ? "not-allowed" : "pointer",
                }}
              >
                {isSavingBroker ? "Verifying Live Exchange Connection..." : "Verify & Encrypt Real Broker Key"}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
