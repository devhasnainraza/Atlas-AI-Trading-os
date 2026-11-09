"use client";

import React, { useState, useEffect } from "react";
import { soundManager } from "../../lib/soundEffects";
import { AtlasLogo } from "../../components/AtlasLogo";
import { BookOpenIcon, ZapIcon, SunIcon, MoonIcon, CheckIcon, ArrowRightIcon } from "../../components/Icons";

export default function DocsPage() {
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [selectedTopic, setSelectedTopic] = useState<"quickstart" | "kafka" | "mcp" | "a2a" | "rest">("quickstart");

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
          <AtlasLogo size="sm" showText={true} badge="DOCS" />
        </a>

        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <a href="/architecture" style={{ fontSize: "12px", color: "var(--text-secondary)", textDecoration: "none", fontWeight: 600 }}>Architecture</a>
          <a href="/pricing" style={{ fontSize: "12px", color: "var(--text-secondary)", textDecoration: "none", fontWeight: 600 }}>Pricing</a>
          <a href="/security" style={{ fontSize: "12px", color: "var(--text-secondary)", textDecoration: "none", fontWeight: 600 }}>Security</a>
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

      {/* Main Documentation Layout */}
      <div style={{ maxWidth: "1200px", margin: "0 auto", display: "grid", gridTemplateColumns: "240px minmax(0, 1fr)", minHeight: "calc(100vh - 54px)" }}>
        {/* Sidebar Nav */}
        <aside style={{ borderRight: "1px solid var(--border-subtle)", padding: "24px 16px", background: "var(--bg-surface)" }}>
          <div style={{ fontSize: "10.5px", fontWeight: 800, color: "var(--text-muted)", letterSpacing: "0.06em", marginBottom: "12px" }}>
            OPERATING SYSTEM GUIDE
          </div>
          <nav style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            {[
              { id: "quickstart", label: "Quickstart Guide" },
              { id: "kafka", label: "Kafka Event Bus Contract" },
              { id: "mcp", label: "Model Context Protocol (MCP)" },
              { id: "a2a", label: "Agent-to-Agent (A2A) RFC" },
              { id: "rest", label: "REST & WebSocket APIs" },
            ].map((item) => {
              const active = selectedTopic === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    soundManager.playClick();
                    setSelectedTopic(item.id as any);
                  }}
                  style={{
                    textAlign: "left",
                    padding: "8px 12px",
                    borderRadius: "6px",
                    fontSize: "12px",
                    fontWeight: active ? 700 : 500,
                    background: active ? "var(--bg-surface-elevated)" : "transparent",
                    color: active ? "var(--accent-blue)" : "var(--text-secondary)",
                    border: active ? "1px solid var(--accent-blue-border)" : "1px solid transparent",
                    cursor: "pointer",
                  }}
                >
                  {item.label}
                </button>
              );
            })}
          </nav>
        </aside>

        {/* Content Area */}
        <main style={{ padding: "40px 48px" }}>
          {selectedTopic === "quickstart" && (
            <div>
              <span style={{ fontSize: "11px", fontWeight: 800, color: "var(--accent-blue)", letterSpacing: "0.06em" }}>SECTION 1.0</span>
              <h1 style={{ fontSize: "32px", fontWeight: 900, margin: "6px 0 16px" }}>Atlas AI Quickstart</h1>
              <p style={{ fontSize: "14px", color: "var(--text-secondary)", lineHeight: 1.6 }}>
                Deploy the sovereign multi-agent trading operating system on your workstation or cloud container in 3 commands.
              </p>

              <h3 style={{ fontSize: "16px", fontWeight: 800, marginTop: "28px" }}>1. Clone Repository &amp; Install Dependencies</h3>
              <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "6px", padding: "14px", fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--accent-blue)" }}>
                git clone https://github.com/atlas-ai/atlas-financial-os.git<br />
                cd atlas-financial-os &amp;&amp; npm install
              </div>

              <h3 style={{ fontSize: "16px", fontWeight: 800, marginTop: "24px" }}>2. Launch 24/7 Swarm Engine &amp; Web Cockpit</h3>
              <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "6px", padding: "14px", fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--accent-blue)" }}>
                npm run dev
              </div>

              <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "16px", lineHeight: 1.6 }}>
                Open <a href="/cockpit" style={{ color: "var(--accent-blue)", fontWeight: 700 }}>http://localhost:3000/cockpit</a> in your browser to inspect live L2 orderbooks, monitor active agent threads, or review trade proposals.
              </p>
            </div>
          )}

          {selectedTopic === "kafka" && (
            <div>
              <span style={{ fontSize: "11px", fontWeight: 800, color: "var(--accent-blue)", letterSpacing: "0.06em" }}>SECTION 2.0</span>
              <h1 style={{ fontSize: "32px", fontWeight: 900, margin: "6px 0 16px" }}>Kafka Event Bus Specifications</h1>
              <p style={{ fontSize: "14px", color: "var(--text-secondary)", lineHeight: 1.6 }}>
                All agent telemetry, order proposals, and risk evaluations are broadcast over typed Kafka / Redpanda topics.
              </p>

              <div style={{ display: "grid", gap: "14px", marginTop: "24px" }}>
                {[
                  { topic: "atlas.market.orderbook.v1", payload: "{ symbol, bids: [p, q][], asks: [p, q][], cvdDelta, timestamp }", desc: "Sub-10ms raw L2 tick orderbook feed ingested by Market Agent." },
                  { topic: "atlas.macro.news.v1", payload: "{ eventId, impact: 'HIGH'|'MED', forecast, actual, embargoActive }", desc: "Macroeconomic calendar events triggering volatility embargoes." },
                  { topic: "atlas.swarm.proposal.v1", payload: "{ proposalId, symbol, side, ev, rrRatio, riskCapUsd, agentVotes }", desc: "Synthesized setup published for Risk Agent VaR verification." },
                  { topic: "atlas.execution.orders.v1", payload: "{ orderId, brokerId, symbol, side, qty, tpPrice, slPrice, humanSignature }", desc: "Audited trade execution payload delivered exclusively to Execution Agent." },
                ].map((t, idx) => (
                  <div key={idx} style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "8px", padding: "16px" }}>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: "13px", fontWeight: 800, color: "var(--accent-blue)", marginBottom: "4px" }}>{t.topic}</div>
                    <div style={{ fontSize: "11.5px", color: "var(--text-muted)", fontFamily: "var(--font-mono)", marginBottom: "6px" }}>Payload: {t.payload}</div>
                    <div style={{ fontSize: "12.5px", color: "var(--text-secondary)" }}>{t.desc}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {selectedTopic === "mcp" && (
            <div>
              <span style={{ fontSize: "11px", fontWeight: 800, color: "var(--accent-blue)", letterSpacing: "0.06em" }}>SECTION 3.0</span>
              <h1 style={{ fontSize: "32px", fontWeight: 900, margin: "6px 0 16px" }}>Model Context Protocol (MCP)</h1>
              <p style={{ fontSize: "14px", color: "var(--text-secondary)", lineHeight: 1.6 }}>
                Agents interact with tools via the standardized Model Context Protocol JSON-RPC specification.
              </p>
              <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "8px", padding: "16px", marginTop: "20px" }}>
                <pre style={{ margin: 0, fontSize: "12px", fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>
{`// Example MCP Tool Definition: get_orderbook_cvd
{
  "name": "get_orderbook_cvd",
  "description": "Calculates Cumulative Volume Delta absorption on L2 depth",
  "parameters": {
    "type": "object",
    "properties": {
      "symbol": { "type": "string" },
      "lookback_candles": { "type": "number", "default": 20 }
    },
    "required": ["symbol"]
  }
}`}
                </pre>
              </div>
            </div>
          )}

          {selectedTopic === "a2a" && (
            <div>
              <span style={{ fontSize: "11px", fontWeight: 800, color: "var(--accent-blue)", letterSpacing: "0.06em" }}>SECTION 4.0</span>
              <h1 style={{ fontSize: "32px", fontWeight: 900, margin: "6px 0 16px" }}>Agent-to-Agent (A2A) Protocol RFC</h1>
              <p style={{ fontSize: "14px", color: "var(--text-secondary)", lineHeight: 1.6 }}>
                Cross-agent communication specification adhering to <a href="https://a2a-protocol.org" target="_blank" rel="noreferrer" style={{ color: "var(--accent-blue)" }}>a2a-protocol.org</a> for decentralized agent discovery and delegation.
              </p>
              <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "8px", padding: "16px", marginTop: "20px" }}>
                <pre style={{ margin: 0, fontSize: "12px", fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>
{`// A2A Delegation Message Envelope
{
  "protocol": "A2A/1.0",
  "sender": "did:atlas:decision-agent-01",
  "recipient": "did:remote:whale-tracker-node",
  "action": "DELEGATE_ANALYTICS",
  "nonce": 9842104,
  "signature": "0x4f8a...3e1d"
}`}
                </pre>
              </div>
            </div>
          )}

          {selectedTopic === "rest" && (
            <div>
              <span style={{ fontSize: "11px", fontWeight: 800, color: "var(--accent-blue)", letterSpacing: "0.06em" }}>SECTION 5.0</span>
              <h1 style={{ fontSize: "32px", fontWeight: 900, margin: "6px 0 16px" }}>REST &amp; WebSocket Endpoints</h1>
              <div style={{ display: "grid", gap: "10px", marginTop: "20px" }}>
                <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "6px", padding: "12px" }}>
                  <code style={{ color: "#10b981", fontWeight: 800 }}>GET /api/agent/stream</code> — Server-Sent Events stream for live agent reasoning tokens.
                </div>
                <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "6px", padding: "12px" }}>
                  <code style={{ color: "var(--accent-blue)", fontWeight: 800 }}>POST /api/agent/execute</code> — Submits Human Approval Signature to Execution Agent.
                </div>
                <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "6px", padding: "12px" }}>
                  <code style={{ color: "#ef4444", fontWeight: 800 }}>POST /api/risk/halt</code> — Trips Emergency Circuit Breaker to HALTED.
                </div>
                <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "6px", padding: "12px" }}>
                  <code style={{ color: "var(--text-secondary)", fontWeight: 800 }}>GET /api/journal</code> — Returns structured AI decision history and evaluation benchmarks.
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

