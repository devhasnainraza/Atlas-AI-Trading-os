"use client";

import React, { useState } from "react";
import {
  ChannelConfig,
  DEFAULT_CHANNEL_CONFIG,
  ChannelDispatchResult,
} from "../lib/channelService";
import { soundManager } from "../lib/soundEffects";
import {
  ShieldIcon,
  ZapIcon,
  CheckIcon,
  AlertTriangleIcon,
  CloseIcon,
  SendIcon,
} from "./Icons";

interface OmnichannelSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function OmnichannelSettingsModal({
  isOpen,
  onClose,
}: OmnichannelSettingsModalProps) {
  const [config, setConfig] = useState<ChannelConfig>(DEFAULT_CHANNEL_CONFIG);
  const [activeTab, setActiveTab] = useState<"WHATSAPP" | "TELEGRAM" | "DISCORD" | "TWITTER">("WHATSAPP");
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<ChannelDispatchResult | null>(null);
  const [copiedWebhook, setCopiedWebhook] = useState(false);
  const [showMetaToken, setShowMetaToken] = useState(false);

  // Load saved channel credentials from localStorage on mount
  React.useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("atlas_channel_config");
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          setConfig((prev) => ({
            ...prev,
            ...parsed,
            whatsapp: {
              ...prev.whatsapp,
              ...(parsed.whatsapp || {}),
            },
          }));
        } catch {
          // ignore parsing error
        }
      }
    }
  }, []);

  const updateConfig = (newCfg: ChannelConfig) => {
    setConfig(newCfg);
    if (typeof window !== "undefined") {
      try {
        localStorage.setItem("atlas_channel_config", JSON.stringify(newCfg));
      } catch {
        // ignore storage errors
      }
    }
  };

  if (!isOpen) return null;

  const currentHost = typeof window !== "undefined" ? window.location.origin : "http://localhost:3000";
  const whatsappWebhookUrl = `${currentHost}/api/channels/whatsapp`;
  const telegramWebhookUrl = `${currentHost}/api/channels/telegram`;

  const handleCopyWebhook = (url: string) => {
    navigator.clipboard?.writeText(url);
    setCopiedWebhook(true);
    soundManager.playClick();
    setTimeout(() => setCopiedWebhook(false), 2500);
  };

  const handleTestChannel = async (channelType: "WHATSAPP" | "TELEGRAM" | "DISCORD" | "TWITTER") => {
    setIsTesting(true);
    setTestResult(null);
    soundManager.playClick();

    // Persist current config before testing
    if (typeof window !== "undefined") {
      try {
        localStorage.setItem("atlas_channel_config", JSON.stringify(config));
      } catch {}
    }

    try {
      const res = await fetch("/api/channels/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          channel: channelType,
          config,
        }),
      });

      const data = await res.json();
      setTestResult(data);

      if (data.success) {
        soundManager.playOrderFilled();
      } else {
        soundManager.playErrorBeep();
      }
    } catch (err: any) {
      setTestResult({
        channel: channelType,
        success: false,
        message: err.message || "Failed to reach backend test route.",
      });
      soundManager.playErrorBeep();
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: "rgba(0, 0, 0, 0.6)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1100,
        padding: "12px",
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: "var(--bg-surface)",
          border: "1px solid var(--border-medium)",
          borderRadius: "8px",
          padding: "16px",
          width: "min(560px, calc(100vw - 20px))",
          boxShadow: "var(--card-shadow)",
          display: "flex",
          flexDirection: "column",
          gap: "14px",
          maxHeight: "90vh",
          overflowY: "auto",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <ZapIcon size={16} color="var(--accent-green)" />
            <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)" }}>
              Live Omnichannel Integrations (Real Phone & Webhooks)
            </span>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              cursor: "pointer",
              color: "var(--text-muted)",
            }}
          >
            <CloseIcon size={14} color="var(--text-muted)" />
          </button>
        </div>

        {/* Channel Selector Segmented Tabs */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))",
            gap: "4px",
            background: "var(--bg-surface-elevated)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "5px",
            padding: "3px",
          }}
        >
          <button
            type="button"
            onClick={() => {
              soundManager.playClick();
              setActiveTab("WHATSAPP");
              setTestResult(null);
            }}
            style={{
              background: activeTab === "WHATSAPP" ? "var(--bg-surface-card)" : "transparent",
              color: activeTab === "WHATSAPP" ? "var(--text-primary)" : "var(--text-muted)",
              boxShadow: activeTab === "WHATSAPP" ? "0 1px 3px rgba(0,0,0,0.08)" : "none",
              border: "none",
              borderRadius: "3px",
              padding: "6px 0",
              fontSize: "10.5px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            WhatsApp (Real)
          </button>
          <button
            type="button"
            onClick={() => {
              soundManager.playClick();
              setActiveTab("TELEGRAM");
              setTestResult(null);
            }}
            style={{
              background: activeTab === "TELEGRAM" ? "var(--bg-surface-card)" : "transparent",
              color: activeTab === "TELEGRAM" ? "var(--text-primary)" : "var(--text-muted)",
              boxShadow: activeTab === "TELEGRAM" ? "0 1px 3px rgba(0,0,0,0.08)" : "none",
              border: "none",
              borderRadius: "3px",
              padding: "6px 0",
              fontSize: "10.5px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Telegram Bot
          </button>
          <button
            type="button"
            onClick={() => {
              soundManager.playClick();
              setActiveTab("DISCORD");
              setTestResult(null);
            }}
            style={{
              background: activeTab === "DISCORD" ? "var(--bg-surface-card)" : "transparent",
              color: activeTab === "DISCORD" ? "var(--text-primary)" : "var(--text-muted)",
              boxShadow: activeTab === "DISCORD" ? "0 1px 3px rgba(0,0,0,0.08)" : "none",
              border: "none",
              borderRadius: "3px",
              padding: "6px 0",
              fontSize: "10.5px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Discord Channel
          </button>
          <button
            type="button"
            onClick={() => {
              soundManager.playClick();
              setActiveTab("TWITTER");
              setTestResult(null);
            }}
            style={{
              background: activeTab === "TWITTER" ? "var(--bg-surface-card)" : "transparent",
              color: activeTab === "TWITTER" ? "var(--text-primary)" : "var(--text-muted)",
              boxShadow: activeTab === "TWITTER" ? "0 1px 3px rgba(0,0,0,0.08)" : "none",
              border: "none",
              borderRadius: "3px",
              padding: "6px 0",
              fontSize: "10.5px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Twitter / X
          </button>
        </div>

        {/* TAB 1: REAL WHATSAPP INTEGRATION */}
        {activeTab === "WHATSAPP" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <div style={{ fontSize: "11px", color: "var(--text-secondary)", lineHeight: "16px" }}>
              Connect your actual physical phone to Atlas AI. When you text your WhatsApp bot or reply <strong>"YES"</strong>, our backend webhook receives it in real-time.
            </div>

            <div>
              <label style={{ fontSize: "10.5px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                WhatsApp Gateway Provider
              </label>
              <select
                value={config.whatsapp.provider}
                onChange={(e) =>
                  updateConfig({
                    ...config,
                    whatsapp: { ...config.whatsapp, provider: e.target.value as any },
                  })
                }
                style={{
                  width: "100%",
                  background: "var(--bg-surface-elevated)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "4px",
                  color: "var(--text-primary)",
                  padding: "6px 8px",
                  fontSize: "11px",
                }}
              >
                <option value="TWILIO">Twilio WhatsApp API (Easiest / Sandbox Available)</option>
                <option value="META_CLOUD">Meta Cloud API (Official WhatsApp Business Platform)</option>
              </select>
            </div>

            {config.whatsapp.provider === "META_CLOUD" ? (
              <>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 220px), 1fr))", gap: "8px" }}>
                  <div>
                    <label style={{ fontSize: "10px", color: "var(--text-muted)", display: "block", marginBottom: "3px" }}>
                      Meta Phone Number ID
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. 1241071022432173"
                      value={config.whatsapp.metaPhoneNumberId || ""}
                      onChange={(e) =>
                        updateConfig({
                          ...config,
                          whatsapp: { ...config.whatsapp, metaPhoneNumberId: e.target.value },
                        })
                      }
                      style={{
                        width: "100%",
                        background: "var(--bg-surface-elevated)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "4px",
                        color: "var(--text-primary)",
                        padding: "6px 8px",
                        fontSize: "11px",
                        fontFamily: "monospace",
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ fontSize: "10px", color: "var(--text-muted)", display: "block", marginBottom: "3px" }}>
                      WhatsApp Business Account ID
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. 1636031451262320"
                      value={config.whatsapp.metaBusinessAccountId || ""}
                      onChange={(e) =>
                        updateConfig({
                          ...config,
                          whatsapp: { ...config.whatsapp, metaBusinessAccountId: e.target.value },
                        })
                      }
                      style={{
                        width: "100%",
                        background: "var(--bg-surface-elevated)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "4px",
                        color: "var(--text-primary)",
                        padding: "6px 8px",
                        fontSize: "11px",
                        fontFamily: "monospace",
                      }}
                    />
                  </div>
                </div>

                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "3px" }}>
                    <label style={{ fontSize: "10px", color: "var(--text-muted)" }}>
                      Meta System User Access Token
                    </label>
                    <button
                      type="button"
                      onClick={() => setShowMetaToken(!showMetaToken)}
                      style={{
                        background: "transparent",
                        border: "none",
                        color: "var(--accent-blue)",
                        fontSize: "9.5px",
                        cursor: "pointer",
                        padding: 0,
                      }}
                    >
                      {showMetaToken ? "Hide Token" : "Show Full Token"}
                    </button>
                  </div>
                  <input
                    type={showMetaToken ? "text" : "password"}
                    placeholder="EAA..."
                    value={config.whatsapp.metaAccessToken || ""}
                    onChange={(e) =>
                      updateConfig({
                        ...config,
                        whatsapp: { ...config.whatsapp, metaAccessToken: e.target.value },
                      })
                    }
                    style={{
                      width: "100%",
                      background: "var(--bg-surface-elevated)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "4px",
                      color: "var(--text-primary)",
                      padding: "6px 8px",
                      fontSize: "11px",
                      fontFamily: "monospace",
                    }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: "10px", color: "var(--text-muted)", display: "block", marginBottom: "3px" }}>
                    Your Personal WhatsApp Phone Number (with Country Code)
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. +923192004088"
                    value={config.whatsapp.userPhoneNumber || ""}
                    onChange={(e) =>
                      updateConfig({
                        ...config,
                        whatsapp: { ...config.whatsapp, userPhoneNumber: e.target.value },
                      })
                    }
                    style={{
                      width: "100%",
                      background: "var(--bg-surface-elevated)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "4px",
                      color: "var(--text-primary)",
                      padding: "6px 8px",
                      fontSize: "11px",
                    }}
                  />
                </div>
              </>
            ) : (
              <>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 220px), 1fr))", gap: "8px" }}>
                  <div>
                    <label style={{ fontSize: "10px", color: "var(--text-muted)", display: "block", marginBottom: "3px" }}>
                      Twilio Account SID
                    </label>
                    <input
                      type="text"
                      placeholder="ACxxxxxxxxxxxxxxxx"
                      value={config.whatsapp.accountSid}
                      onChange={(e) =>
                        setConfig({
                          ...config,
                          whatsapp: { ...config.whatsapp, accountSid: e.target.value },
                        })
                      }
                      style={{
                        width: "100%",
                        background: "var(--bg-surface-elevated)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "4px",
                        color: "var(--text-primary)",
                        padding: "6px 8px",
                        fontSize: "11px",
                        fontFamily: "monospace",
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ fontSize: "10px", color: "var(--text-muted)", display: "block", marginBottom: "3px" }}>
                      Twilio Auth Token
                    </label>
                    <input
                      type="password"
                      placeholder="Enter Auth Token..."
                      value={config.whatsapp.authToken}
                      onChange={(e) =>
                        setConfig({
                          ...config,
                          whatsapp: { ...config.whatsapp, authToken: e.target.value },
                        })
                      }
                      style={{
                        width: "100%",
                        background: "var(--bg-surface-elevated)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "4px",
                        color: "var(--text-primary)",
                        padding: "6px 8px",
                        fontSize: "11px",
                        fontFamily: "monospace",
                      }}
                    />
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 220px), 1fr))", gap: "8px" }}>
                  <div>
                    <label style={{ fontSize: "10px", color: "var(--text-muted)", display: "block", marginBottom: "3px" }}>
                      Twilio WhatsApp Number
                    </label>
                    <input
                      type="text"
                      placeholder="+14155238886"
                      value={config.whatsapp.fromNumber}
                      onChange={(e) =>
                        setConfig({
                          ...config,
                          whatsapp: { ...config.whatsapp, fromNumber: e.target.value },
                        })
                      }
                      style={{
                        width: "100%",
                        background: "var(--bg-surface-elevated)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "4px",
                        color: "var(--text-primary)",
                        padding: "6px 8px",
                        fontSize: "11px",
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ fontSize: "10px", color: "var(--text-muted)", display: "block", marginBottom: "3px" }}>
                      Your Personal Phone Number
                    </label>
                    <input
                      type="text"
                      placeholder="+923001234567"
                      value={config.whatsapp.userPhoneNumber}
                      onChange={(e) =>
                        setConfig({
                          ...config,
                          whatsapp: { ...config.whatsapp, userPhoneNumber: e.target.value },
                        })
                      }
                      style={{
                        width: "100%",
                        background: "var(--bg-surface-elevated)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "4px",
                        color: "var(--text-primary)",
                        padding: "6px 8px",
                        fontSize: "11px",
                      }}
                    />
                  </div>
                </div>
              </>
            )}

            {/* Inbound Webhook Helper */}
            <div
              style={{
                background: "var(--bg-surface-elevated)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "4px",
                padding: "8px 10px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <div>
                <div style={{ fontSize: "10px", fontWeight: 600, color: "#f8fafc" }}>
                  Your Inbound Webhook Endpoint
                </div>
                <div style={{ fontSize: "9.5px", color: "var(--text-muted)", fontFamily: "monospace" }}>
                  {whatsappWebhookUrl}
                </div>
              </div>
              <button
                type="button"
                onClick={() => handleCopyWebhook(whatsappWebhookUrl)}
                style={{
                  background: "var(--bg-surface-card)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "3px",
                  color: copiedWebhook ? "var(--accent-green)" : "var(--text-secondary)",
                  padding: "2px 7px",
                  fontSize: "9.5px",
                  cursor: "pointer",
                }}
              >
                {copiedWebhook ? "Copied" : "Copy Webhook"}
              </button>
            </div>

            {/* Test Ping Button */}
            <button
              type="button"
              disabled={isTesting}
              onClick={() => handleTestChannel("WHATSAPP")}
              style={{
                background: "var(--accent-green)",
                border: "none",
                color: "#05070a",
                borderRadius: "4px",
                padding: "8px 0",
                fontSize: "11px",
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              {isTesting ? "DISPATCHING REAL WHATSAPP PING..." : "SEND TEST PING TO MY REAL WHATSAPP"}
            </button>
          </div>
        )}

        {/* TAB 2: TELEGRAM BOT INTEGRATION */}
        {activeTab === "TELEGRAM" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <div style={{ fontSize: "11px", color: "var(--text-secondary)", lineHeight: "16px" }}>
              Telegram takes <strong>60 seconds to setup for free</strong> (no Twilio required!). Create a bot on Telegram via <strong>@BotFather</strong>, paste token below, and receive instant interactive <strong>[YES] / [NO]</strong> trade proposals on mobile!
            </div>

            <div>
              <label style={{ fontSize: "10px", color: "var(--text-muted)", display: "block", marginBottom: "3px" }}>
                Telegram Bot Token (from @BotFather)
              </label>
              <input
                type="password"
                placeholder="123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ..."
                value={config.telegram.botToken}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    telegram: { ...config.telegram, botToken: e.target.value },
                  })
                }
                style={{
                  width: "100%",
                  background: "var(--bg-surface-elevated)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "4px",
                  color: "var(--text-primary)",
                  padding: "6px 8px",
                  fontSize: "11px",
                  fontFamily: "monospace",
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: "10px", color: "var(--text-muted)", display: "block", marginBottom: "3px" }}>
                Your Telegram Chat ID (from @userinfobot)
              </label>
              <input
                type="text"
                placeholder="e.g. 987654321"
                value={config.telegram.chatId}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    telegram: { ...config.telegram, chatId: e.target.value },
                  })
                }
                style={{
                  width: "100%",
                  background: "var(--bg-surface-elevated)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "4px",
                  color: "var(--text-primary)",
                  padding: "6px 8px",
                  fontSize: "11px",
                }}
              />
            </div>

            {/* Telegram Webhook Helper */}
            <div
              style={{
                background: "var(--bg-surface-elevated)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "4px",
                padding: "8px 10px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <div>
                <div style={{ fontSize: "10px", fontWeight: 600, color: "#f8fafc" }}>
                  Telegram Webhook Route
                </div>
                <div style={{ fontSize: "9.5px", color: "var(--text-muted)", fontFamily: "monospace" }}>
                  {telegramWebhookUrl}
                </div>
              </div>
              <button
                type="button"
                onClick={() => handleCopyWebhook(telegramWebhookUrl)}
                style={{
                  background: "var(--bg-surface-card)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "3px",
                  color: copiedWebhook ? "var(--accent-green)" : "var(--text-secondary)",
                  padding: "2px 7px",
                  fontSize: "9.5px",
                  cursor: "pointer",
                }}
              >
                {copiedWebhook ? "Copied" : "Copy"}
              </button>
            </div>

            <button
              type="button"
              disabled={isTesting}
              onClick={() => handleTestChannel("TELEGRAM")}
              style={{
                background: "var(--accent-green)",
                border: "none",
                color: "#05070a",
                borderRadius: "4px",
                padding: "8px 0",
                fontSize: "11px",
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              {isTesting ? "SENDING TO TELEGRAM..." : "SEND TEST MESSAGE TO MY TELEGRAM"}
            </button>
          </div>
        )}

        {/* TAB 3: DISCORD WEBHOOK INTEGRATION */}
        {activeTab === "DISCORD" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <div style={{ fontSize: "11px", color: "var(--text-secondary)", lineHeight: "16px" }}>
              Get automated multi-agent deliberation alerts, macro catalysts, and trade debriefs delivered straight to your private Discord server.
            </div>

            <div>
              <label style={{ fontSize: "10px", color: "var(--text-muted)", display: "block", marginBottom: "3px" }}>
                Discord Webhook URL (from Channel Settings &rarr; Integrations &rarr; Webhooks)
              </label>
              <input
                type="text"
                placeholder="https://discord.com/api/webhooks/..."
                value={config.discord.webhookUrl}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    discord: { ...config.discord, webhookUrl: e.target.value },
                  })
                }
                style={{
                  width: "100%",
                  background: "var(--bg-surface-elevated)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "4px",
                  color: "var(--text-primary)",
                  padding: "6px 8px",
                  fontSize: "11px",
                  fontFamily: "monospace",
                }}
              />
            </div>

            <button
              type="button"
              disabled={isTesting}
              onClick={() => handleTestChannel("DISCORD")}
              style={{
                background: "var(--accent-green)",
                border: "none",
                color: "#05070a",
                borderRadius: "4px",
                padding: "8px 0",
                fontSize: "11px",
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              {isTesting ? "POSTING DISCORD EMBED..." : "SEND TEST EMBED TO MY DISCORD CHANNEL"}
            </button>
          </div>
        )}

        {/* TAB 4: TWITTER / X INTEGRATION */}
        {activeTab === "TWITTER" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <div style={{ fontSize: "11px", color: "var(--text-secondary)", lineHeight: "16px" }}>
              Authorizes the Chief Manager Agent to publish sanitized market structure recaps and technical analysis directly to your Twitter / X feed.
            </div>

            <div>
              <label style={{ fontSize: "10px", color: "var(--text-muted)", display: "block", marginBottom: "3px" }}>
                Twitter / X API Bearer Token
              </label>
              <input
                type="password"
                placeholder="Enter Twitter Bearer Token..."
                value={config.twitter.bearerToken}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    twitter: { ...config.twitter, bearerToken: e.target.value },
                  })
                }
                style={{
                  width: "100%",
                  background: "var(--bg-surface-elevated)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "4px",
                  color: "var(--text-primary)",
                  padding: "6px 8px",
                  fontSize: "11px",
                  fontFamily: "monospace",
                }}
              />
            </div>

            <div
              style={{
                background: "var(--bg-surface-elevated)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "4px",
                padding: "8px 10px",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <ShieldIcon size={14} color="var(--accent-green)" />
              <div style={{ fontSize: "9.5px", color: "var(--text-muted)" }}>
                Privacy Sanitization Guard guarantees your account dollar balance is stripped before posting.
              </div>
            </div>
          </div>
        )}

        {/* Live Test Result Banner */}
        {testResult && (
          <div
            style={{
              background: testResult.success ? "var(--accent-green-subtle)" : "var(--accent-red-subtle)",
              border: `1px solid ${testResult.success ? "var(--accent-green-border)" : "var(--accent-red-border)"}`,
              borderRadius: "4px",
              padding: "10px",
              fontSize: "11px",
              color: testResult.success ? "var(--accent-green)" : "var(--accent-red)",
              display: "flex",
              alignItems: "flex-start",
              gap: "8px",
            }}
          >
            {testResult.success ? <CheckIcon size={14} color="var(--accent-green)" /> : <AlertTriangleIcon size={14} color="var(--accent-red)" />}
            <div>
              <strong>{testResult.success ? "Connection Verified!" : "Connection Failed"}</strong>
              <div style={{ fontSize: "10px", marginTop: "2px" }}>{testResult.message}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
