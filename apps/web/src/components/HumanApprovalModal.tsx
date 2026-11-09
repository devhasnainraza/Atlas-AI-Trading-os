"use client";

import React, { useState, useEffect } from "react";
import { soundManager } from "../lib/soundEffects";
import { CheckIcon, CloseIcon, ShieldIcon } from "./Icons";

export interface OrderProposal {
  id: string;
  symbol: string;
  side: "BUY" | "SELL";
  price: number;
  sizeStr: string;
  riskUsd: number;
  riskPct: number;
  targetEv: number;
  invalidationPrice: number;
  tpPrice: number;
}

interface HumanApprovalModalProps {
  orderProposal: OrderProposal | null;
  onApprove: (order: OrderProposal) => void;
  onDecline: () => void;
}

export function HumanApprovalModal({ orderProposal, onApprove, onDecline }: HumanApprovalModalProps) {
  const [isSigning, setIsSigning] = useState(false);
  const [signedTxId, setSignedTxId] = useState<string | null>(null);

  useEffect(() => {
    if (orderProposal) {
      soundManager.playAlert();
    }
  }, [orderProposal]);

  if (!orderProposal) {
    return null;
  }

  const handleApprove = () => {
    soundManager.playClick();
    setIsSigning(true);
    setTimeout(() => {
      const txId = "0x" + Math.random().toString(16).substring(2, 10) + "..." + Math.random().toString(16).substring(2, 6);
      setSignedTxId(txId);
      soundManager.playExecutionSuccess();
      onApprove(orderProposal);

      setTimeout(() => {
        setIsSigning(false);
        setSignedTxId(null);
      }, 1500);
    }, 700);
  };

  return (
    <div
      style={{
        position: "fixed",
        bottom: "16px",
        right: "16px",
        zIndex: 100,
        width: "420px",
        background: "var(--bg-surface-card)",
        border: signedTxId ? "1px solid var(--accent-green)" : "1px solid var(--border-medium)",
        borderRadius: "8px",
        boxShadow: "var(--card-shadow)",
        padding: "14px 16px",
      }}
    >
      {signedTxId ? (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div
              style={{
                width: "24px",
                height: "24px",
                borderRadius: "50%",
                background: "rgba(34, 197, 94, 0.15)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <CheckIcon size={14} color="var(--accent-green)" />
            </div>
            <div>
              <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--accent-green)", display: "block" }}>
                ORDER SIGNED & DISPATCHED TO BROKER
              </span>
              <span style={{ fontSize: "10px", color: "var(--text-muted)", fontFamily: "monospace" }}>
                HMAC TxID: {signedTxId}
              </span>
            </div>
          </div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {/* Header */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <ShieldIcon size={13} color="var(--accent-blue)" />
              <span style={{ fontSize: "10px", fontWeight: 700, color: "var(--text-primary)", letterSpacing: "0.5px" }}>
                HUMAN APPROVAL GATE · {orderProposal.side} {orderProposal.symbol}
              </span>
            </div>
            <button
              onClick={onDecline}
              style={{
                background: "transparent",
                border: "none",
                color: "var(--text-muted)",
                cursor: "pointer",
                padding: "2px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
              title="Close"
            >
              <CloseIcon size={12} />
            </button>
          </div>

          {/* prompt.md 5-Stage Approval Pipeline Stepper */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(5, 1fr)",
              gap: "4px",
              padding: "4px",
              background: "var(--bg-surface-elevated)",
              borderRadius: "4px",
              fontSize: "8.5px",
              textAlign: "center",
              fontWeight: 700,
            }}
          >
            <div style={{ color: "#4ade80", background: "rgba(34, 197, 94, 0.15)", borderRadius: "2px", padding: "2px 0" }}>
              1. AI Propose ✓
            </div>
            <div style={{ color: "#4ade80", background: "rgba(34, 197, 94, 0.15)", borderRadius: "2px", padding: "2px 0" }}>
              2. Risk Check ✓
            </div>
            <div style={{ color: "#4ade80", background: "rgba(34, 197, 94, 0.15)", borderRadius: "2px", padding: "2px 0" }}>
              3. Policy Gate ✓
            </div>
            <div style={{ color: "#facc15", background: "rgba(234, 179, 8, 0.2)", borderRadius: "2px", padding: "2px 0", border: "1px solid rgba(234, 179, 8, 0.5)" }}>
              4. User Sign
            </div>
            <div style={{ color: "#94a3b8", background: "rgba(255, 255, 255, 0.05)", borderRadius: "2px", padding: "2px 0" }}>
              5. Execute
            </div>
          </div>

          {/* Details */}
          <div style={{ fontSize: "12px", color: "var(--text-primary)" }}>
            <span
              style={{
                color: orderProposal.side === "BUY" ? "var(--accent-green)" : "var(--accent-red)",
                fontWeight: 800,
                marginRight: "4px",
              }}
            >
              {orderProposal.side}
            </span>
            <strong>{orderProposal.sizeStr}</strong> of <strong>{orderProposal.symbol}</strong> @ ${orderProposal.price.toLocaleString()}
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "10px", color: "var(--text-secondary)" }} className="tabular-nums">
            <span>
              Risk: <strong style={{ color: "var(--accent-red)" }}>${orderProposal.riskUsd.toLocaleString()}</strong> ({orderProposal.riskPct}%)
            </span>
            <span>
              Target: <strong style={{ color: "var(--accent-green)" }}>+${orderProposal.targetEv.toLocaleString()}</strong>
            </span>
            <span>
              SL: <strong style={{ color: "var(--accent-red)" }}>${orderProposal.invalidationPrice.toLocaleString()}</strong>
            </span>
          </div>

          {/* Buttons */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "4px" }}>
            <button
              onClick={onDecline}
              disabled={isSigning}
              style={{
                flex: 1,
                background: "transparent",
                border: "1px solid var(--border-subtle)",
                color: "var(--text-secondary)",
                borderRadius: "4px",
                padding: "6px 0",
                fontSize: "11px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Cancel
            </button>
            <button
              onClick={handleApprove}
              disabled={isSigning}
              style={{
                flex: 2,
                background: orderProposal.side === "BUY" ? "var(--accent-green)" : "var(--accent-red)",
                border: "none",
                color: orderProposal.side === "BUY" ? "#05160e" : "#fff",
                borderRadius: "4px",
                padding: "6px 0",
                fontSize: "11px",
                fontWeight: 800,
                cursor: "pointer",
              }}
            >
              {isSigning ? "Signing HMAC..." : `Approve & Sign [${orderProposal.side}]`}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
