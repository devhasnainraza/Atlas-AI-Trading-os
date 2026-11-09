"use client";

import React, { useState, useEffect } from "react";
import { soundManager } from "../../lib/soundEffects";
import { AtlasLogo } from "../../components/AtlasLogo";
import { CheckIcon, ZapIcon, ShieldIcon, SunIcon, MoonIcon, ArrowRightIcon } from "../../components/Icons";

export default function PricingPage() {
  const [billingCycle, setBillingCycle] = useState<"monthly" | "annual">("annual");
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

  const plans = [
    {
      name: "Community",
      badge: "FREE FOREVER",
      priceMonthly: 0,
      priceAnnual: 0,
      desc: "For individual traders exploring autonomous AI agents with paper trading simulations.",
      features: [
        "Full access to 7-Agent Neural Swarm (Paper mode)",
        "Live Binance L2 real-time orderbook feeds",
        "Multi-asset charting (Crypto & FX feeds)",
        "Daily automated trade journaling",
        "Community Discord & GitHub support",
        "Local rule execution & manual approval",
      ],
      cta: "Start Free Paper Trading",
      highlighted: false,
    },
    {
      name: "Pro Quant",
      badge: "MOST POPULAR",
      priceMonthly: 79,
      priceAnnual: 64,
      desc: "For serious systematic traders and prop firm quants running automated 24/7 loops.",
      features: [
        "Everything in Community, plus:",
        "Direct non-custodial live broker execution (OANDA, Binance, MT5)",
        "AES-256-GCM Envelope Encryption (AWS KMS / GCP Cloud KMS)",
        "Sub-15ms Event Loop over Kafka / Redpanda",
        "Omnichannel Alerts: Telegram & WhatsApp Gateway",
        "Dynamic Trailing Stops & Auto-Breakeven engine",
        "Model Context Protocol (MCP) toolchain extensibility",
      ],
      cta: "Deploy Pro Quant OS",
      highlighted: true,
    },
    {
      name: "Hedge Fund & Family Office",
      badge: "ENTERPRISE",
      priceMonthly: 499,
      priceAnnual: 399,
      desc: "For institutional funds, multi-seat trading desks, and proprietary liquidity providers.",
      features: [
        "Everything in Pro Quant, plus:",
        "Unlimited live broker connections & sub-accounts",
        "Self-hosted VPC / on-premises Kubernetes deployment",
        "Agent-to-Agent (A2A) cross-firm protocol interconnect",
        "Custom Hard Veto risk compliance policies & audit logs",
        "Institutional FIX protocol & low-latency direct market access (DMA)",
        "Dedicated Quantitative Solutions Engineer & 24/7 SLA",
      ],
      cta: "Contact Institutional Sales",
      highlighted: false,
    },
  ];

  const faqs = [
    {
      q: "Can Atlas AI execute trades without my permission?",
      a: "Never by default. The platform adheres to strict segregation of duties: all high-risk proposals pass through the Human Approval Gate with 1:2 R:R brackets, expected value validation, and risk checks before the Execution Agent is authorized.",
    },
    {
      q: "Do you store or have access to my broker private keys?",
      a: "No. Atlas OS is strictly non-custodial. Your broker credentials and API secrets are envelope-encrypted on your client/vault using AES-256-GCM and stored only in your encrypted database with AWS/GCP KMS key management.",
    },
    {
      q: "Can I connect custom trading models or Python scripts?",
      a: "Yes. Atlas OS implements both the Model Context Protocol (MCP) and Agent-to-Agent (A2A) specifications, allowing external Python quants, LangGraph scripts, and custom risk models to seamlessly interoperate.",
    },
    {
      q: "What brokers are natively supported?",
      a: "Out of the box, Atlas OS supports Binance (Spot & Futures), OANDA (Forex & Commodities), and MetaTrader 5 (MT5 / ZeroMQ bridge), with Coinbase Advanced and Interactive Brokers (IBKR) arriving next.",
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
          <AtlasLogo size="sm" showText={true} badge="PRICING" />
        </a>

        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <a href="/architecture" style={{ fontSize: "12px", color: "var(--text-secondary)", textDecoration: "none", fontWeight: 600 }}>Architecture</a>
          <a href="/security" style={{ fontSize: "12px", color: "var(--text-secondary)", textDecoration: "none", fontWeight: 600 }}>Security</a>
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

      {/* Hero Section */}
      <main style={{ maxWidth: "1160px", margin: "0 auto", padding: "56px 20px 80px" }}>
        <div style={{ textAlign: "center", marginBottom: "40px" }}>
          <span style={{ fontSize: "11px", fontWeight: 800, color: "var(--accent-blue)", letterSpacing: "0.08em" }}>
            TRANSPARENT INSTITUTIONAL TIERS
          </span>
          <h1 style={{ fontSize: "40px", fontWeight: 900, marginTop: "8px", letterSpacing: "-0.02em" }}>
            Predictable Pricing for Autonomous Execution
          </h1>
          <p style={{ fontSize: "16px", color: "var(--text-secondary)", maxWidth: "620px", margin: "12px auto 0", lineHeight: 1.6 }}>
            Run the 7-node multi-agent operating system on your terms. From individual paper trading to multi-desk institutional hedge fund deployments.
          </p>

          {/* Billing Cycle Toggle */}
          <div style={{ display: "inline-flex", alignItems: "center", background: "var(--bg-surface)", border: "1px solid var(--border-medium)", borderRadius: "8px", padding: "4px", marginTop: "28px" }}>
            <button
              onClick={() => { soundManager.playClick(); setBillingCycle("monthly"); }}
              style={{
                padding: "6px 18px",
                borderRadius: "6px",
                fontSize: "12px",
                fontWeight: billingCycle === "monthly" ? 700 : 500,
                background: billingCycle === "monthly" ? "var(--bg-surface-elevated)" : "transparent",
                color: billingCycle === "monthly" ? "var(--text-primary)" : "var(--text-muted)",
                border: billingCycle === "monthly" ? "1px solid var(--border-subtle)" : "1px solid transparent",
                cursor: "pointer",
              }}
            >
              Monthly Billing
            </button>
            <button
              onClick={() => { soundManager.playClick(); setBillingCycle("annual"); }}
              style={{
                padding: "6px 18px",
                borderRadius: "6px",
                fontSize: "12px",
                fontWeight: billingCycle === "annual" ? 700 : 500,
                background: billingCycle === "annual" ? "var(--accent-blue)" : "transparent",
                color: billingCycle === "annual" ? "#ffffff" : "var(--text-muted)",
                border: "none",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              <span>Annual Billing</span>
              <span style={{ fontSize: "9.5px", fontWeight: 800, background: "rgba(255,255,255,0.25)", padding: "1px 5px", borderRadius: "4px" }}>SAVE 20%</span>
            </button>
          </div>
        </div>

        {/* Pricing Cards Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "24px", marginBottom: "64px" }}>
          {plans.map((p, idx) => {
            const price = billingCycle === "annual" ? p.priceAnnual : p.priceMonthly;
            return (
              <div
                key={idx}
                style={{
                  background: "var(--bg-surface)",
                  border: p.highlighted ? "2px solid var(--accent-blue)" : "1px solid var(--border-subtle)",
                  borderRadius: "12px",
                  padding: "32px 28px",
                  display: "flex",
                  flexDirection: "column",
                  position: "relative",
                  boxShadow: p.highlighted ? "0 12px 32px rgba(37, 99, 235, 0.12)" : "var(--card-shadow)",
                }}
              >
                {p.highlighted && (
                  <div
                    style={{
                      position: "absolute",
                      top: "-12px",
                      left: "50%",
                      transform: "translateX(-50%)",
                      background: "var(--accent-blue)",
                      color: "#fff",
                      fontSize: "10px",
                      fontWeight: 800,
                      padding: "3px 12px",
                      borderRadius: "12px",
                      letterSpacing: "0.05em",
                    }}
                  >
                    RECOMMENDED FOR QUANTS
                  </div>
                )}

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
                  <h3 style={{ fontSize: "18px", fontWeight: 800, margin: 0 }}>{p.name}</h3>
                  <span style={{ fontSize: "9px", fontWeight: 800, color: p.highlighted ? "var(--accent-blue)" : "var(--text-muted)", letterSpacing: "0.06em" }}>
                    {p.badge}
                  </span>
                </div>

                <p style={{ fontSize: "12.5px", color: "var(--text-secondary)", minHeight: "36px", margin: "6px 0 20px", lineHeight: 1.5 }}>
                  {p.desc}
                </p>

                <div style={{ display: "flex", alignItems: "baseline", gap: "4px", marginBottom: "24px" }}>
                  <span style={{ fontSize: "36px", fontWeight: 900 }}>${price}</span>
                  <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 600 }}>/ month {billingCycle === "annual" && price > 0 ? "billed annually" : ""}</span>
                </div>

                <a
                  href="/cockpit"
                  style={{
                    background: p.highlighted ? "var(--accent-blue)" : "var(--bg-surface-elevated)",
                    color: p.highlighted ? "#fff" : "var(--text-primary)",
                    border: p.highlighted ? "none" : "1px solid var(--border-medium)",
                    padding: "11px",
                    borderRadius: "6px",
                    fontSize: "12.5px",
                    fontWeight: 700,
                    textAlign: "center",
                    textDecoration: "none",
                    marginBottom: "28px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "6px",
                  }}
                >
                  <span>{p.cta}</span>
                  <ArrowRightIcon size={12} color="currentColor" />
                </a>

                <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "20px", flex: 1 }}>
                  <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", marginBottom: "12px", letterSpacing: "0.04em" }}>
                    INCLUDED CAPABILITIES
                  </div>
                  <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "10px" }}>
                    {p.features.map((feat, fIdx) => (
                      <li key={fIdx} style={{ display: "flex", alignItems: "flex-start", gap: "8px", fontSize: "12px", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                        <span style={{ color: "var(--accent-green)", marginTop: "2px", flexShrink: 0 }}>
                          <CheckIcon size={12} color="currentColor" />
                        </span>
                        <span>{feat}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            );
          })}
        </div>

        {/* FAQ Section */}
        <section style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "12px", padding: "36px 32px", boxShadow: "var(--card-shadow)" }}>
          <h2 style={{ fontSize: "20px", fontWeight: 800, textAlign: "center", marginBottom: "28px" }}>
            Frequently Asked Questions
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(440px, 1fr))", gap: "24px" }}>
            {faqs.map((faq, i) => (
              <div key={i} style={{ borderBottom: "1px solid var(--border-subtle)", paddingBottom: "16px" }}>
                <h4 style={{ fontSize: "13.5px", fontWeight: 700, margin: "0 0 6px", color: "var(--text-primary)" }}>{faq.q}</h4>
                <p style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>{faq.a}</p>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

