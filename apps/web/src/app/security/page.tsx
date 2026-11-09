"use client";

import React, { useState, useEffect } from "react";
import { soundManager } from "../../lib/soundEffects";
import { AtlasLogo } from "../../components/AtlasLogo";
import { ShieldIcon, LockIcon, AlertTriangleIcon, CheckIcon, ZapIcon, SunIcon, MoonIcon, ArrowRightIcon } from "../../components/Icons";

export default function SecurityPage() {
  const [theme, setTheme] = useState<"light" | "dark">("light");

  useEffect(() => {
    try {
      const saved = localStorage.getItem("atlas_theme") as "light" | "dark" | null;
      if (saved) {
        setTheme(saved);
        document.documentElement.setAttribute("data-theme", saved);
      }
    } catch {}
  }, []);

  const handleToggleTheme = () => {
    soundManager.playClick();
    setTheme((prev) => {
      const next = prev === "light" ? "dark" : "light";
      try {
        localStorage.setItem("atlas_theme", next);
        document.documentElement.setAttribute("data-theme", next);
      } catch {}
      return next;
    });
  };

  const securityPillars = [
    {
      title: "Zero-Trust Segregation of Duties",
      desc: "No single agent possesses end-to-end execution capability. Market, News, and Decision agents have strictly read/analyze scopes. Only the Execution Agent holds broker access, and is hard-gated behind cryptographic Human Signatures.",
      icon: ShieldIcon,
      badge: "CONSTITUTIONAL",
    },
    {
      title: "AES-256-GCM Envelope Encryption",
      desc: "Broker API credentials, secrets, and private keys are encrypted locally using AES-256-GCM with envelope key encryption. Key Encryption Keys (KEK) are managed via AWS KMS or GCP Cloud KMS, never stored in plain text or logged.",
      icon: LockIcon,
      badge: "KMS HARDENED",
    },
    {
      title: "Non-Custodial Broker Connectivity",
      desc: "Atlas AI never takes custody of funds. Orders are routed directly from your localized Execution Agent runtime to certified broker APIs (OANDA, Binance, MT5 ZeroMQ). Your capital remains securely inside your brokerage account.",
      icon: CheckIcon,
      badge: "NON-CUSTODIAL",
    },
    {
      title: "Constitutional Hard Veto Risk Gate",
      desc: "The Risk Sentinel maintains unilateral, absolute veto power. If a trade proposal exceeds 1.5% portfolio VaR, breaches daily drawdown caps, or enters pre-FOMC volatility windows, the Risk Agent trips the circuit to HALTED instantaneously.",
      icon: AlertTriangleIcon,
      badge: "HARD VETO",
    },
  ];

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg-canvas)", color: "var(--text-primary)" }}>
      {/* Top Navbar */}
      <nav
        style={{
          height: "54px",
          background: "var(--bg-surface)",
          borderBottom: "1px solid var(--border-subtle)",
          padding: "0 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          position: "sticky",
          top: 0,
          zIndex: 50,
        }}
      >
        <a href="/" style={{ textDecoration: "none", color: "inherit", display: "flex", alignItems: "center" }}>
          <AtlasLogo size="sm" showText={true} badge="SECURITY" />
        </a>

        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <a href="/architecture" style={{ fontSize: "12px", color: "var(--text-secondary)", textDecoration: "none", fontWeight: 600 }}>Architecture</a>
          <a href="/pricing" style={{ fontSize: "12px", color: "var(--text-secondary)", textDecoration: "none", fontWeight: 600 }}>Pricing</a>
          <a href="/docs" style={{ fontSize: "12px", color: "var(--text-secondary)", textDecoration: "none", fontWeight: 600 }}>Docs</a>
          <button
            onClick={handleToggleTheme}
            style={{
              width: "32px",
              height: "32px",
              background: "var(--bg-surface-elevated)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "6px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {theme === "light" ? <MoonIcon size={13} color="currentColor" /> : <SunIcon size={13} color="var(--accent-amber)" />}
          </button>
          <a
            href="/cockpit"
            style={{
              background: "var(--accent-blue)",
              color: "#fff",
              padding: "7px 16px",
              borderRadius: "6px",
              fontSize: "12px",
              fontWeight: 700,
              textDecoration: "none",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <ZapIcon size={12} color="#fff" />
            <span>Launch Cockpit</span>
          </a>
        </div>
      </nav>

      {/* Main Content */}
      <main style={{ maxWidth: "1080px", margin: "0 auto", padding: "56px 20px 80px" }}>
        <div style={{ textAlign: "center", marginBottom: "48px" }}>
          <span style={{ fontSize: "11px", fontWeight: 800, color: "var(--accent-blue)", letterSpacing: "0.08em" }}>
            INSTITUTIONAL TRUST &amp; COMPLIANCE
          </span>
          <h1 style={{ fontSize: "40px", fontWeight: 900, marginTop: "8px", letterSpacing: "-0.02em" }}>
            Zero-Trust Sovereign Security Architecture
          </h1>
          <p style={{ fontSize: "16px", color: "var(--text-secondary)", maxWidth: "660px", margin: "12px auto 0", lineHeight: 1.6 }}>
            Engineered specifically for institutional financial operations. Complete defense-in-depth across cryptographic key vaults, runtime agent sandbox boundaries, and immutable Kafka decision logs.
          </p>
        </div>

        {/* 4 Security Pillars Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(460px, 1fr))", gap: "20px", marginBottom: "48px" }}>
          {securityPillars.map((p, idx) => {
            const Icon = p.icon;
            return (
              <div
                key={idx}
                style={{
                  background: "var(--bg-surface)",
                  border: "1px solid var(--border-medium)",
                  borderRadius: "10px",
                  padding: "28px",
                  boxShadow: "var(--card-shadow)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                  <div style={{ width: "36px", height: "36px", borderRadius: "8px", background: "var(--bg-surface-elevated)", border: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <Icon size={18} color="var(--accent-blue)" />
                  </div>
                  <span style={{ fontSize: "9px", fontWeight: 800, padding: "3px 8px", borderRadius: "4px", background: "var(--accent-blue-subtle)", color: "var(--accent-blue)", border: "1px solid var(--accent-blue-border)", letterSpacing: "0.05em" }}>
                    {p.badge}
                  </span>
                </div>
                <h3 style={{ fontSize: "16px", fontWeight: 800, margin: "0 0 8px" }}>{p.title}</h3>
                <p style={{ fontSize: "12.5px", color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>{p.desc}</p>
              </div>
            );
          })}
        </div>

        {/* Cryptographic Key Architecture Deep Dive */}
        <section style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "12px", padding: "32px", marginBottom: "48px" }}>
          <h2 style={{ fontSize: "18px", fontWeight: 800, marginBottom: "16px" }}>
            2. Envelope Encryption Flow (AES-256-GCM + KMS)
          </h2>
          <div style={{ background: "var(--bg-canvas)", border: "1px solid var(--border-subtle)", borderRadius: "8px", padding: "20px", fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--text-secondary)", lineHeight: 1.7 }}>
            <div>1. Client inputs Broker API Key &amp; Secret into localized Broker Vault.</div>
            <div>2. Vault generates unique ephemeral Data Encryption Key (DEK).</div>
            <div>3. Broker credentials encrypted locally using AES-256-GCM with 96-bit authenticated nonce.</div>
            <div>4. DEK sent to AWS KMS / GCP Cloud KMS for wrapping via customer-managed Key Encryption Key (KEK).</div>
            <div>5. Only encrypted ciphertext + wrapped DEK persisted in PostgreSQL 16 database.</div>
            <div>6. Plaintext credentials NEVER sent to LLM prompt context or remote cloud servers.</div>
          </div>
        </section>

        {/* Emergency Kill Switch Section */}
        <section style={{ background: "rgba(239, 68, 68, 0.05)", border: "1px solid rgba(239, 68, 68, 0.25)", borderRadius: "12px", padding: "28px 32px", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "20px" }}>
          <div>
            <h3 style={{ fontSize: "16px", fontWeight: 800, color: "#ef4444", margin: "0 0 6px" }}>
              Emergency Hard Kill Switch (FLATTEN)
            </h3>
            <p style={{ fontSize: "12.5px", color: "var(--text-secondary)", margin: 0, maxWidth: "600px", lineHeight: 1.5 }}>
              One-click operator override immediately executes market-order liquidation across all connected brokers, revokes pending limits, and locks the Risk Sentinel in HALTED state.
            </p>
          </div>
          <a
            href="/cockpit"
            style={{
              background: "#ef4444",
              color: "#fff",
              padding: "10px 20px",
              borderRadius: "6px",
              fontSize: "12px",
              fontWeight: 800,
              textDecoration: "none",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <span>Test in Cockpit</span>
            <ArrowRightIcon size={12} color="#fff" />
          </a>
        </section>
      </main>
    </div>
  );
}

