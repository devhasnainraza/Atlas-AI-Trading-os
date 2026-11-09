"use client";

import React, { useState, useEffect } from "react";
import { AtlasLogo } from "../../components/AtlasLogo";
import { ZapIcon, ShieldIcon, CheckIcon, ArrowRightIcon, SunIcon, MoonIcon } from "../../components/Icons";

export default function ArchitecturePage() {
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
    setTheme((prev) => {
      const next = prev === "light" ? "dark" : "light";
      try {
        localStorage.setItem("atlas_theme", next);
        document.documentElement.setAttribute("data-theme", next);
      } catch {}
      return next;
    });
  };

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg-canvas)", color: "var(--text-primary)" }}>
      {/* Nav */}
      <nav style={{ height: "54px", background: "var(--bg-surface)", borderBottom: "1px solid var(--border-subtle)", padding: "0 24px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <a href="/" style={{ textDecoration: "none", color: "inherit", display: "flex", alignItems: "center" }}>
          <AtlasLogo size="sm" showText={true} badge="ARCHITECTURE" />
        </a>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <button onClick={handleToggleTheme} style={{ width: "32px", height: "32px", background: "var(--bg-surface-elevated)", border: "1px solid var(--border-subtle)", borderRadius: "6px", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
            {theme === "light" ? <MoonIcon size={13} color="currentColor" /> : <SunIcon size={13} color="currentColor" />}
          </button>
          <a href="/cockpit" style={{ background: "var(--accent-blue)", color: "#fff", padding: "6px 14px", borderRadius: "6px", fontSize: "12px", fontWeight: 700, textDecoration: "none" }}>
            Launch Cockpit
          </a>
        </div>
      </nav>

      {/* Main Content */}
      <main style={{ maxWidth: "1000px", margin: "0 auto", padding: "48px 24px" }}>
        <div style={{ textAlign: "center", marginBottom: "40px" }}>
          <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--accent-blue)", letterSpacing: "0.08em" }}>
            TECHNICAL BLUEPRINT
          </span>
          <h1 style={{ fontSize: "36px", fontWeight: 900, marginTop: "6px" }}>
            Atlas AI Multi-Agent Operating System
          </h1>
          <p style={{ fontSize: "15px", color: "var(--text-secondary)", maxWidth: "640px", margin: "8px auto 0", lineHeight: 1.6 }}>
            A distributed LangGraph state graph enforcing strict zero-trust segregation of duties between analysis, risk governance, and execution.
          </p>
        </div>

        {/* Roles & Permissions Matrix */}
        <section style={{ background: "var(--bg-surface)", border: "1px solid var(--border-medium)", borderRadius: "10px", padding: "24px", marginBottom: "32px", boxShadow: "var(--card-shadow)" }}>
          <h2 style={{ fontSize: "18px", fontWeight: 800, marginBottom: "16px" }}>1. Agent Roles &amp; Permissions Matrix</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "12px" }}>
            {[
              { name: "Manager Agent", perm: "COORDINATE", broker: "STRICTLY 0 ACCESS", desc: "Coordinates LangGraph deliberation threads and issues approval tickets. Forbidden from holding exchange keys." },
              { name: "Market Agent", perm: "READ", broker: "NONE", desc: "Ingests L2 orderbook depth, calculates Cumulative Volume Delta (CVD) absorption, and monitors volatility regimes." },
              { name: "News Agent", perm: "READ / ANALYZE", broker: "NONE", desc: "Tracks macroeconomic calendar releases, central bank commentary, and enforces pre-news trading embargoes." },
              { name: "Risk Agent", perm: "ANALYZE & HARD VETO", broker: "NONE", desc: "Computes 99% VaR, margin usage, and drawdown limits. Holds absolute unbendable constitutional Hard Veto." },
              { name: "Decision Agent", perm: "ANALYZE", broker: "NONE", desc: "Synthesizes mathematical setups with positive Expected Value (EV), 1:2 R:R brackets, and confluence scoring." },
              { name: "Critic Agent", perm: "CRITIQUE", broker: "NONE", desc: "Acts as internal Devil's Advocate: stress-tests downside traps, overhead resistance clusters, and crowded positioning." },
              { name: "Execution Agent", perm: "EXECUTE ONLY", broker: "EXCLUSIVE", desc: "The ONLY node holding broker keys. Hard-coded code barrier prevents execution without verified human signature." },
            ].map((node, i) => (
              <div key={i} style={{ background: "var(--bg-surface-elevated)", border: "1px solid var(--border-subtle)", borderRadius: "8px", padding: "14px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                  <strong style={{ fontSize: "13px" }}>{node.name}</strong>
                  <span style={{ fontSize: "9px", fontWeight: 800, padding: "2px 6px", borderRadius: "3px", background: "var(--bg-surface-card)", border: "1px solid var(--border-subtle)", color: "var(--accent-blue)" }}>
                    {node.perm}
                  </span>
                </div>
                <div style={{ fontSize: "10.5px", color: "var(--text-muted)", marginBottom: "6px" }}>Broker Access: <strong>{node.broker}</strong></div>
                <p style={{ fontSize: "11.5px", color: "var(--text-secondary)", lineHeight: 1.5, margin: 0 }}>{node.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Protocols Section */}
        <section style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
          <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "10px", padding: "24px", boxShadow: "var(--card-shadow)" }}>
            <h3 style={{ fontSize: "16px", fontWeight: 800, color: "var(--accent-blue)", margin: "0 0 10px" }}>
              Model Context Protocol (MCP)
            </h3>
            <p style={{ fontSize: "12.5px", color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>
              Atlas AI implements the standard Model Context Protocol. Domain capabilities like real-time orderbooks, news sentiment feeds, and portfolio telemetry are registered as standardized MCP tools on <code>atlas-mcp-core</code>, enabling agents to dynamically discover and invoke tools with typed validation.
            </p>
          </div>

          <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "10px", padding: "24px", boxShadow: "var(--card-shadow)" }}>
            <h3 style={{ fontSize: "16px", fontWeight: 800, color: "#10b981", margin: "0 0 10px" }}>
              Agent-to-Agent (A2A) Protocol
            </h3>
            <p style={{ fontSize: "12.5px", color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>
              Adheres to the open A2A specification (<a href="https://a2a-protocol.org" target="_blank" rel="noreferrer" style={{ color: "var(--accent-blue)" }}>a2a-protocol.org</a>). Internal swarms can publish signed <code>A2ADelegationRequest</code> payloads to remote external specialist agents (e.g., On-Chain Whale Trackers, Implied Volatility Surface quants) and verify responses with cryptographic signatures.
            </p>
          </div>
        </section>
      </main>
    </div>
  );
}

