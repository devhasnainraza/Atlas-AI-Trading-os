"use client";

import React, { useState, useEffect } from "react";
import { soundManager } from "../lib/soundEffects";
import { AtlasLogo, AtlasEmblem } from "./AtlasLogo";
import { BellIcon, VolumeIcon, VolumeMuteIcon, AlertTriangleIcon, ZapIcon, ShieldIcon, LogOutIcon, SunIcon, MoonIcon, SendIcon } from "./Icons";

interface HeaderProps {
  activeView: string;
  setActiveView: (view: string) => void;
  circuitStatus?: "NORMAL" | "ALERT" | "HALTED";
  onEmergencyFlatten?: () => void;
  onResetCircuit?: () => void;
  openPositionsCount?: number;
  onOpenCopilot?: () => void;
  onOpenAlerts?: () => void;
  onOpenOmnichannel?: () => void;
  unreadAlertsCount?: number;
  user?: { id: string; email: string; name: string } | null;
  onOpenAuth?: () => void;
  onLogout?: () => void;
  theme?: "dark" | "light";
  onToggleTheme?: () => void;
}

export function HeaderHUD({
  activeView,
  setActiveView,
  circuitStatus = "NORMAL",
  onEmergencyFlatten = () => { },
  onResetCircuit = () => { },
  openPositionsCount = 0,
  onOpenCopilot = () => { },
  onOpenAlerts = () => { },
  onOpenOmnichannel,
  unreadAlertsCount = 0,
  user = null,
  onOpenAuth = () => { },
  onLogout = () => { },
  theme = "light",
  onToggleTheme,
}: HeaderProps) {
  const [showKillModal, setShowKillModal] = useState(false);
  const [isAudioMuted, setIsAudioMuted] = useState(false);
  const [isMoreMenuOpen, setIsMoreMenuOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    setIsAudioMuted(soundManager.isMuted());
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  const handleToggleAudio = () => {
    const muted = soundManager.toggleMute();
    setIsAudioMuted(muted);
    if (!muted) {
      soundManager.playClick();
    }
  };

  const primaryTabs = [
    { id: "cockpit", label: "Cockpit" },
    { id: "ai-command", label: "AI Command" },
    { id: "automation", label: "Automation" },
    { id: "journal", label: "Journal" },
    { id: "vault", label: "Vault" },
  ];

  const handleConfirmFlatten = () => {
    onEmergencyFlatten();
    setShowKillModal(false);
  };

  return (
    <>
      {isMobile ? (
        <header
          style={{
            height: "46px",
            background: "var(--bg-surface)",
            backdropFilter: "blur(20px)",
            WebkitBackdropFilter: "blur(20px)",
            borderBottom: "1px solid var(--border-subtle)",
            boxShadow: "0 1px 3px rgba(0, 0, 0, 0.05)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0 12px",
            flexShrink: 0,
            zIndex: 40,
          }}
        >
          {/* Mobile Left: Brand */}
          <a
            href="/"
            style={{ display: "flex", alignItems: "center", textDecoration: "none" }}
            title="Atlas OS Home"
          >
            <AtlasLogo size="sm" showText={true} subtext="INSTITUTIONAL QUANT" />
          </a>

          {/* Mobile Right: Copilot + Theme + Alerts + Flatten + Menu */}
          <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
            {/* Quick Copilot Trigger Button */}
            <button
              onClick={() => {
                soundManager.playCopilotChime();
                onOpenCopilot();
              }}
              style={{
                background: "var(--bg-surface-elevated)",
                border: "1px solid var(--border-subtle)",
                color: "var(--accent-blue)",
                borderRadius: "5px",
                padding: "4px 8px",
                fontSize: "10px",
                fontWeight: 700,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "4px",
              }}
              title="Summon Copilot"
            >
              <ZapIcon size={11} color="var(--accent-blue)" />
              <span>AI</span>
            </button>

            {/* Mobile Theme Toggle Button */}
            {onToggleTheme && (
              <button
                onClick={() => {
                  soundManager.playClick();
                  onToggleTheme();
                }}
                style={{
                  background: "var(--bg-surface-elevated)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "5px",
                  padding: "4px 7px",
                  color: "var(--text-secondary)",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
                title={theme === "light" ? "Switch to Dark Mode" : "Switch to Light Mode"}
              >
                {theme === "light" ? <MoonIcon size={12} color="var(--text-secondary)" /> : <SunIcon size={12} color="var(--accent-amber)" />}
              </button>
            )}

            {/* Alerts Bell Button */}
            <button
              onClick={() => {
                soundManager.playClick();
                onOpenAlerts();
              }}
              style={{
                background: "var(--bg-surface-elevated)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "5px",
                padding: "4px 7px",
                color: unreadAlertsCount > 0 ? "var(--accent-amber)" : "var(--text-secondary)",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "3px",
              }}
              title="Alerts Sentinel"
            >
              <BellIcon size={12} color={unreadAlertsCount > 0 ? "var(--accent-amber)" : "var(--text-secondary)"} />
              {unreadAlertsCount > 0 && (
                <span style={{ fontSize: "9px", fontWeight: 700 }}>{unreadAlertsCount}</span>
              )}
            </button>

            {/* Mobile Omnichannel Channels Button */}
            {onOpenOmnichannel && (
              <button
                onClick={() => {
                  soundManager.playClick();
                  onOpenOmnichannel();
                }}
                style={{
                  background: "var(--bg-surface-elevated)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "5px",
                  padding: "4px 7px",
                  color: "var(--accent-blue)",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
                title="Omnichannel Channels & Alerts"
              >
                <SendIcon size={12} color="var(--accent-blue)" />
              </button>
            )}

            {/* Quick Kill Switch Button */}
            <button
              onClick={() => setShowKillModal(true)}
              style={{
                background: "rgba(239, 68, 68, 0.12)",
                border: "1px solid rgba(239, 68, 68, 0.3)",
                color: "#ef4444",
                borderRadius: "5px",
                padding: "4px 7px",
                fontSize: "9px",
                fontWeight: 700,
                cursor: "pointer",
              }}
              title="Emergency Flatten"
            >
              FLATTEN
            </button>

            {/* Mobile Hamburger Menu Drawer Toggle */}
            <button
              onClick={() => {
                soundManager.playClick();
                setIsMobileMenuOpen(!isMobileMenuOpen);
              }}
              style={{
                background: isMobileMenuOpen ? "var(--accent-blue-subtle)" : "var(--bg-surface-elevated)",
                border: `1px solid ${isMobileMenuOpen ? "var(--accent-blue-border)" : "var(--border-subtle)"}`,
                borderRadius: "5px",
                padding: "4px 7px",
                color: "var(--text-primary)",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
              title="Open Navigation Menu"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </button>
          </div>
        </header>
      ) : (
        <header
          style={{
            height: "42px",
            background: "var(--bg-surface)",
            borderBottom: "1px solid var(--border-subtle)",
            boxShadow: "inset 0 1px 0 0 var(--border-highlight)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0 14px",
            flexShrink: 0,
            zIndex: 40,
          }}
        >
          {/* Left: Brand + Clean Primary Workspaces */}
          <div style={{ display: "flex", alignItems: "center", gap: "12px", flexShrink: 0 }}>
            {/* Logo — click to open Landing / Home Page */}
            <a
              href="/"
              style={{ display: "flex", alignItems: "center", textDecoration: "none" }}
              title="Atlas OS Home & Landing Page"
            >
              <AtlasLogo size="sm" showText={true} />
            </a>

            {/* Segmented View Switcher Tabs (Primary 5 Workspaces) */}
            <nav
              className="scroll-x"
              style={{
                display: "flex",
                alignItems: "center",
                gap: "2px",
                background: "var(--bg-surface-card)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "5px",
                padding: "2px",
                position: "relative",
                flexShrink: 0,
              }}
            >
              {primaryTabs.map((tab) => {
                const isActive = activeView === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => {
                      soundManager.playClick();
                      setIsMoreMenuOpen(false);
                      setActiveView(tab.id);
                    }}
                    style={{
                      background: isActive ? "var(--bg-surface-elevated)" : "transparent",
                      color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
                      border: isActive ? "1px solid var(--border-medium)" : "1px solid transparent",
                      borderRadius: "3px",
                      padding: "3px 8px",
                      fontSize: "10.5px",
                      fontWeight: isActive ? 600 : 500,
                      cursor: "pointer",
                      transition: "color 0.1s ease, background 0.1s ease",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {tab.label}
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Center: Clean Spotlight Command & Market Session Telemetry */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              fontSize: "10.5px",
              color: "var(--text-muted)",
              whiteSpace: "nowrap",
              flexShrink: 1,
            }}
          >
            {/* Institutional Copilot Spotlight Command Button */}
            <button
              onClick={() => {
                soundManager.playCopilotChime();
                onOpenCopilot();
              }}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "5px",
                background: "var(--bg-surface-elevated)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "4px",
                padding: "3px 8px",
                cursor: "pointer",
                transition: "border-color 0.15s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "var(--border-medium)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "var(--border-subtle)";
              }}
              title="Summon Atlas Copilot (Ctrl+K)"
            >
              <ZapIcon size={11} color="var(--accent-blue)" />
              <span className="nav-copilot-text" style={{ fontSize: "10.5px", color: "var(--text-secondary)", fontWeight: 600 }}>
                Copilot
              </span>
              <span className="kbd-badge">Ctrl+K</span>
            </button>

            {/* Clean Session & Latency Chip */}
            <div
              className="nav-latency-chip"
              style={{
                display: "flex",
                alignItems: "center",
                gap: "5px",
                background: "var(--bg-surface-card)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "4px",
                padding: "2px 7px",
              }}
            >
              <span className="live-dot-green" />
              <span style={{ color: "var(--text-secondary)", fontWeight: 500 }}>NY · 4ms</span>
            </div>

            {/* Macro Event Catalyst Pill */}
            <button
              className="nav-macro-pill"
              onClick={() => {
                soundManager.playClick();
                setActiveView("automation");
              }}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "5px",
                background: "var(--bg-surface-elevated)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "4px",
                padding: "2px 7px",
                color: "var(--text-secondary)",
                fontSize: "10px",
                fontWeight: 500,
                cursor: "pointer",
              }}
              title="Next Macro Catalyst: FOMC Rate Decision (Click to view Macro Sentinel)"
            >
              <span className="live-dot-amber" />
              <span>FOMC in 2h 45m</span>
            </button>
          </div>

          {/* Right: Risk Status & Kill Switch & Alerts */}
          <div style={{ display: "flex", alignItems: "center", gap: "6px", whiteSpace: "nowrap", flexShrink: 0 }}>
            {/* Circuit Breaker Pill */}
            <div
              style={{
                background: circuitStatus === "NORMAL" ? "var(--accent-green-subtle)" : "var(--accent-red-subtle)",
                border: `1px solid ${circuitStatus === "NORMAL" ? "var(--accent-green-border)" : "var(--accent-red-border)"}`,
                borderRadius: "4px",
                padding: "3px 7px",
                fontSize: "10px",
                fontWeight: 600,
                color: circuitStatus === "NORMAL" ? "var(--accent-green)" : "var(--accent-red)",
                display: "flex",
                alignItems: "center",
                gap: "5px",
                height: "28px",
              }}
            >
              <span className={circuitStatus === "NORMAL" ? "live-dot-green" : "live-dot-red"} />
              <span className="nav-gate-label">GATE: </span>
              <span>{circuitStatus}</span>
            </div>

            {/* Reset Circuit Button if Halted */}
            {circuitStatus === "HALTED" && (
              <button
                onClick={onResetCircuit}
                style={{
                  background: "var(--bg-surface-elevated)",
                  border: "1px solid var(--border-medium)",
                  color: "#f8fafc",
                  borderRadius: "4px",
                  padding: "0 8px",
                  height: "28px",
                  fontSize: "10px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                RESET GATE
              </button>
            )}

            {/* Emergency Flatten Kill Switch Button */}
            <button
              onClick={() => setShowKillModal(true)}
              style={{
                background: "rgba(244, 63, 94, 0.08)",
                border: "1px solid rgba(244, 63, 94, 0.25)",
                color: "#f43f5e",
                borderRadius: "4px",
                padding: "0 8px",
                height: "28px",
                fontSize: "10px",
                fontWeight: 700,
                letterSpacing: "0.02em",
                cursor: "pointer",
                transition: "all 0.15s ease",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "rgba(244, 63, 94, 0.16)";
                e.currentTarget.style.borderColor = "rgba(244, 63, 94, 0.4)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "rgba(244, 63, 94, 0.08)";
                e.currentTarget.style.borderColor = "rgba(244, 63, 94, 0.25)";
              }}
              title="Emergency Flatten: Liquidate all active exposure"
            >
              FLATTEN
            </button>

            {/* Alerts Bell Button */}
            <button
              onClick={() => {
                soundManager.playClick();
                onOpenAlerts();
              }}
              style={{
                width: "28px",
                height: "28px",
                background: "var(--bg-surface-elevated)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "4px",
                color: unreadAlertsCount > 0 ? "var(--accent-amber)" : "var(--text-secondary)",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                position: "relative",
                transition: "border-color 0.15s ease",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--border-medium)")}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border-subtle)")}
              title={`Alerts Sentinel (${unreadAlertsCount} active)`}
            >
              <BellIcon size={12} color="currentColor" />
              {unreadAlertsCount > 0 && (
                <span
                  style={{
                    position: "absolute",
                    top: "-2px",
                    right: "-2px",
                    background: "var(--accent-amber)",
                    color: "#000",
                    fontSize: "8px",
                    fontWeight: 800,
                    borderRadius: "50%",
                    width: "12px",
                    height: "12px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  {unreadAlertsCount}
                </span>
              )}
            </button>

            {/* Omnichannel Channels Button */}
            {onOpenOmnichannel && (
              <button
                onClick={() => {
                  soundManager.playClick();
                  onOpenOmnichannel();
                }}
                style={{
                  width: "28px",
                  height: "28px",
                  background: "var(--bg-surface-elevated)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "4px",
                  color: "var(--accent-blue)",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  transition: "border-color 0.15s ease",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--border-medium)")}
                onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border-subtle)")}
                title="Omnichannel Gateway (WhatsApp & Telegram)"
              >
                <SendIcon size={12} color="currentColor" />
              </button>
            )}

            {/* Audio Synthesizer Toggle */}
            <button
              onClick={handleToggleAudio}
              style={{
                width: "28px",
                height: "28px",
                background: "var(--bg-surface-elevated)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "4px",
                color: isAudioMuted ? "var(--text-muted)" : "var(--text-secondary)",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                transition: "border-color 0.15s ease",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--border-medium)")}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border-subtle)")}
              title={isAudioMuted ? "Unmute Audio (Synthesized Web Audio Cues)" : "Mute Audio"}
            >
              {isAudioMuted ? <VolumeMuteIcon size={12} color="currentColor" /> : <VolumeIcon size={12} color="currentColor" />}
            </button>

            {/* Desktop Theme Switcher Button */}
            {onToggleTheme && (
              <button
                onClick={() => {
                  soundManager.playClick();
                  onToggleTheme();
                }}
                style={{
                  width: "28px",
                  height: "28px",
                  background: "var(--bg-surface-elevated)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "4px",
                  color: theme === "light" ? "var(--text-secondary)" : "var(--accent-amber)",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  transition: "border-color 0.15s ease",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--border-medium)")}
                onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border-subtle)")}
                title={theme === "light" ? "Switch to Dark Mode" : "Switch to Light Mode"}
              >
                {theme === "light" ? <MoonIcon size={12} color="currentColor" /> : <SunIcon size={12} color="currentColor" />}
              </button>
            )}

            {/* User Auth Section */}
            {user ? (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  background: "var(--bg-surface-elevated)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "4px",
                  padding: "0 6px",
                  height: "28px",
                }}
              >
                <div
                  style={{
                    width: "18px",
                    height: "18px",
                    borderRadius: "50%",
                    background: "linear-gradient(135deg, #0284c7 0%, #2563eb 100%)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "8.5px",
                    fontWeight: 700,
                    color: "#fff",
                  }}
                >
                  {((user.name || user.email)?.[0] || "U").toUpperCase()}
                </div>
                <span
                  style={{
                    fontSize: "10px",
                    fontWeight: 600,
                    color: "var(--text-primary)",
                    maxWidth: "70px",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {user.name || (user.email ? user.email.split("@")[0] : "Trader")}
                </span>
                <button
                  onClick={onLogout}
                  style={{
                    background: "transparent",
                    border: "none",
                    color: "var(--text-muted)",
                    cursor: "pointer",
                    padding: "2px",
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.color = "#f43f5e")}
                  onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-muted)")}
                  title="Sign Out of Atlas OS"
                >
                  <LogOutIcon size={11} color="currentColor" />
                </button>
              </div>
            ) : (
              <button
                onClick={onOpenAuth}
                style={{
                  background: "var(--accent-blue-subtle)",
                  border: "1px solid var(--accent-blue-border)",
                  color: "var(--accent-blue)",
                  borderRadius: "4px",
                  padding: "0 8px",
                  height: "28px",
                  fontSize: "10.5px",
                  fontWeight: 700,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "4px",
                  whiteSpace: "nowrap",
                }}
              >
                <ShieldIcon size={11} color="currentColor" />
                <span>Sign In</span>
              </button>
            )}
          </div>
        </header>
      )}

      {/* Slide-out Mobile Navigation Drawer */}
      {isMobile && isMobileMenuOpen && (
        <div
          style={{
            position: "fixed",
            top: "44px",
            left: 0,
            right: 0,
            bottom: 0,
            background: "var(--bg-surface)",
            backdropFilter: "blur(12px)",
            zIndex: 90,
            display: "flex",
            flexDirection: "column",
            padding: "16px",
            overflowY: "auto",
            gap: "14px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "10px" }}>
            <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", letterSpacing: "0.08em" }}>
              WORKSPACES & TOOLS
            </span>
            <button
              onClick={() => setIsMobileMenuOpen(false)}
              className="btn-sober"
              style={{ padding: "3px 8px", fontSize: "10.5px" }}
            >
              Close
            </button>
          </div>

          {/* Primary Workspaces Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
            {primaryTabs.map((tab) => {
              const isActive = activeView === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => {
                    soundManager.playClick();
                    setActiveView(tab.id);
                    setIsMobileMenuOpen(false);
                  }}
                  style={{
                    background: isActive ? "var(--bg-surface-elevated)" : "var(--bg-surface-card)",
                    border: `1px solid ${isActive ? "var(--accent-blue)" : "var(--border-subtle)"}`,
                    borderRadius: "6px",
                    padding: "10px 12px",
                    color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
                    fontSize: "12px",
                    fontWeight: isActive ? 700 : 500,
                    textAlign: "left",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <span>{tab.label}</span>
                  {isActive && <span className="live-dot-green" />}
                </button>
              );
            })}
          </div>

          {/* Quick AI & Automation Tools */}
          <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "8px", borderTop: "1px solid var(--border-subtle)", paddingTop: "14px" }}>
            <span style={{ fontSize: "10px", fontWeight: 700, color: "var(--text-muted)", letterSpacing: "0.08em" }}>
              INSTANT ASSISTANTS & DISPATCH
            </span>
            <button
              onClick={() => {
                soundManager.playCopilotChime();
                setIsMobileMenuOpen(false);
                onOpenCopilot();
              }}
              style={{
                background: "var(--bg-surface-elevated)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "6px",
                padding: "10px 14px",
                color: "var(--text-primary)",
                fontSize: "12px",
                fontWeight: 600,
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                cursor: "pointer",
              }}
            >
              <span>Atlas AI Copilot</span>
              <span className="kbd-badge">Ctrl+K</span>
            </button>

            <button
              onClick={() => {
                soundManager.playClick();
                setIsMobileMenuOpen(false);
                onOpenAlerts();
              }}
              style={{
                background: "var(--bg-surface-elevated)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "6px",
                padding: "10px 14px",
                color: "var(--text-secondary)",
                fontSize: "12px",
                fontWeight: 600,
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                cursor: "pointer",
              }}
            >
              <span>Price & Indicator Alerts</span>
              <span className="tabular-nums">{unreadAlertsCount} Active</span>
            </button>

            <button
              onClick={handleToggleAudio}
              style={{
                background: "var(--bg-surface-elevated)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "6px",
                padding: "10px 14px",
                color: "var(--text-secondary)",
                fontSize: "12px",
                fontWeight: 600,
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                cursor: "pointer",
              }}
            >
              <span>Synthesizer Audio Cues</span>
              <span>{isAudioMuted ? "MUTED" : "ENABLED"}</span>
            </button>

            {/* Mobile Omnichannel Channels Button */}
            {onOpenOmnichannel && (
              <button
                onClick={() => {
                  soundManager.playClick();
                  setIsMobileMenuOpen(false);
                  onOpenOmnichannel();
                }}
                style={{
                  background: "var(--bg-surface-elevated)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "6px",
                  padding: "10px 14px",
                  color: "var(--text-primary)",
                  fontSize: "12px",
                  fontWeight: 600,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  cursor: "pointer",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <SendIcon size={13} color="var(--accent-blue)" />
                  <span>Omnichannel Push (WhatsApp / Telegram)</span>
                </div>
                <span style={{ fontSize: "10px", color: "var(--accent-blue)", fontWeight: 700 }}>24/7 Gate</span>
              </button>
            )}
          </div>

          {/* User Auth Section in Mobile Drawer */}
          <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "14px" }}>
            {user ? (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  background: "var(--bg-surface-card)",
                  border: "1px solid var(--border-subtle)",
                  padding: "10px 12px",
                  borderRadius: "6px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <div
                    style={{
                      width: "24px",
                      height: "24px",
                      borderRadius: "50%",
                      background: "linear-gradient(135deg, #0284c7 0%, #2563eb 100%)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "10px",
                      fontWeight: 700,
                      color: "#fff",
                    }}
                  >
                    {((user.name || user.email)?.[0] || "U").toUpperCase()}
                  </div>
                  <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-primary)" }}>
                    {user.name || (user.email ? user.email.split("@")[0] : "Trader")}
                  </span>
                </div>
                <button
                  onClick={() => {
                    onLogout();
                    setIsMobileMenuOpen(false);
                  }}
                  style={{
                    background: "transparent",
                    border: "1px solid rgba(244, 63, 94, 0.3)",
                    color: "#f43f5e",
                    borderRadius: "4px",
                    padding: "4px 8px",
                    fontSize: "11px",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <button
                onClick={() => {
                  onOpenAuth();
                  setIsMobileMenuOpen(false);
                }}
                style={{
                  width: "100%",
                  background: "linear-gradient(135deg, rgba(56, 189, 248, 0.15) 0%, rgba(59, 130, 246, 0.15) 100%)",
                  border: "1px solid rgba(56, 189, 248, 0.35)",
                  color: "#38bdf8",
                  borderRadius: "6px",
                  padding: "10px",
                  fontSize: "12px",
                  fontWeight: 700,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "6px",
                }}
              >
                <ShieldIcon size={13} color="#38bdf8" />
                <span>Sign In / Register</span>
              </button>
            )}
          </div>

          {/* Session Telemetry Footer */}
          <div style={{ marginTop: "auto", borderTop: "1px solid var(--border-subtle)", paddingTop: "12px", display: "flex", justifyContent: "space-between", fontSize: "10px", color: "var(--text-muted)" }}>
            <span>NY Feed: 4ms</span>
            <span>Next FOMC: 2h 45m</span>
            <span>Risk Gate: {circuitStatus}</span>
          </div>
        </div>
      )}

      {/* Emergency Flatten Confirmation Modal */}
      {showKillModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0,0,0,0.85)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
          }}
          onClick={() => setShowKillModal(false)}
        >
          <div
            style={{
              background: "var(--bg-surface)",
              border: "1px solid rgba(239, 68, 68, 0.4)",
              borderRadius: "8px",
              padding: "20px",
              width: "440px",
              boxShadow: "var(--card-shadow)",
              display: "flex",
              flexDirection: "column",
              gap: "12px",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <AlertTriangleIcon size={18} color="#ef4444" />
              <span style={{ fontSize: "13px", fontWeight: 700, color: "#ef4444", letterSpacing: "0.5px" }}>
                CONFIRM EMERGENCY FLATTEN
              </span>
            </div>

            <p style={{ margin: 0, fontSize: "12px", color: "var(--text-primary)", lineHeight: "18px" }}>
              Are you sure you want to trigger the Emergency Kill Switch?
            </p>

            <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "11px", color: "var(--text-secondary)", lineHeight: "18px" }}>
              <li>
                Instantly liquidate all <strong>{openPositionsCount} active positions</strong> at best market price.
              </li>
              <li>Cancel all active broker orders and pending limits.</li>
              <li>Trip the institutional Risk Gate to <strong>HALTED</strong> status.</li>
              <li>Lock order execution until explicitly reset by operator.</li>
            </ul>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", marginTop: "6px" }}>
              <button
                onClick={() => setShowKillModal(false)}
                style={{
                  background: "var(--bg-surface-elevated)",
                  border: "1px solid var(--border-medium)",
                  color: "var(--text-primary)",
                  borderRadius: "4px",
                  padding: "8px 0",
                  fontSize: "11px",
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                Abort
              </button>
              <button
                onClick={handleConfirmFlatten}
                style={{
                  background: "#ef4444",
                  border: "none",
                  color: "#fff",
                  borderRadius: "4px",
                  padding: "8px 0",
                  fontSize: "11px",
                  fontWeight: 800,
                  cursor: "pointer",
                }}
              >
                FLATTEN & HALT ALL
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
