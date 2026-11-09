"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  WhatsAppMessage,
  WhatsAppTradeProposal,
  INITIAL_WHATSAPP_CHAT,
} from "../lib/apiVault";
import { soundManager } from "../lib/soundEffects";
import { dispatchChannelAlert } from "../lib/channelService";
import {
  ShieldIcon,
  CheckIcon,
  CloseIcon,
  SendIcon,
  ZapIcon,
  AlertTriangleIcon,
} from "./Icons";

interface WhatsAppCopilotDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onExecuteTradeProposal: (proposal: WhatsAppTradeProposal) => void;
  onOpenSettings?: () => void;
  currentBtcPrice?: number;
  dailyPnlUsd?: number;
}

export function WhatsAppCopilotDrawer({
  isOpen,
  onClose,
  onExecuteTradeProposal,
  onOpenSettings,
  currentBtcPrice = 86234.0,
  dailyPnlUsd = 866.0,
}: WhatsAppCopilotDrawerProps) {
  const [messages, setMessages] = useState<WhatsAppMessage[]>(INITIAL_WHATSAPP_CHAT);
  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [isPushing, setIsPushing] = useState(false);
  const [pushSuccess, setPushSuccess] = useState(false);
  const [storedPhone, setStoredPhone] = useState<string>("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    try {
      if (typeof window !== "undefined") {
        const saved = localStorage.getItem("atlas_channel_config");
        if (saved) {
          const cfg = JSON.parse(saved);
          if (cfg?.whatsapp?.userPhoneNumber) {
            setStoredPhone(cfg.whatsapp.userPhoneNumber);
          }
        }
      }
    } catch {}
  }, [isOpen]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  if (!isOpen) return null;

  const handleSendUserMessage = (textToSend?: string) => {
    const text = textToSend || inputValue.trim();
    if (!text) return;

    soundManager.playClick();
    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    const userMsg: WhatsAppMessage = {
      id: "msg-" + Date.now(),
      sender: "USER",
      timestamp: timeStr,
      text,
      status: "SENT",
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInputValue("");
    setIsTyping(true);

    // AI Response generation in Roman Urdu / English
    setTimeout(() => {
      const lower = text.toLowerCase();
      let replyText = "Bhai, market update analyse ho raha hai...";
      let newProposal: WhatsAppTradeProposal | undefined = undefined;

      if (lower.includes("btc") || lower.includes("bitcoin")) {
        replyText = `Bhai, Bitcoin abhi $${currentBtcPrice.toLocaleString()} par chal raha hai. 4H time frame par liquidity sweep confirm ho chuki hai. Bullish conviction 87% hai aur support $84,200 par solid hai.`;
      } else if (lower.includes("pnl") || lower.includes("profit") || lower.includes("loss")) {
        replyText = `Bhai, aaj ka total Realized PnL +$${dailyPnlUsd.toFixed(2)} hai. Sab running algos profit targets ko trail kar rahe hain aur Risk Gate NORMAL state mein hai.`;
      } else if (lower.includes("risk")) {
        replyText = `Risk Manager Agent ne update record kar liya hai: Max risk per trade ko 1.0% ($1,250) par strictly enforce kiya ja raha hai.`;
      } else if (lower.includes("proposal") || lower.includes("trade") || lower.includes("setup")) {
        replyText = `Bhai! Chief Manager Agent ne Binance par naya institutional setup detect kiya hai:`;
        newProposal = {
          symbol: "ETH/USDT",
          side: "LONG",
          entryPrice: 2748.0,
          targetPriceTp1: 2840.0,
          targetPriceTp2: 2950.0,
          stopLossPrice: 2690.0,
          riskUsd: 220.0,
          riskPct: 1.1,
          estRewardUsd: 620.0,
          convictionPct: 89,
          timeframe: "1H FVG Retest",
          catalyst: "1H Bullish Order Block + Spot Delta Inflow",
          exchangeName: "Binance Futures",
          status: "PENDING",
        };
      } else {
        replyText = `Bhai ji, main 24/7 market scan kar raha hoon. Agar aap chahein toh main live portfolio audit, BTC analysis, ya specific coin ka setup dhoondh kar trade proposal bhej sakta hoon.`;
      }

      const aiMsg: WhatsAppMessage = {
        id: "msg-" + Date.now(),
        sender: "ATLAS_AI",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        text: replyText,
        proposal: newProposal,
        status: "DELIVERED",
      };

      setIsTyping(false);
      setMessages((prev) => [...prev, aiMsg]);
      soundManager.playCopilotChime();

      // Dispatch to user's real WhatsApp phone!
      let waTitle = "WhatsApp AI Assistant";
      let waCategory: "TRADE_PROPOSAL" | "ALERT" = "ALERT";
      let waContent = replyText;

      if (newProposal) {
        waTitle = `NEW PROPOSAL: ${newProposal.side} ${newProposal.symbol}`;
        waCategory = "TRADE_PROPOSAL";
        waContent = `Symbol: ${newProposal.symbol} (${newProposal.side})\nEntry: $${newProposal.entryPrice}\nTarget TP1: $${newProposal.targetPriceTp1} | TP2: $${newProposal.targetPriceTp2}\nStop Loss: $${newProposal.stopLossPrice}\nRisk: $${newProposal.riskUsd} (${newProposal.riskPct}%)\nConviction: ${newProposal.convictionPct}%\nExchange: ${newProposal.exchangeName}\nCatalyst: ${newProposal.catalyst}\n\nReply "YES" to execute on your broker, or "NO" to cancel.`;
      }
      dispatchChannelAlert(waTitle, waContent, waCategory);
    }, 1200);
  };

  const handleApproveProposal = (msgId: string, proposal: WhatsAppTradeProposal) => {
    soundManager.playOrderFilled();
    onExecuteTradeProposal(proposal);

    setMessages((prev) =>
      prev.map((m) => {
        if (m.id === msgId && m.proposal) {
          return {
            ...m,
            proposal: {
              ...m.proposal,
              status: "APPROVED",
            },
          };
        }
        return m;
      })
    );

    // AI Confirmation Receipt
    setTimeout(() => {
      const confirmMsg: WhatsAppMessage = {
        id: "msg-confirm-" + Date.now(),
        sender: "ATLAS_AI",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        text: `Zabardast! Aapki ijazat se ${proposal.symbol} ${proposal.side} order $${proposal.entryPrice} par aapke ${proposal.exchangeName} account par execute ho gaya hai. Hard SL aur Auto-Breakeven rule attach kar diya gaya hai!`,
        status: "READ",
      };
      setMessages((prev) => [...prev, confirmMsg]);
      soundManager.playOrderSent();

      // Dispatch execution receipt to real WhatsApp phone
      dispatchChannelAlert(
        `TRADE EXECUTED: ${proposal.side} ${proposal.symbol}`,
        `Order executed on ${proposal.exchangeName} at $${proposal.entryPrice}.\nStop Loss: $${proposal.stopLossPrice} | Target: $${proposal.targetPriceTp1}.\nAuto-Breakeven rule armed. Capital preserved.`,
        "EXECUTION"
      );
    }, 600);
  };

  const handleRejectProposal = (msgId: string) => {
    soundManager.playClick();
    setMessages((prev) =>
      prev.map((m) => {
        if (m.id === msgId && m.proposal) {
          return {
            ...m,
            proposal: {
              ...m.proposal,
              status: "REJECTED",
            },
          };
        }
        return m;
      })
    );

    const abortMsg: WhatsAppMessage = {
      id: "msg-abort-" + Date.now(),
      sender: "ATLAS_AI",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      text: "Theek hai bhai, trade proposal ko cancel kar diya gaya hai. Capital safe hai.",
      status: "READ",
    };
    setMessages((prev) => [...prev, abortMsg]);
    soundManager.playClick();

    dispatchChannelAlert(
      `PROPOSAL CANCELLED`,
      `Trade proposal has been safely discarded. Capital remains 100% preserved.`,
      "ALERT"
    );
  };

  return (
    <div
      style={{
        position: "fixed",
        bottom: "20px",
        right: "20px",
        width: "380px",
        height: "560px",
        background: "var(--bg-surface)",
        border: "1px solid var(--border-medium)",
        borderRadius: "10px",
        boxShadow: "var(--card-shadow)",
        display: "flex",
        flexDirection: "column",
        zIndex: 1000,
        overflow: "hidden",
      }}
    >
      {/* WhatsApp Styled Header */}
      <div
        style={{
          background: "var(--bg-surface-elevated)",
          borderBottom: "1px solid var(--border-subtle)",
          padding: "10px 14px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div
            style={{
              width: "32px",
              height: "32px",
              borderRadius: "50%",
              background: "var(--bg-surface-elevated)",
              border: "1px solid var(--border-medium)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              position: "relative",
            }}
          >
            <ShieldIcon size={16} color="var(--accent-green)" />
            <span
              style={{
                position: "absolute",
                bottom: "0",
                right: "0",
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                background: "#22c55e",
                border: "1.5px solid var(--bg-surface-elevated)",
              }}
            />
          </div>

          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
              <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-primary)" }}>
                Atlas Manager Agent
              </span>
              <span
                style={{
                  background: "rgba(34, 197, 94, 0.15)",
                  color: "var(--accent-green)",
                  fontSize: "8.5px",
                  fontWeight: 700,
                  borderRadius: "2px",
                  padding: "1px 4px",
                }}
              >
                WHATSAPP BOT
              </span>
            </div>
            <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>
              24/7 Autonomous Market Vigilance
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          {onOpenSettings && (
            <button
              onClick={() => {
                soundManager.playClick();
                onOpenSettings();
              }}
              style={{
                background: "rgba(34, 197, 94, 0.15)",
                border: "1px solid rgba(34, 197, 94, 0.3)",
                color: "var(--accent-green)",
                borderRadius: "3px",
                padding: "2px 6px",
                fontSize: "9px",
                fontWeight: 600,
                cursor: "pointer",
              }}
              title="Configure real physical phone WhatsApp/Twilio connection"
            >
              Connect Real Phone
            </button>
          )}

          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
              padding: "4px",
            }}
          >
            <CloseIcon size={14} color="var(--text-muted)" />
          </button>
        </div>
      </div>

      {/* Live Physical Phone Direct Push Bar */}
      <div
        style={{
          padding: "6px 12px",
          background: "var(--bg-surface-elevated)",
          borderBottom: "1px solid var(--border-subtle)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "8px",
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span
            style={{
              width: "6px",
              height: "6px",
              borderRadius: "50%",
              background: "var(--accent-green)",
              boxShadow: "0 0 6px var(--accent-green)",
            }}
          />
          <span style={{ fontSize: "10px", color: "var(--text-secondary)" }}>
            Real Phone: <strong style={{ color: "var(--text-primary)" }}>{storedPhone || "Configured in Settings"}</strong>
          </span>
        </div>

        <button
          type="button"
          disabled={isPushing}
          onClick={async () => {
            setIsPushing(true);
            soundManager.playClick();
            await dispatchChannelAlert(
              "Live Market Vigilance Status",
              `BTC Price: $${currentBtcPrice.toLocaleString()} | Today PnL: +$${dailyPnlUsd.toFixed(2)} | Risk Gate: NORMAL | All Algos Active.`,
              "ALERT"
            );
            soundManager.playExecutionSuccess();
            setIsPushing(false);
            setPushSuccess(true);
            setTimeout(() => setPushSuccess(false), 3500);
          }}
          style={{
            background: pushSuccess ? "var(--accent-green)" : "var(--bg-surface-card)",
            color: pushSuccess ? "#05070a" : "var(--accent-green)",
            border: "1px solid var(--border-medium)",
            borderRadius: "4px",
            padding: "3px 8px",
            fontSize: "9.5px",
            fontWeight: 700,
            cursor: isPushing ? "wait" : "pointer",
            transition: "all 0.15s ease",
          }}
        >
          {isPushing ? "Pushing..." : pushSuccess ? "Delivered to WhatsApp!" : "Ping My Phone Now"}
        </button>
      </div>

      {/* Quick Action Suggestion Chips */}
      <div
        style={{
          display: "flex",
          gap: "6px",
          padding: "6px 12px",
          background: "var(--bg-surface)",
          borderBottom: "1px solid var(--border-subtle)",
          overflowX: "auto",
          whiteSpace: "nowrap",
          flexShrink: 0,
        }}
      >
        <button
          onClick={() => handleSendUserMessage("Bhai BTC ka kya scene hai?")}
          style={{
            background: "var(--bg-surface-elevated)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "12px",
            padding: "2px 8px",
            fontSize: "9.5px",
            color: "var(--text-secondary)",
            cursor: "pointer",
          }}
        >
          BTC View?
        </button>
        <button
          onClick={() => handleSendUserMessage("Aaj ka net PnL kitna hua?")}
          style={{
            background: "var(--bg-surface-elevated)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "12px",
            padding: "2px 8px",
            fontSize: "9.5px",
            color: "var(--text-secondary)",
            cursor: "pointer",
          }}
        >
          Aaj ka PnL?
        </button>
        <button
          onClick={() => handleSendUserMessage("Risk per trade 1% set kardo")}
          style={{
            background: "var(--bg-surface-elevated)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "12px",
            padding: "2px 8px",
            fontSize: "9.5px",
            color: "var(--text-secondary)",
            cursor: "pointer",
          }}
        >
          Risk 1% Lock
        </button>
        <button
          onClick={() => handleSendUserMessage("Bhai koi A+ trade proposal dhoondo")}
          style={{
            background: "rgba(34, 197, 94, 0.15)",
            border: "1px solid rgba(34, 197, 94, 0.3)",
            borderRadius: "12px",
            padding: "2px 8px",
            fontSize: "9.5px",
            color: "var(--accent-green)",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Generate Trade Proposal
        </button>
      </div>

      {/* Messages Feed */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "12px",
          display: "flex",
          flexDirection: "column",
          gap: "10px",
          background: "var(--bg-canvas)",
        }}
      >
        {messages.map((m) => {
          const isUser = m.sender === "USER";
          return (
            <div
              key={m.id}
              style={{
                alignSelf: isUser ? "flex-end" : "flex-start",
                maxWidth: "88%",
                display: "flex",
                flexDirection: "column",
                gap: "4px",
              }}
            >
              {/* Message Bubble */}
              <div
                style={{
                  background: isUser ? "var(--accent-green-subtle)" : "var(--bg-surface-card)",
                  border: isUser ? "1px solid var(--accent-green-border)" : "1px solid var(--border-subtle)",
                  borderRadius: isUser ? "10px 10px 2px 10px" : "10px 10px 10px 2px",
                  padding: "8px 11px",
                  color: "var(--text-primary)",
                  fontSize: "11px",
                  lineHeight: "16px",
                  boxShadow: "0 1px 3px rgba(0, 0, 0, 0.05)",
                }}
              >
                <div>{m.text}</div>

                {/* THE MANDATORY HUMAN CONSENT GATE CARD */}
                {m.proposal && (
                  <div
                    style={{
                      marginTop: "8px",
                      background: "var(--bg-surface-elevated)",
                      border: "1px solid rgba(34, 197, 94, 0.3)",
                      borderRadius: "6px",
                      padding: "10px",
                      display: "flex",
                      flexDirection: "column",
                      gap: "8px",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <span
                        style={{
                          background: m.proposal.side === "LONG" ? "var(--accent-green-subtle)" : "var(--accent-red-subtle)",
                          color: m.proposal.side === "LONG" ? "var(--accent-green)" : "var(--accent-red)",
                          border: "1px solid var(--border-subtle)",
                          fontSize: "9px",
                          fontWeight: 700,
                          borderRadius: "3px",
                          padding: "1px 5px",
                        }}
                      >
                        {m.proposal.side} {m.proposal.symbol}
                      </span>
                      <span style={{ fontSize: "9.5px", color: "var(--accent-green)", fontWeight: 700 }}>
                        {m.proposal.convictionPct}% Conviction
                      </span>
                    </div>

                    <div style={{ fontSize: "10px", color: "var(--text-muted)", lineHeight: "14px" }}>
                      <strong>Setup:</strong> {m.proposal.catalyst}
                    </div>

                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px", fontSize: "10px", background: "var(--bg-surface-card)", padding: "6px", borderRadius: "4px" }}>
                      <div>
                        <span style={{ color: "var(--text-muted)" }}>Entry: </span>
                        <strong className="tabular-nums" style={{ color: "var(--text-primary)" }}>${m.proposal.entryPrice}</strong>
                      </div>
                      <div>
                        <span style={{ color: "var(--text-muted)" }}>Stop-Loss: </span>
                        <strong className="tabular-nums" style={{ color: "var(--accent-red)" }}>${m.proposal.stopLossPrice}</strong>
                      </div>
                      <div>
                        <span style={{ color: "var(--text-muted)" }}>TP1 Target: </span>
                        <strong className="tabular-nums" style={{ color: "var(--accent-green)" }}>${m.proposal.targetPriceTp1}</strong>
                      </div>
                      <div>
                        <span style={{ color: "var(--text-muted)" }}>Risk / Reward: </span>
                        <strong className="tabular-nums" style={{ color: "var(--text-primary)" }}>${m.proposal.riskUsd} / ${m.proposal.estRewardUsd}</strong>
                      </div>
                    </div>

                    <div style={{ fontSize: "10.5px", fontWeight: 700, color: "var(--text-primary)", textAlign: "center", marginTop: "2px" }}>
                      Kya main aapke {m.proposal.exchangeName} par yeh trade execute kar dun?
                    </div>

                    {/* Interactive YES / NO Buttons */}
                    {m.proposal.status === "PENDING" ? (
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px", marginTop: "4px" }}>
                        <button
                          onClick={() => handleRejectProposal(m.id)}
                          style={{
                            background: "var(--bg-surface-card)",
                            border: "1px solid var(--border-medium)",
                            color: "var(--text-muted)",
                            borderRadius: "4px",
                            padding: "6px 0",
                            fontSize: "10px",
                            fontWeight: 700,
                            cursor: "pointer",
                          }}
                        >
                          NO, PASS
                        </button>
                        <button
                          onClick={() => handleApproveProposal(m.id, m.proposal!)}
                          style={{
                            background: "var(--accent-green)",
                            border: "none",
                            color: "#05070a",
                            borderRadius: "4px",
                            padding: "6px 0",
                            fontSize: "10px",
                            fontWeight: 800,
                            cursor: "pointer",
                          }}
                        >
                          YES, EXECUTE
                        </button>
                      </div>
                    ) : (
                      <div
                        style={{
                          background: m.proposal.status === "APPROVED" ? "var(--accent-green-subtle)" : "var(--accent-red-subtle)",
                          color: m.proposal.status === "APPROVED" ? "var(--accent-green)" : "var(--accent-red)",
                          border: `1px solid ${m.proposal.status === "APPROVED" ? "var(--accent-green-border)" : "var(--accent-red-border)"}`,
                          padding: "4px",
                          borderRadius: "4px",
                          textAlign: "center",
                          fontSize: "10px",
                          fontWeight: 700,
                        }}
                      >
                        {m.proposal.status === "APPROVED" ? "ORDER AUTHORIZED & EXECUTED" : "ORDER CANCELLED"}
                      </div>
                    )}
                  </div>
                )}

                <div
                  style={{
                    fontSize: "8.5px",
                    color: "var(--text-muted)",
                    textAlign: "right",
                    marginTop: "3px",
                  }}
                >
                  {m.timestamp}
                </div>
              </div>
            </div>
          );
        })}

        {isTyping && (
          <div style={{ alignSelf: "flex-start", background: "var(--bg-surface-elevated)", padding: "6px 12px", borderRadius: "10px", fontSize: "10px", color: "var(--text-muted)" }}>
            Atlas AI is formulating response...
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSendUserMessage();
        }}
        style={{
          background: "var(--bg-surface-elevated)",
          borderTop: "1px solid var(--border-subtle)",
          padding: "8px 10px",
          display: "flex",
          alignItems: "center",
          gap: "8px",
          flexShrink: 0,
        }}
      >
        <input
          type="text"
          placeholder="Message Atlas AI in Roman Urdu or English..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          style={{
            flex: 1,
            background: "var(--bg-surface-card)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "6px",
            padding: "7px 10px",
            fontSize: "11px",
            color: "var(--text-primary)",
            outline: "none",
          }}
        />
        <button
          type="submit"
          style={{
            background: "var(--accent-green)",
            border: "none",
            borderRadius: "6px",
            width: "30px",
            height: "30px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            flexShrink: 0,
          }}
        >
          <SendIcon size={13} color="#05070a" />
        </button>
      </form>
    </div>
  );
}
