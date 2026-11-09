"use client";

import React, { useState } from "react";
import { soundManager } from "../lib/soundEffects";
import { AtlasEmblem } from "./AtlasLogo";
import { ShieldIcon, CloseIcon, ZapIcon, CheckIcon, AlertTriangleIcon, LockIcon } from "./Icons";

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  createdAt: string;
}

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (user: AuthUser) => void;
}

export function AuthModal({ isOpen, onClose, onSuccess }: AuthModalProps) {
  const [mode, setMode] = useState<"LOGIN" | "REGISTER">("LOGIN");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleFillDemo = () => {
    soundManager.playClick();
    setEmail("quant.lead@atlas-ai.internal");
    setPassword("AtlasQuant2026!Secure");
    if (mode === "REGISTER") {
      setName("Atlas Lead Quant");
    }
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    soundManager.playClick();

    const endpoint = mode === "REGISTER" ? "/api/auth/register" : "/api/auth/login";
    const payload = mode === "REGISTER" ? { email, password, name } : { email, password };

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.error || "Authentication failed. Verify credentials.");
        soundManager.playErrorBeep();
      } else {
        soundManager.playOrderFilled();
        onSuccess(data.user);
        onClose();
      }
    } catch (err: any) {
      setError(err.message || "Network error connecting to auth server.");
      soundManager.playErrorBeep();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "var(--modal-backdrop)",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        padding: "16px",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "460px",
          background: "var(--bg-surface)",
          border: "1px solid var(--border-medium)",
          borderRadius: "14px",
          boxShadow: "0 24px 60px rgba(0, 0, 0, 0.2), 0 0 1px 1px var(--border-highlight)",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          position: "relative",
        }}
      >
        {/* Top Accent Gradient Border */}
        <div
          style={{
            height: "3px",
            background: "linear-gradient(90deg, #38bdf8 0%, #2563eb 50%, #10b981 100%)",
            width: "100%",
          }}
        />

        {/* Modal Header */}
        <div
          style={{
            padding: "20px 24px 16px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            background: "var(--bg-surface)",
            borderBottom: "1px solid var(--border-subtle)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div
              style={{
                width: "42px",
                height: "42px",
                borderRadius: "10px",
                background: "var(--bg-surface-elevated)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                border: "1px solid var(--border-subtle)",
                boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
              }}
            >
              <AtlasEmblem size={28} glow={true} />
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <h3 style={{ fontSize: "16px", fontWeight: 800, color: "var(--text-primary)", margin: 0, letterSpacing: "-0.01em" }}>
                  {mode === "LOGIN" ? "Atlas Sovereign Sign In" : "Register Quant Account"}
                </h3>
              </div>
              <p style={{ fontSize: "11.5px", color: "var(--text-muted)", margin: "3px 0 0", lineHeight: 1.4 }}>
                Zero-trust authentication &amp; encrypted KMS session vault
              </p>
            </div>
          </div>

          <button
            onClick={() => {
              soundManager.playClick();
              onClose();
            }}
            style={{
              background: "var(--bg-surface-elevated)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "6px",
              color: "var(--text-muted)",
              cursor: "pointer",
              padding: "6px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
            title="Close (Esc)"
          >
            <CloseIcon size={14} />
          </button>
        </div>

        {/* Segmented Capsule Switcher */}
        <div style={{ padding: "12px 24px 0", background: "var(--bg-surface)" }}>
          <div
            style={{
              display: "flex",
              background: "var(--bg-surface-elevated)",
              borderRadius: "8px",
              padding: "3px",
              border: "1px solid var(--border-subtle)",
            }}
          >
            <button
              type="button"
              onClick={() => {
                soundManager.playClick();
                setMode("LOGIN");
                setError(null);
              }}
              style={{
                flex: 1,
                padding: "8px 0",
                background: mode === "LOGIN" ? "var(--bg-surface)" : "transparent",
                border: mode === "LOGIN" ? "1px solid var(--border-subtle)" : "1px solid transparent",
                borderRadius: "6px",
                color: mode === "LOGIN" ? "var(--accent-blue)" : "var(--text-muted)",
                fontSize: "12px",
                fontWeight: mode === "LOGIN" ? 700 : 500,
                cursor: "pointer",
                boxShadow: mode === "LOGIN" ? "0 1px 3px rgba(0,0,0,0.06)" : "none",
                transition: "all 0.15s ease",
              }}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                soundManager.playClick();
                setMode("REGISTER");
                setError(null);
              }}
              style={{
                flex: 1,
                padding: "8px 0",
                background: mode === "REGISTER" ? "var(--bg-surface)" : "transparent",
                border: mode === "REGISTER" ? "1px solid var(--border-subtle)" : "1px solid transparent",
                borderRadius: "6px",
                color: mode === "REGISTER" ? "var(--accent-blue)" : "var(--text-muted)",
                fontSize: "12px",
                fontWeight: mode === "REGISTER" ? 700 : 500,
                cursor: "pointer",
                boxShadow: mode === "REGISTER" ? "0 1px 3px rgba(0,0,0,0.06)" : "none",
                transition: "all 0.15s ease",
              }}
            >
              Register New Desk
            </button>
          </div>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} style={{ padding: "16px 24px 24px", display: "flex", flexDirection: "column", gap: "14px" }}>
          {/* Error Banner */}
          {error && (
            <div
              style={{
                padding: "10px 12px",
                borderRadius: "6px",
                background: "rgba(239, 68, 68, 0.1)",
                border: "1px solid rgba(239, 68, 68, 0.3)",
                color: "#ef4444",
                fontSize: "11.5px",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <AlertTriangleIcon size={14} color="#ef4444" />
              <span>{error}</span>
            </div>
          )}

          {/* Full Name field (Register only) */}
          {mode === "REGISTER" && (
            <div>
              <label style={{ display: "block", fontSize: "11px", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "5px" }}>
                LEAD TRADER / DESK NAME
              </label>
              <input
                type="text"
                required
                placeholder="Muhammad Hasnain"
                value={name}
                onChange={(e) => setName(e.target.value)}
                style={{
                  width: "100%",
                  padding: "9px 12px",
                  borderRadius: "6px",
                  background: "var(--bg-surface-elevated)",
                  border: "1px solid var(--border-subtle)",
                  color: "var(--text-primary)",
                  fontSize: "12.5px",
                  outline: "none",
                  transition: "border-color 0.15s ease",
                }}
                onFocus={(e) => (e.currentTarget.style.borderColor = "var(--accent-blue)")}
                onBlur={(e) => (e.currentTarget.style.borderColor = "var(--border-subtle)")}
              />
            </div>
          )}

          {/* Email Address */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "5px" }}>
              <label style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-secondary)" }}>
                OPERATOR EMAIL
              </label>
              <button
                type="button"
                onClick={handleFillDemo}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "var(--accent-blue)",
                  fontSize: "10.5px",
                  fontWeight: 600,
                  cursor: "pointer",
                  padding: 0,
                }}
              >
                Auto-fill Quant Demo
              </button>
            </div>
            <input
              type="email"
              required
              placeholder="trader@atlas-ai.internal"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={{
                width: "100%",
                padding: "9px 12px",
                borderRadius: "6px",
                background: "var(--bg-surface-elevated)",
                border: "1px solid var(--border-subtle)",
                color: "var(--text-primary)",
                fontSize: "12.5px",
                outline: "none",
                transition: "border-color 0.15s ease",
              }}
              onFocus={(e) => (e.currentTarget.style.borderColor = "var(--accent-blue)")}
              onBlur={(e) => (e.currentTarget.style.borderColor = "var(--border-subtle)")}
            />
          </div>

          {/* Password with Show/Hide toggle */}
          <div>
            <label style={{ display: "block", fontSize: "11px", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "5px" }}>
              SECURITY PASSPHRASE
            </label>
            <div style={{ position: "relative" }}>
              <input
                type={showPassword ? "text" : "password"}
                required
                placeholder="••••••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{
                  width: "100%",
                  padding: "9px 36px 9px 12px",
                  borderRadius: "6px",
                  background: "var(--bg-surface-elevated)",
                  border: "1px solid var(--border-subtle)",
                  color: "var(--text-primary)",
                  fontSize: "12.5px",
                  outline: "none",
                  transition: "border-color 0.15s ease",
                }}
                onFocus={(e) => (e.currentTarget.style.borderColor = "var(--accent-blue)")}
                onBlur={(e) => (e.currentTarget.style.borderColor = "var(--border-subtle)")}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: "absolute",
                  right: "10px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  background: "transparent",
                  border: "none",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                  padding: 0,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
                title={showPassword ? "Hide passphrase" : "Show passphrase"}
              >
                {showPassword ? (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                    <line x1="1" y1="1" x2="23" y2="23" />
                  </svg>
                ) : (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </div>
          </div>

          {/* Cryptographic Assurance Micro-Card */}
          <div
            style={{
              padding: "10px 12px",
              borderRadius: "8px",
              background: "var(--accent-blue-subtle)",
              border: "1px solid var(--accent-blue-border)",
              fontSize: "11px",
              color: "var(--text-secondary)",
              lineHeight: 1.5,
              display: "flex",
              alignItems: "flex-start",
              gap: "8px",
            }}
          >
            <ShieldIcon size={14} color="var(--accent-blue)" />
            <div style={{ flex: 1 }}>
              <span style={{ fontWeight: 700, color: "var(--accent-blue)" }}>
                Zero-Custody Envelope Vaulting:
              </span>{" "}
              Broker credentials &amp; API keys are never stored in plaintext or logged. All state transactions are signed with ES256 tokens and protected under constitutional Hard Veto.
            </div>
          </div>

          {/* Submit Action */}
          <button
            type="submit"
            disabled={loading}
            style={{
              marginTop: "4px",
              padding: "11px",
              borderRadius: "6px",
              background: "linear-gradient(135deg, #0284c7 0%, #2563eb 100%)",
              boxShadow: "0 4px 12px rgba(37, 99, 235, 0.25)",
              border: "none",
              color: "#ffffff",
              fontSize: "13px",
              fontWeight: 700,
              cursor: loading ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
              transition: "transform 0.1s ease, box-shadow 0.15s ease",
            }}
          >
            {loading ? (
              <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span className="live-dot-green" />
                <span>Verifying Cryptographic Identity...</span>
              </span>
            ) : mode === "LOGIN" ? (
              <>
                <ShieldIcon size={14} color="#fff" />
                <span>Sign In Securely</span>
              </>
            ) : (
              <>
                <ZapIcon size={14} color="#fff" />
                <span>Create Isolated Quant Account</span>
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
