"use client";

import React, { useState, useEffect } from "react";
import { soundManager } from "../lib/soundEffects";
import { AtlasLogo, AtlasEmblem } from "./AtlasLogo";
import {
  ZapIcon,
  ShieldIcon,
  ActivityIcon,
  CheckIcon,
  RadarIcon,
  TrendingUpIcon,
  TrendingDownIcon,
  SendIcon,
  LockIcon,
  BookOpenIcon,
  SlidersIcon,
  SunIcon,
  MoonIcon,
  CloseIcon,
  ArrowRightIcon,
} from "./Icons";

interface LandingPageViewProps {
  onLaunchCockpit: () => void;
  theme?: "light" | "dark";
  onToggleTheme?: () => void;
}

export function LandingPageView({
  onLaunchCockpit,
  theme = "light",
  onToggleTheme,
}: LandingPageViewProps) {
  const [activeAsset, setActiveAsset] = useState<"BTC" | "ETH" | "SOL">("BTC");
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationStep, setSimulationStep] = useState<number>(0);
  const [simLogs, setSimLogs] = useState<string[]>([]);
  const [isMobile, setIsMobile] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const [prices, setPrices] = useState({
    BTC: { symbol: "BTC/USDT", price: 86234, change: "+1.85%", up: true },
    ETH: { symbol: "ETH/USDT", price: 2842, change: "+2.14%", up: true },
    SOL: { symbol: "SOL/USDT", price: 154.2, change: "-0.65%", up: false },
    BNB: { symbol: "BNB/USDT", price: 790.1, change: "+1.15%", up: true },
    XRP: { symbol: "XRP/USDT", price: 1.613, change: "+3.20%", up: true },
    EUR: { symbol: "EUR/USD", price: 1.1417, change: "+0.15%", up: true },
    GBP: { symbol: "GBP/USD", price: 1.2985, change: "+0.35%", up: true },
    JPY: { symbol: "USD/JPY", price: 148.85, change: "-0.40%", up: false },
    XAU: { symbol: "XAU/USD", price: 2664.5, change: "+0.95%", up: true },
    OIL: { symbol: "USOIL", price: 71.2, change: "-1.10%", up: false },
    US100: { symbol: "NASDAQ", price: 19840.5, change: "+1.25%", up: true },
    NVDA: { symbol: "NVDA", price: 128.4, change: "+4.20%", up: true },
  });

  // Responsive mobile width detection
  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
    };
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Fetch live prices from Binance
  useEffect(() => {
    const fetchQuotes = async () => {
      try {
        const res = await fetch("https://api.binance.com/api/v3/ticker/price?symbols=[%22BTCUSDT%22,%22ETHUSDT%22,%22SOLUSDT%22,%22BNBUSDT%22,%22XRPUSDT%22]");
        if (res.ok) {
          const data = await res.json();
          const btc = data.find((d: any) => d.symbol === "BTCUSDT");
          const eth = data.find((d: any) => d.symbol === "ETHUSDT");
          const sol = data.find((d: any) => d.symbol === "SOLUSDT");
          const bnb = data.find((d: any) => d.symbol === "BNBUSDT");
          const xrp = data.find((d: any) => d.symbol === "XRPUSDT");
          setPrices((prev) => ({
            ...prev,
            BTC: btc ? { ...prev.BTC, price: Math.round(parseFloat(btc.price)) } : prev.BTC,
            ETH: eth ? { ...prev.ETH, price: Math.round(parseFloat(eth.price)) } : prev.ETH,
            SOL: sol ? { ...prev.SOL, price: parseFloat(parseFloat(sol.price).toFixed(2)) } : prev.SOL,
            BNB: bnb ? { ...prev.BNB, price: parseFloat(parseFloat(bnb.price).toFixed(1)) } : prev.BNB,
            XRP: xrp ? { ...prev.XRP, price: parseFloat(parseFloat(xrp.price).toFixed(4)) } : prev.XRP,
          }));
        }
      } catch {}
    };
    fetchQuotes();
    const interval = setInterval(fetchQuotes, 8000);
    return () => clearInterval(interval);
  }, []);

  // Run interactive 7-node swarm simulation demo
  const handleRunDemo = () => {
    if (isSimulating) return;
    setIsSimulating(true);
    setSimulationStep(1);
    setSimLogs([`[00:01] Manager Agent: Orchestrating LangGraph thread for ${activeAsset}/USDT. Direct broker access strictly DISABLED.`]);
    soundManager.playClick();

    setTimeout(() => {
      setSimulationStep(2);
      setSimLogs((prev) => [
        ...prev,
        `[00:02] Market Agent (READ): Orderbook depth skew +19% bids. CVD taker ratio 64.2% (Absorption: Strong limit buying).`,
      ]);
      soundManager.playClick();
    }, 700);

    setTimeout(() => {
      setSimulationStep(3);
      setSimLogs((prev) => [
        ...prev,
        `[00:03] News Agent (READ/ANALYZE): Macro sentiment +0.64 Bullish. Institutional ETF inflows +$380M. Zero macro embargo active.`,
      ]);
      soundManager.playClick();
    }, 1400);

    setTimeout(() => {
      setSimulationStep(4);
      setSimLogs((prev) => [
        ...prev,
        `[00:04] Risk Agent (ANALYZE & HARD VETO): Margin limit verified. VaR 99%: 1.85%. Drawdown Headroom: 1.85%. Passed.`,
      ]);
      soundManager.playClick();
    }, 2100);

    setTimeout(() => {
      setSimulationStep(5);
      setSimLogs((prev) => [
        ...prev,
        `[00:05] Decision Agent (ANALYZE): Synthesized BUY Proposal @ $${prices[activeAsset].price.toLocaleString()} | SL: -1.2% | TP: +2.5% | EV: +$168.`,
      ]);
      soundManager.playClick();
    }, 2800);

    setTimeout(() => {
      setSimulationStep(6);
      setSimLogs((prev) => [
        ...prev,
        `[00:06] Critic Agent (CRITIQUE): Stress-tested downside liquidity pool. Enforced strict invalidation body-close stop.`,
      ]);
      soundManager.playClick();
    }, 3500);

    setTimeout(() => {
      setSimulationStep(7);
      setSimLogs((prev) => [
        ...prev,
        `[00:07] Policy / Risk Engine: Pre-execution checks 4/4 Passed. Generated Ticket #TICKET-8842. PAUSED FOR HUMAN APPROVAL.`,
      ]);
      soundManager.playAlert();
      setIsSimulating(false);
    }, 4200);
  };

  const handleSimulateHumanApproval = () => {
    soundManager.playClick();
    setSimulationStep(8);
    setSimLogs((prev) => [
      ...prev,
      `[00:08] Human Approval Gate: Operator cryptographic token verified (Web/WhatsApp YES). Execution Agent unlocked.`,
      `[00:09] Execution Agent (EXECUTE ONLY): Order filled on Binance Spot Adapter @ $${prices[activeAsset].price.toLocaleString()}. Auto-Breakeven ARMED.`,
      `[00:10] AI Trading Journal: 7-part immutable audit record persisted with market state snapshot.`,
    ]);
    soundManager.playOrderFilled();
  };

  const closeMobileMenu = () => {
    setIsMobileMenuOpen(false);
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--bg-canvas)",
        color: "var(--text-primary)",
        fontFamily: "var(--font-sans, system-ui, sans-serif)",
        display: "flex",
        flexDirection: "column",
        overflowX: "hidden",
      }}
    >
      {/* ─────────────────────────────────────────────────────────────
          TOP INSTITUTIONAL NAVIGATION BAR (MOBILE & DESKTOP TUNED)
          ───────────────────────────────────────────────────────────── */}
      <nav
        style={{
          height: isMobile ? "50px" : "54px",
          background: "var(--bg-surface)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          borderBottom: "1px solid var(--border-subtle)",
          position: "sticky",
          top: 0,
          zIndex: 50,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: isMobile ? "0 12px" : "0 24px",
        }}
      >
        {/* Brand Logo */}
        <a href="/" style={{ textDecoration: "none", color: "inherit", display: "flex", alignItems: "center" }}>
          <AtlasLogo size={isMobile ? 22 : 26} showText={true} badge={isMobile ? undefined : "v2.5 QUANT"} glow={true} />
        </a>

        {/* Desktop Center Nav Links */}
        <div
          className="hide-mobile"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "20px",
            fontSize: "12.5px",
            fontWeight: 500,
            color: "var(--text-secondary)",
          }}
        >
          <a href="#pillars" style={{ color: "inherit", textDecoration: "none", transition: "color 0.15s" }}>
            8 Pillars
          </a>
          <a href="#architecture" style={{ color: "inherit", textDecoration: "none", transition: "color 0.15s" }}>
            Architecture
          </a>
          <a href="#demo" style={{ color: "inherit", textDecoration: "none", transition: "color 0.15s" }}>
            Swarm Demo
          </a>
          <a href="/security" style={{ color: "inherit", textDecoration: "none", transition: "color 0.15s" }}>
            Security &amp; Vault
          </a>
          <a href="/pricing" style={{ color: "inherit", textDecoration: "none", transition: "color 0.15s" }}>
            Pricing
          </a>
          <a href="/docs" style={{ color: "inherit", textDecoration: "none", transition: "color 0.15s" }}>
            Docs &amp; APIs
          </a>
        </div>

        {/* Right Action Cluster */}
        <div style={{ display: "flex", alignItems: "center", gap: isMobile ? "6px" : "10px" }}>
          {onToggleTheme && (
            <button
              onClick={onToggleTheme}
              style={{
                width: isMobile ? "28px" : "32px",
                height: isMobile ? "28px" : "32px",
                background: "var(--bg-surface-elevated)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "6px",
                color: theme === "light" ? "var(--text-secondary)" : "var(--accent-amber)",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
              title="Toggle Light / Dark Mode"
            >
              {theme === "light" ? <MoonIcon size={12} color="currentColor" /> : <SunIcon size={12} color="currentColor" />}
            </button>
          )}

          <button
            onClick={onLaunchCockpit}
            style={{
              background: "var(--accent-blue)",
              border: "none",
              color: "#ffffff",
              borderRadius: "6px",
              padding: isMobile ? "6px 11px" : "7px 16px",
              fontSize: isMobile ? "11px" : "12px",
              fontWeight: 700,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "5px",
              boxShadow: "0 2px 8px rgba(37, 99, 235, 0.25)",
              whiteSpace: "nowrap",
            }}
          >
            <ZapIcon size={12} color="#ffffff" />
            <span>{isMobile ? "Cockpit" : "Launch Cockpit"}</span>
          </button>

          {/* Mobile Hamburger Drawer Toggle */}
          {isMobile && (
            <button
              onClick={() => {
                soundManager.playClick();
                setIsMobileMenuOpen(!isMobileMenuOpen);
              }}
              style={{
                width: "28px",
                height: "28px",
                background: isMobileMenuOpen ? "var(--accent-blue-subtle)" : "var(--bg-surface-elevated)",
                border: `1px solid ${isMobileMenuOpen ? "var(--accent-blue-border)" : "var(--border-subtle)"}`,
                borderRadius: "6px",
                color: "var(--text-primary)",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
              title="Navigation Menu"
            >
              {isMobileMenuOpen ? (
                <CloseIcon size={13} color="var(--text-primary)" />
              ) : (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <line x1="3" y1="12" x2="21" y2="12" />
                  <line x1="3" y1="6" x2="21" y2="6" />
                  <line x1="3" y1="18" x2="21" y2="18" />
                </svg>
              )}
            </button>
          )}
        </div>
      </nav>

      {/* Slide-out Mobile Navigation Drawer */}
      {isMobile && isMobileMenuOpen && (
        <div
          style={{
            position: "fixed",
            top: "50px",
            left: 0,
            right: 0,
            bottom: 0,
            background: "var(--bg-surface)",
            backdropFilter: "blur(20px)",
            WebkitBackdropFilter: "blur(20px)",
            zIndex: 99,
            display: "flex",
            flexDirection: "column",
            padding: "16px",
            gap: "8px",
            overflowY: "auto",
            boxShadow: "0 16px 32px rgba(0,0,0,0.15)",
          }}
        >
          <div style={{ fontSize: "10.5px", fontWeight: 800, color: "var(--text-muted)", letterSpacing: "0.06em", marginBottom: "4px" }}>
            ATLAS OS NAVIGATION
          </div>

          {[
            { href: "#demo", label: "Swarm Simulation Demo", icon: RadarIcon },
            { href: "#architecture", label: "System Architecture Blueprint", icon: ShieldIcon },
            { href: "#pillars", label: "The 8 Core Pillars", icon: ActivityIcon },
            { href: "/architecture", label: "Technical Blueprint (LangGraph & MCP)", icon: BookOpenIcon },
            { href: "/security", label: "KMS Envelope Vault & Security", icon: LockIcon },
            { href: "/pricing", label: "Institutional Tiers & Pricing", icon: SlidersIcon },
            { href: "/docs", label: "Developer Docs & Kafka Specs", icon: BookOpenIcon },
          ].map((item, idx) => {
            const Icon = item.icon;
            return (
              <a
                key={idx}
                href={item.href}
                onClick={closeMobileMenu}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  padding: "11px 12px",
                  borderRadius: "8px",
                  background: "var(--bg-surface-elevated)",
                  border: "1px solid var(--border-subtle)",
                  color: "var(--text-primary)",
                  fontSize: "13px",
                  fontWeight: 600,
                  textDecoration: "none",
                }}
              >
                <Icon size={14} color="var(--accent-blue)" />
                <span>{item.label}</span>
              </a>
            );
          })}

          <div style={{ marginTop: "12px", paddingTop: "12px", borderTop: "1px solid var(--border-subtle)" }}>
            <button
              onClick={() => {
                closeMobileMenu();
                onLaunchCockpit();
              }}
              style={{
                width: "100%",
                background: "var(--accent-blue)",
                color: "#ffffff",
                border: "none",
                borderRadius: "8px",
                padding: "12px",
                fontSize: "13.5px",
                fontWeight: 800,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
                boxShadow: "0 4px 14px rgba(37, 99, 235, 0.35)",
              }}
            >
              <ZapIcon size={15} color="#ffffff" />
              <span>Launch 24/7 Trading Cockpit</span>
            </button>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          LIVE TICKER TAPE (AUTO-SCROLLING CONTINUOUS SLACK MARQUEE)
          ───────────────────────────────────────────────────────────── */}
      <div
        style={{
          background: "var(--bg-surface-elevated)",
          borderBottom: "1px solid var(--border-subtle)",
          height: isMobile ? "32px" : "36px",
          overflow: "hidden",
          position: "relative",
          display: "flex",
          alignItems: "center",
          userSelect: "none",
        }}
      >
        {/* Pinned Left Header Badge */}
        <div
          style={{
            position: "relative",
            zIndex: 3,
            display: "flex",
            alignItems: "center",
            gap: "6px",
            background: "var(--bg-surface-elevated)",
            padding: isMobile ? "0 10px" : "0 16px",
            height: "100%",
            borderRight: "1px solid var(--border-subtle)",
            boxShadow: "4px 0 12px rgba(0,0,0,0.06)",
            flexShrink: 0,
          }}
        >
          <span className="live-dot-green" />
          <span
            style={{
              fontSize: isMobile ? "9.5px" : "11px",
              fontWeight: 800,
              color: "var(--text-primary)",
              letterSpacing: "0.06em",
              whiteSpace: "nowrap",
            }}
          >
            {isMobile ? "TAPE" : "LIVE TAPE"}
          </span>
        </div>

        {/* Marquee Viewport with Edge Fade Gradients */}
        <div style={{ flex: 1, overflow: "hidden", position: "relative", height: "100%", display: "flex", alignItems: "center" }}>
          <div style={{ position: "absolute", top: 0, left: 0, bottom: 0, width: "20px", background: "linear-gradient(to right, var(--bg-surface-elevated), transparent)", zIndex: 2, pointerEvents: "none" }} />
          <div style={{ position: "absolute", top: 0, right: 0, bottom: 0, width: "24px", background: "linear-gradient(to left, var(--bg-surface-elevated), transparent)", zIndex: 2, pointerEvents: "none" }} />

          <div className="ticker-marquee-track">
            {/* Strip 1 */}
            <div style={{ display: "flex", alignItems: "center", gap: isMobile ? "18px" : "28px", paddingRight: isMobile ? "18px" : "28px" }}>
              {Object.entries(prices).map(([key, item]) => (
                <div key={`s1-${key}`} style={{ display: "flex", alignItems: "center", gap: "6px", whiteSpace: "nowrap" }}>
                  <span style={{ fontWeight: 700, fontSize: isMobile ? "10px" : "11px", color: "var(--text-primary)" }}>{item.symbol}</span>
                  <span className="tabular-nums" style={{ fontSize: isMobile ? "10px" : "11px" }}>${item.price.toLocaleString()}</span>
                  <span
                    style={{
                      color: item.up ? "#10b981" : "#f43f5e",
                      fontSize: isMobile ? "9px" : "10px",
                      fontWeight: 700,
                      background: item.up ? "rgba(16, 185, 129, 0.08)" : "rgba(244, 63, 94, 0.08)",
                      padding: "1px 4px",
                      borderRadius: "3px",
                    }}
                  >
                    {item.change}
                  </span>
                  <span style={{ color: "var(--border-medium)", margin: "0 2px" }}>•</span>
                </div>
              ))}
            </div>

            {/* Strip 2 (Identical for seamless infinite continuous loop) */}
            <div style={{ display: "flex", alignItems: "center", gap: isMobile ? "18px" : "28px", paddingRight: isMobile ? "18px" : "28px" }}>
              {Object.entries(prices).map(([key, item]) => (
                <div key={`s2-${key}`} style={{ display: "flex", alignItems: "center", gap: "6px", whiteSpace: "nowrap" }}>
                  <span style={{ fontWeight: 700, fontSize: isMobile ? "10px" : "11px", color: "var(--text-primary)" }}>{item.symbol}</span>
                  <span className="tabular-nums" style={{ fontSize: isMobile ? "10px" : "11px" }}>${item.price.toLocaleString()}</span>
                  <span
                    style={{
                      color: item.up ? "#10b981" : "#f43f5e",
                      fontSize: isMobile ? "9px" : "10px",
                      fontWeight: 700,
                      background: item.up ? "rgba(16, 185, 129, 0.08)" : "rgba(244, 63, 94, 0.08)",
                      padding: "1px 4px",
                      borderRadius: "3px",
                    }}
                  >
                    {item.change}
                  </span>
                  <span style={{ color: "var(--border-medium)", margin: "0 2px" }}>•</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          HERO SECTION (MOBILE & DESKTOP TUNED)
          ───────────────────────────────────────────────────────────── */}
      <header
        style={{
          padding: isMobile ? "32px 14px 36px" : "56px 24px 60px",
          maxWidth: "1160px",
          margin: "0 auto",
          textAlign: "center",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: isMobile ? "14px" : "18px",
          width: "100%",
        }}
      >
        {/* Emblem Crest Presentation */}
        <div style={{ position: "relative", marginBottom: "2px" }}>
          <div
            style={{
              position: "absolute",
              inset: isMobile ? "-10px" : "-14px",
              background: "radial-gradient(circle, rgba(56, 189, 248, 0.28) 0%, rgba(37, 99, 235, 0.1) 50%, transparent 75%)",
              filter: "blur(14px)",
              borderRadius: "50%",
              zIndex: 0,
            }}
          />
          <div
            style={{
              position: "relative",
              zIndex: 1,
              width: isMobile ? "54px" : "68px",
              height: isMobile ? "54px" : "68px",
              borderRadius: isMobile ? "14px" : "18px",
              background: "var(--bg-surface)",
              border: "1px solid var(--border-medium)",
              boxShadow: "0 8px 24px rgba(37, 99, 235, 0.16)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <AtlasEmblem size={isMobile ? 38 : 48} glow={true} />
          </div>
        </div>

        {/* Telemetry pill */}
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            background: "var(--bg-surface-card)",
            border: "1px solid var(--border-medium)",
            borderRadius: "30px",
            padding: isMobile ? "4px 10px" : "5px 14px",
            fontSize: isMobile ? "9.5px" : "11px",
            color: "var(--text-secondary)",
            fontWeight: 600,
            boxShadow: "var(--card-shadow)",
            maxWidth: "100%",
            textAlign: "center",
            lineHeight: 1.3,
          }}
        >
          <span className="live-dot-green" />
          <span>24/7 AUTONOMOUS FINANCIAL OS · FEED &lt;4MS</span>
        </div>

        {/* Hero Title */}
        <h1
          style={{
            fontSize: isMobile ? "26px" : "clamp(34px, 5.5vw, 56px)",
            fontWeight: 900,
            letterSpacing: "-0.03em",
            lineHeight: isMobile ? 1.2 : 1.12,
            color: "var(--text-primary)",
            maxWidth: "960px",
            margin: 0,
          }}
        >
          The Autonomous Multi-Agent Operating System for Financial Markets
        </h1>

        {/* Hero Subtitle */}
        <p
          style={{
            fontSize: isMobile ? "13px" : "clamp(15px, 2vw, 17px)",
            color: "var(--text-secondary)",
            lineHeight: 1.55,
            maxWidth: "760px",
            margin: 0,
          }}
        >
          A secure, persistent 24/7 multi-agent operating system that continuously monitors order flow, synthesizes algorithmic opportunities, manages risk, communicates via WhatsApp &amp; Telegram, and executes broker actions <strong>strictly under explicit policy and human approval controls</strong>.
        </p>

        {/* Primary CTAs */}
        <div
          style={{
            display: "flex",
            gap: "10px",
            flexDirection: isMobile ? "column" : "row",
            width: isMobile ? "100%" : "auto",
            justifyContent: "center",
            marginTop: "6px",
          }}
        >
          <button
            onClick={onLaunchCockpit}
            style={{
              background: "var(--accent-blue)",
              border: "none",
              color: "#ffffff",
              borderRadius: "8px",
              padding: isMobile ? "13px 20px" : "12px 28px",
              fontSize: "13.5px",
              fontWeight: 800,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
              boxShadow: "0 4px 16px rgba(37, 99, 235, 0.35)",
              width: isMobile ? "100%" : "auto",
            }}
          >
            <ZapIcon size={16} color="#ffffff" />
            <span>Launch Trading Cockpit</span>
          </button>

          <a
            href="#demo"
            style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border-medium)",
              color: "var(--text-primary)",
              borderRadius: "8px",
              padding: isMobile ? "12px 20px" : "12px 24px",
              fontSize: "13.5px",
              fontWeight: 700,
              textDecoration: "none",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
              width: isMobile ? "100%" : "auto",
            }}
          >
            <RadarIcon size={15} color="var(--accent-blue)" />
            <span>Interactive Swarm Demo</span>
          </a>
        </div>

        {/* 4 Pillars Stat Strip */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: isMobile ? "1fr 1fr" : "repeat(auto-fit, minmax(200px, 1fr))",
            gap: isMobile ? "8px" : "12px",
            width: "100%",
            marginTop: isMobile ? "20px" : "32px",
          }}
        >
          {[
            { label: "AGENT PERMISSIONS", val: "7 Segregated Nodes", sub: "Strict Least-Privilege" },
            { label: "HUMAN APPROVAL GATE", val: "Cryptographic Tokens", sub: "Web + WhatsApp Sign-off" },
            { label: "DATA LOG ENGINE", val: "24/7 Kafka Streams", sub: "Redpanda Event Loops" },
            { label: "SECURITY ENVELOPE", val: "AES-256-GCM Vault", sub: "Local KMS Key Store" },
          ].map((item, idx) => (
            <div
              key={idx}
              style={{
                background: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "8px",
                padding: isMobile ? "10px 12px" : "14px 16px",
                textAlign: "left",
                boxShadow: "var(--card-shadow)",
              }}
            >
              <div style={{ fontSize: isMobile ? "8.5px" : "9.5px", fontWeight: 700, color: "var(--text-muted)", letterSpacing: "0.06em" }}>
                {item.label}
              </div>
              <div style={{ fontSize: isMobile ? "13px" : "16px", fontWeight: 800, color: "var(--text-primary)", marginTop: "3px" }}>
                {item.val}
              </div>
              <div style={{ fontSize: isMobile ? "9.5px" : "11px", color: "var(--accent-blue)", marginTop: "2px", fontWeight: 600 }}>
                {item.sub}
              </div>
            </div>
          ))}
        </div>
      </header>

      {/* ─────────────────────────────────────────────────────────────
          SECTION: INTERACTIVE SWARM SIMULATION DEMO (MOBILE TUNED)
          ───────────────────────────────────────────────────────────── */}
      <section
        id="demo"
        style={{
          background: "var(--bg-surface)",
          borderTop: "1px solid var(--border-subtle)",
          borderBottom: "1px solid var(--border-subtle)",
          padding: isMobile ? "40px 14px" : "64px 24px",
        }}
      >
        <div style={{ maxWidth: "1160px", margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: isMobile ? "24px" : "32px" }}>
            <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--accent-blue)", letterSpacing: "0.08em" }}>
              LIVE DELIBERATION ENGINE
            </span>
            <h2 style={{ fontSize: isMobile ? "22px" : "28px", fontWeight: 800, marginTop: "6px", color: "var(--text-primary)" }}>
              Test the 7-Node Multi-Agent Swarm
            </h2>
            <p style={{ fontSize: isMobile ? "12.5px" : "14px", color: "var(--text-secondary)", maxWidth: "600px", margin: "6px auto 0", lineHeight: 1.5 }}>
              Trigger a live algorithmic synthesis. Watch the Market, News, and Risk nodes analyze data, the Critic stress-test vulnerabilities, and the Human Gate halt execution for your approval.
            </p>
          </div>

          {/* Interactive Demo Card */}
          <div
            style={{
              background: "var(--bg-surface-elevated)",
              border: "1px solid var(--border-medium)",
              borderRadius: "12px",
              padding: isMobile ? "14px" : "20px",
              boxShadow: "var(--card-shadow)",
            }}
          >
            {/* Asset Selector & Run Button */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                flexDirection: isMobile ? "column" : "row",
                gap: "12px",
                borderBottom: "1px solid var(--border-subtle)",
                paddingBottom: "14px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap", width: isMobile ? "100%" : "auto" }}>
                <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", width: isMobile ? "100%" : "auto" }}>
                  Target Asset:
                </span>
                {(["BTC", "ETH", "SOL"] as const).map((a) => (
                  <button
                    key={a}
                    onClick={() => setActiveAsset(a)}
                    style={{
                      background: activeAsset === a ? "var(--accent-blue)" : "var(--bg-surface)",
                      color: activeAsset === a ? "#ffffff" : "var(--text-secondary)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "5px",
                      padding: "5px 10px",
                      fontSize: "11px",
                      fontWeight: 700,
                      cursor: "pointer",
                      flex: isMobile ? 1 : "initial",
                      textAlign: "center",
                    }}
                  >
                    {a} (${prices[a].price.toLocaleString()})
                  </button>
                ))}
              </div>

              <button
                onClick={handleRunDemo}
                disabled={isSimulating}
                style={{
                  background: isSimulating ? "var(--bg-surface)" : "var(--accent-blue)",
                  color: isSimulating ? "var(--text-muted)" : "#ffffff",
                  border: "none",
                  borderRadius: "6px",
                  padding: "10px 18px",
                  fontSize: "12px",
                  fontWeight: 700,
                  cursor: isSimulating ? "not-allowed" : "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "6px",
                  width: isMobile ? "100%" : "auto",
                }}
              >
                <ZapIcon size={13} color="currentColor" />
                <span>{isSimulating ? "Deliberating..." : "Run Swarm Deliberation"}</span>
              </button>
            </div>

            {/* Pipeline Stage Indicators */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: isMobile ? "repeat(2, 1fr)" : "repeat(auto-fit, minmax(130px, 1fr))",
                gap: "6px",
                margin: "14px 0",
              }}
            >
              {[
                { stage: 1, name: "Manager", desc: "0 Broker Access" },
                { stage: 2, name: "Market", desc: "L2 & CVD (READ)" },
                { stage: 3, name: "News", desc: "Macro (READ)" },
                { stage: 4, name: "Risk", desc: "VaR (HARD VETO)" },
                { stage: 5, name: "Decision", desc: "EV Setup (ANALYZE)" },
                { stage: 6, name: "Critic", desc: "Devil's Advocate" },
                { stage: 7, name: "Policy", desc: "Ticket Issued" },
                { stage: 8, name: "Execution", desc: "Broker Filled" },
              ].map((s) => {
                const isPassed = simulationStep >= s.stage;
                const isCurrent = simulationStep === s.stage;
                return (
                  <div
                    key={s.stage}
                    style={{
                      background: isCurrent ? "var(--accent-blue-subtle)" : "var(--bg-surface)",
                      border: `1px solid ${isCurrent ? "var(--accent-blue)" : isPassed ? "#10b981" : "var(--border-subtle)"}`,
                      borderRadius: "6px",
                      padding: "8px",
                      fontSize: "10.5px",
                      transition: "all 0.2s ease",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <span style={{ fontWeight: 700, color: isCurrent ? "var(--accent-blue)" : isPassed ? "#10b981" : "var(--text-muted)" }}>
                        {s.name}
                      </span>
                      {isPassed && <CheckIcon size={11} color="#10b981" />}
                    </div>
                    <span style={{ fontSize: "9px", color: "var(--text-muted)", display: "block", marginTop: "2px" }}>
                      {s.desc}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Simulation Log Terminal */}
            <div
              style={{
                background: "var(--bg-canvas)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "6px",
                padding: "10px 12px",
                fontFamily: "var(--font-mono)",
                fontSize: "10.5px",
                lineHeight: "17px",
                minHeight: "110px",
                maxHeight: "180px",
                overflowY: "auto",
                display: "flex",
                flexDirection: "column",
                gap: "3px",
              }}
            >
              {simLogs.length === 0 ? (
                <span style={{ color: "var(--text-muted)" }}>
                  Click &ldquo;Run Swarm Deliberation&rdquo; above to synthesize algorithmic trade proposals across all 7 agent nodes.
                </span>
              ) : (
                simLogs.map((log, idx) => (
                  <span key={idx} style={{ color: log.includes("FILLED") ? "#10b981" : log.includes("HUMAN") ? "#f59e0b" : "var(--text-primary)", wordBreak: "break-word" }}>
                    {log}
                  </span>
                ))
              )}
            </div>

            {/* Human Gate Trigger Banner if stage 7 reached */}
            {simulationStep === 7 && (
              <div
                style={{
                  marginTop: "12px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  flexDirection: isMobile ? "column" : "row",
                  gap: "10px",
                  background: "rgba(245, 158, 11, 0.12)",
                  border: "1px solid rgba(245, 158, 11, 0.3)",
                  borderRadius: "6px",
                  padding: "10px 12px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "11.5px", color: "var(--text-primary)", textAlign: isMobile ? "left" : "inherit" }}>
                  <ShieldIcon size={14} color="#f59e0b" />
                  <span><strong>Ticket #TICKET-8842 Issued:</strong> Execution Agent locked awaiting operator sign-off.</span>
                </div>
                <button
                  onClick={handleSimulateHumanApproval}
                  style={{
                    background: "#10b981",
                    color: "#ffffff",
                    border: "none",
                    borderRadius: "5px",
                    padding: "8px 16px",
                    fontSize: "12px",
                    fontWeight: 800,
                    cursor: "pointer",
                    width: isMobile ? "100%" : "auto",
                  }}
                >
                  Sign Off &amp; Execute (1-Click)
                </button>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────
          SECTION: ARCHITECTURE BLUEPRINT (MOBILE TUNED)
          ───────────────────────────────────────────────────────────── */}
      <section
        id="architecture"
        style={{
          padding: isMobile ? "40px 14px" : "72px 24px",
          maxWidth: "1160px",
          margin: "0 auto",
          width: "100%",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: isMobile ? "24px" : "36px" }}>
          <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--accent-blue)", letterSpacing: "0.08em" }}>
            SYSTEM ARCHITECTURE
          </span>
          <h2 style={{ fontSize: isMobile ? "22px" : "28px", fontWeight: 800, marginTop: "6px", color: "var(--text-primary)" }}>
            Zero-Trust Segregation of Duties
          </h2>
          <p style={{ fontSize: isMobile ? "12.5px" : "14px", color: "var(--text-secondary)", maxWidth: "680px", margin: "6px auto 0", lineHeight: 1.5 }}>
            In Atlas AI, the Manager Agent coordinates without broker access. The Execution Agent executes without strategy autonomy. Risk has an unbendable constitutional veto.
          </p>
        </div>

        {/* Visual Architecture Flow Diagram */}
        <div
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border-medium)",
            borderRadius: "12px",
            padding: isMobile ? "16px 12px" : "28px",
            boxShadow: "var(--card-shadow)",
            display: "flex",
            flexDirection: "column",
            gap: "16px",
          }}
        >
          {/* Layer 1: Manager */}
          <div style={{ display: "flex", justifyContent: "center" }}>
            <div style={{ background: "var(--bg-surface-elevated)", border: "1px solid var(--accent-blue)", borderRadius: "8px", padding: "10px 16px", textAlign: "center", width: "100%", maxWidth: "340px" }}>
              <strong style={{ color: "var(--accent-blue)", fontSize: "12.5px" }}>Manager Agent (Orchestrator)</strong>
              <div style={{ fontSize: "10.5px", color: "var(--text-muted)", marginTop: "2px" }}>Permission: COORDINATE · Zero Broker Access</div>
            </div>
          </div>

          <div style={{ textAlign: "center", color: "var(--text-muted)", fontSize: "12px" }}>↓</div>

          {/* Layer 2: Analysis Triad */}
          <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "repeat(auto-fit, minmax(220px, 1fr))", gap: "8px" }}>
            <div style={{ background: "var(--bg-surface-elevated)", border: "1px solid var(--border-subtle)", borderRadius: "8px", padding: "10px 12px", textAlign: isMobile ? "left" : "center" }}>
              <strong style={{ color: "var(--text-primary)", fontSize: "12px" }}>Market Agent</strong>
              <div style={{ fontSize: "10px", color: "var(--text-muted)", marginTop: "2px" }}>Permission: READ (L2 Depth &amp; CVD)</div>
            </div>
            <div style={{ background: "var(--bg-surface-elevated)", border: "1px solid var(--border-subtle)", borderRadius: "8px", padding: "10px 12px", textAlign: isMobile ? "left" : "center" }}>
              <strong style={{ color: "var(--text-primary)", fontSize: "12px" }}>News Agent</strong>
              <div style={{ fontSize: "10px", color: "var(--text-muted)", marginTop: "2px" }}>Permission: READ/ANALYZE (Macro Calendars)</div>
            </div>
            <div style={{ background: "var(--bg-surface-elevated)", border: "1px solid var(--border-subtle)", borderRadius: "8px", padding: "10px 12px", textAlign: isMobile ? "left" : "center" }}>
              <strong style={{ color: "#f43f5e", fontSize: "12px" }}>Risk Agent</strong>
              <div style={{ fontSize: "10px", color: "var(--text-muted)", marginTop: "2px" }}>Permission: ANALYZE &amp; HARD VETO (VaR Caps)</div>
            </div>
          </div>

          <div style={{ textAlign: "center", color: "var(--text-muted)", fontSize: "12px" }}>↓</div>

          {/* Layer 3: Decision & Critic */}
          <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr", gap: "8px" }}>
            <div style={{ background: "var(--bg-surface-elevated)", border: "1px solid var(--border-subtle)", borderRadius: "8px", padding: "10px 12px", textAlign: isMobile ? "left" : "center" }}>
              <strong style={{ color: "#38bdf8", fontSize: "12px" }}>Decision Agent</strong>
              <div style={{ fontSize: "10px", color: "var(--text-muted)", marginTop: "2px" }}>Permission: ANALYZE (Synthesizes 1:2 R:R Setups)</div>
            </div>
            <div style={{ background: "var(--bg-surface-elevated)", border: "1px solid var(--border-subtle)", borderRadius: "8px", padding: "10px 12px", textAlign: isMobile ? "left" : "center" }}>
              <strong style={{ color: "#f59e0b", fontSize: "12px" }}>Critic Agent</strong>
              <div style={{ fontSize: "10px", color: "var(--text-muted)", marginTop: "2px" }}>Permission: CRITIQUE (Devil&apos;s Advocate Stress-Test)</div>
            </div>
          </div>

          <div style={{ textAlign: "center", color: "var(--text-muted)", fontSize: "12px" }}>↓</div>

          {/* Layer 4: Policy Engine & Human Approval */}
          <div style={{ display: "flex", justifyContent: "center" }}>
            <div style={{ background: "rgba(245, 158, 11, 0.12)", border: "1px solid rgba(245, 158, 11, 0.35)", borderRadius: "8px", padding: isMobile ? "10px 12px" : "12px 28px", textAlign: "center", width: "100%", maxWidth: "440px" }}>
              <strong style={{ color: "#f59e0b", fontSize: "12.5px" }}>Policy Engine &amp; Human Approval</strong>
              <div style={{ fontSize: "10.5px", color: "var(--text-secondary)", marginTop: "2px" }}>Risk &le; 1.5% · Drawdown cap 3.0% · Cryptographic Sign-off</div>
            </div>
          </div>

          <div style={{ textAlign: "center", color: "var(--text-muted)", fontSize: "12px" }}>↓</div>

          {/* Layer 5: Execution Agent & Brokers */}
          <div style={{ display: "flex", justifyContent: "center" }}>
            <div style={{ background: "rgba(16, 185, 129, 0.12)", border: "1px solid rgba(16, 185, 129, 0.35)", borderRadius: "8px", padding: isMobile ? "12px" : "14px 28px", textAlign: "center", width: "100%", maxWidth: "520px" }}>
              <strong style={{ color: "#10b981", fontSize: "13px" }}>Execution Agent (EXECUTE ONLY)</strong>
              <div style={{ fontSize: "10.5px", color: "var(--text-secondary)", marginTop: "4px" }}>
                Exclusive broker adapter: <strong>Binance</strong>, <strong>OANDA</strong>, and <strong>MT5 Bridge</strong>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────
          SECTION: THE 8 FLAGSHIP PILLARS (MOBILE TUNED)
          ───────────────────────────────────────────────────────────── */}
      <section
        id="pillars"
        style={{
          background: "var(--bg-surface)",
          borderTop: "1px solid var(--border-subtle)",
          borderBottom: "1px solid var(--border-subtle)",
          padding: isMobile ? "40px 14px" : "72px 24px",
        }}
      >
        <div style={{ maxWidth: "1160px", margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: isMobile ? "24px" : "36px" }}>
            <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--accent-blue)", letterSpacing: "0.08em" }}>
              FLAGSHIP CAPABILITIES
            </span>
            <h2 style={{ fontSize: isMobile ? "22px" : "28px", fontWeight: 800, marginTop: "6px", color: "var(--text-primary)" }}>
              The 8 Pillars of Atlas AI
            </h2>
          </div>

          {/* 8 Cards Grid */}
          <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "repeat(auto-fit, minmax(260px, 1fr))", gap: isMobile ? "10px" : "16px" }}>
            {[
              {
                num: "01",
                title: "Role-Based Agent Permissions",
                badge: "LEAST PRIVILEGE",
                desc: "No single agent holds power to both formulate and execute trades. Manager coordinates without credentials. Execution agent has no strategy autonomy.",
              },
              {
                num: "02",
                title: "Cryptographic Human Approval Gate",
                badge: "ZERO SURPRISES",
                desc: "Trades above risk threshold halt execution. Users sign off via Cockpit UI or two-way WhatsApp / Telegram commands (YES/HAAN).",
              },
              {
                num: "03",
                title: "24/7 Event-Driven Kafka Loop",
                badge: "REDPANDA PIPELINE",
                desc: "Continuous asynchronous stream loops consume market.ticks, orderbook.imbalances, macro.calendar, and drawdown telemetry without busy polling.",
              },
              {
                num: "04",
                title: "Persistent State Graphs",
                badge: "ZERO LOSS RECOVERY",
                desc: "State snapshots saved at each LangGraph step. If a worker container crashes, recover_workflow() resumes from the exact checkpoint without re-runs.",
              },
              {
                num: "05",
                title: "Model Context Protocol (MCP)",
                badge: "OPEN STANDARDS",
                desc: "Standard MCPServer exposes tool schemas (orderbook, news, VaR, trade dispatch) allowing agents to discover and invoke tools over MCP protocol.",
              },
              {
                num: "06",
                title: "Agent-to-Agent (A2A) Protocol",
                badge: "SPECIALIST DELEGATION",
                desc: "Discover, delegate, and collaborate with external specialist agents (Macro Sentinel, Whale Tracker, Quant Vol Surface) adhering to a2a-protocol.org.",
              },
              {
                num: "07",
                title: "AI Trading Journal",
                badge: "7-PART AUDIT TRAIL",
                desc: "Every trade stores an immutable record: Market State → Observations → Decision → Risk Assessment → Approval Token → Execution → Outcome.",
              },
              {
                num: "08",
                title: "Historical Scenario Evaluation",
                badge: "CRISIS STRESS-TESTS",
                desc: "Evaluates agent swarm against black-swan historical shocks (FTX Crash, SVB Run, LUNA De-peg) verifying >96% accuracy and 0 risk violations.",
              },
            ].map((p) => (
              <div
                key={p.num}
                style={{
                  background: "var(--bg-surface-elevated)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "10px",
                  padding: isMobile ? "16px" : "20px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "8px",
                  boxShadow: "var(--card-shadow)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "15px", fontWeight: 900, color: "var(--accent-blue)", fontFamily: "var(--font-mono)" }}>
                    {p.num}
                  </span>
                  <span style={{ fontSize: "8.5px", fontWeight: 800, background: "var(--bg-surface-card)", border: "1px solid var(--border-subtle)", padding: "2px 6px", borderRadius: "3px", color: "var(--text-muted)" }}>
                    {p.badge}
                  </span>
                </div>
                <h3 style={{ fontSize: "13.5px", fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
                  {p.title}
                </h3>
                <p style={{ fontSize: "11.5px", color: "var(--text-secondary)", lineHeight: 1.5, margin: 0 }}>
                  {p.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────
          SECTION: PRICING & TIERS (MOBILE TUNED)
          ───────────────────────────────────────────────────────────── */}
      <section
        id="pricing"
        style={{
          padding: isMobile ? "40px 14px" : "72px 24px",
          maxWidth: "1160px",
          margin: "0 auto",
          width: "100%",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: isMobile ? "24px" : "36px" }}>
          <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--accent-blue)", letterSpacing: "0.08em" }}>
            TRANSPARENT ACCESS
          </span>
          <h2 style={{ fontSize: isMobile ? "22px" : "28px", fontWeight: 800, marginTop: "6px", color: "var(--text-primary)" }}>
            Institutional Trading Tiers
          </h2>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "repeat(auto-fit, minmax(280px, 1fr))", gap: isMobile ? "16px" : "20px" }}>
          {[
            {
              tier: "COMMUNITY EDITION",
              price: "$0",
              period: "Forever Free",
              badge: "PAPER TRADING",
              features: [
                "Unlimited Paper Trading Simulator",
                "Real Binance L2 Depth & 15m Klines",
                "Built-in VIP Quant Engine (No API key needed)",
                "Full Technical Audit & CVD Absorption Radar",
                "Telegram Bot Approval Webhooks",
              ],
              cta: "Start Free Paper Trading",
              highlight: false,
            },
            {
              tier: "PRO QUANT OPERATOR",
              price: "$99",
              period: "/ month",
              badge: "MOST POPULAR",
              features: [
                "All Community Edition features",
                "Live Multi-Exchange Execution (Binance, OANDA, MT5)",
                "Meta Cloud WhatsApp Push Notifications",
                "Continuous 15m Automated Swarm Scans",
                "KMS Envelope Encrypted Credential Vault",
                "AI Trading Journal with MFE/MAE Analytics",
              ],
              cta: "Launch Pro Operator",
              highlight: true,
            },
            {
              tier: "HEDGE FUND ENTERPRISE",
              price: "Custom",
              period: "Bespoke SLA",
              badge: "INSTITUTIONAL",
              features: [
                "Dedicated On-Premises Redpanda Cluster",
                "Custom A2A Specialist Agent Directory",
                "Hardware Security Module (HSM) Key Vault",
                "Sub-millisecond Co-located Execution Routing",
                "Custom Crisis Scenario Evaluation Suite",
                "24/7 Dedicated Quant Engineering Support",
              ],
              cta: "Contact Institutional Desk",
              highlight: false,
            },
          ].map((t, idx) => (
            <div
              key={idx}
              style={{
                background: "var(--bg-surface)",
                border: t.highlight ? "2px solid var(--accent-blue)" : "1px solid var(--border-subtle)",
                borderRadius: "12px",
                padding: isMobile ? "20px" : "24px",
                display: "flex",
                flexDirection: "column",
                position: "relative",
                boxShadow: "var(--card-shadow)",
              }}
            >
              {t.highlight && (
                <span
                  style={{
                    position: "absolute",
                    top: "-10px",
                    right: "20px",
                    background: "var(--accent-blue)",
                    color: "#ffffff",
                    fontSize: "9px",
                    fontWeight: 800,
                    padding: "2px 8px",
                    borderRadius: "4px",
                  }}
                >
                  {t.badge}
                </span>
              )}
              <span style={{ fontSize: "10.5px", fontWeight: 700, color: "var(--text-muted)" }}>{t.tier}</span>
              <div style={{ display: "flex", alignItems: "baseline", gap: "6px", margin: "8px 0 14px" }}>
                <span style={{ fontSize: isMobile ? "28px" : "32px", fontWeight: 900, color: "var(--text-primary)" }}>{t.price}</span>
                <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>{t.period}</span>
              </div>
              <ul style={{ listStyle: "none", padding: 0, margin: "0 0 20px", display: "flex", flexDirection: "column", gap: "9px", flex: 1 }}>
                {t.features.map((f, fIdx) => (
                  <li key={fIdx} style={{ display: "flex", alignItems: "flex-start", gap: "8px", fontSize: "11.5px", color: "var(--text-secondary)" }}>
                    <CheckIcon size={12} color="#10b981" />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
              <button
                onClick={onLaunchCockpit}
                style={{
                  background: t.highlight ? "var(--accent-blue)" : "var(--bg-surface-elevated)",
                  color: t.highlight ? "#ffffff" : "var(--text-primary)",
                  border: t.highlight ? "none" : "1px solid var(--border-medium)",
                  borderRadius: "6px",
                  padding: "11px 0",
                  fontSize: "12.5px",
                  fontWeight: 700,
                  cursor: "pointer",
                  width: "100%",
                }}
              >
                {t.cta}
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────
          FOOTER (MOBILE & DESKTOP TUNED)
          ───────────────────────────────────────────────────────────── */}
      <footer
        style={{
          background: "var(--bg-surface)",
          borderTop: "1px solid var(--border-subtle)",
          padding: isMobile ? "24px 14px" : "32px 24px",
          marginTop: "auto",
        }}
      >
        <div
          style={{
            maxWidth: "1160px",
            margin: "0 auto",
            display: "flex",
            justifyContent: "space-between",
            alignItems: isMobile ? "flex-start" : "center",
            flexDirection: isMobile ? "column" : "row",
            gap: isMobile ? "16px" : "20px",
            fontSize: "12px",
            color: "var(--text-muted)",
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <AtlasLogo size="sm" showText={true} subtext="Version 2.5 QUANT" />
            <div style={{ fontSize: "10.5px", color: "var(--text-muted)", maxWidth: "480px", lineHeight: 1.5 }}>
              Trading involves substantial risk of loss. Always enforce strict risk gates and never risk funds you cannot afford to lose.
            </div>
          </div>

          <div style={{ display: "flex", gap: isMobile ? "12px" : "16px", flexWrap: "wrap", fontSize: isMobile ? "11.5px" : "12px" }}>
            <a href="/architecture" style={{ color: "inherit", textDecoration: "none" }}>Architecture</a>
            <a href="/security" style={{ color: "inherit", textDecoration: "none" }}>Security</a>
            <a href="/pricing" style={{ color: "inherit", textDecoration: "none" }}>Pricing</a>
            <a href="/docs" style={{ color: "inherit", textDecoration: "none" }}>Docs</a>
            <span onClick={onLaunchCockpit} style={{ color: "var(--accent-blue)", cursor: "pointer", fontWeight: 700 }}>
              Launch Cockpit →
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default LandingPageView;
