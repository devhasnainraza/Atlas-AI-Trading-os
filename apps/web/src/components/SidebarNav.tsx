"use client";

import React, { useState } from "react";

interface NavItem {
  id: string;
  label: string;
  icon: (active: boolean) => React.ReactNode;
  badge?: string;
}

export function SidebarNav() {
  const [activeTab, setActiveTab] = useState("cockpit");

  const navItems: NavItem[] = [
    {
      id: "cockpit",
      label: "Cockpit Overview",
      icon: (active) => (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={active ? "var(--accent-blue)" : "currentColor"} strokeWidth="2">
          <rect width="7" height="9" x="3" y="3" rx="1" />
          <rect width="7" height="5" x="14" y="3" rx="1" />
          <rect width="7" height="9" x="14" y="12" rx="1" />
          <rect width="7" height="5" x="3" y="16" rx="1" />
        </svg>
      ),
    },
    {
      id: "swarm",
      label: "Multi-Agent Swarm",
      badge: "4 Active",
      icon: (active) => (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={active ? "var(--accent-blue)" : "currentColor"} strokeWidth="2">
          <circle cx="12" cy="12" r="3" />
          <path d="M12 2v3m0 14v3M2 12h3m14 0h3m-3.5-6.5-2.1 2.1m-8.8 8.8-2.1 2.1m0-13 2.1 2.1m8.8 8.8 2.1 2.1" />
        </svg>
      ),
    },
    {
      id: "chart",
      label: "Terminal & Charts",
      icon: (active) => (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={active ? "var(--accent-blue)" : "currentColor"} strokeWidth="2">
          <path d="m3 3 7 7 4-4 7 7" />
          <path d="M14 13h7v7" />
        </svg>
      ),
    },
    {
      id: "intelligence",
      label: "Market Intelligence",
      icon: (active) => (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={active ? "var(--accent-blue)" : "currentColor"} strokeWidth="2">
          <path d="M2 12h5l3 8 4-16 3 8h5" />
        </svg>
      ),
    },
    {
      id: "automation",
      label: "Smart Stops & Mandates",
      icon: (active) => (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={active ? "var(--accent-blue)" : "currentColor"} strokeWidth="2">
          <path d="M12 20a8 8 0 1 0 0-16 8 8 0 0 0 0 16Z" />
          <path d="M12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z" />
          <path d="M12 2v2m0 16v2M2 12h2m16 0h2" />
        </svg>
      ),
    },
    {
      id: "journal",
      label: "Behavioral Journal",
      icon: (active) => (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={active ? "var(--accent-blue)" : "currentColor"} strokeWidth="2">
          <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z" />
          <path d="M6 6h10m-10 4h10m-10 4h6" />
        </svg>
      ),
    },
    {
      id: "marketplace",
      label: "AI Marketplace",
      badge: "New",
      icon: (active) => (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={active ? "var(--accent-blue)" : "currentColor"} strokeWidth="2">
          <path d="m2 7 4.41-4.41A2 2 0 0 1 7.83 2h8.34a2 2 0 0 1 1.42.59L22 7" />
          <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
          <path d="M15 22v-4a2 2 0 0 0-2-2h-2a2 2 0 0 0-2 2v4" />
          <path d="M2 7h20" />
        </svg>
      ),
    },
    {
      id: "governance",
      label: "Risk & Governance",
      icon: (active) => (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={active ? "var(--accent-blue)" : "currentColor"} strokeWidth="2">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        </svg>
      ),
    },
  ];

  return (
    <aside
      style={{
        width: "60px",
        background: "var(--bg-canvas)",
        borderRight: "1px solid var(--border-subtle)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "16px 0",
        justifyContent: "space-between",
        flexShrink: 0,
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "10px", width: "100%", alignItems: "center" }}>
        {navItems.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              title={item.label}
              style={{
                width: "38px",
                height: "38px",
                borderRadius: "6px",
                border: isActive ? "1px solid var(--border-medium)" : "1px solid transparent",
                background: isActive ? "var(--bg-surface-elevated)" : "transparent",
                color: isActive ? "var(--text-primary)" : "var(--text-muted)",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                position: "relative",
                transition: "all 0.15s ease",
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.background = "rgba(255, 255, 255, 0.04)";
                  e.currentTarget.style.color = "var(--text-primary)";
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.background = "transparent";
                  e.currentTarget.style.color = "var(--text-muted)";
                }
              }}
            >
              {isActive && (
                <div
                  style={{
                    position: "absolute",
                    left: "-8px",
                    top: "8px",
                    bottom: "8px",
                    width: "2px",
                    borderRadius: "0 2px 2px 0",
                    background: "var(--accent-blue)",
                  }}
                />
              )}
              {item.icon(isActive)}
            </button>
          );
        })}
      </div>

      {/* Bottom Settings */}
      <div style={{ display: "flex", flexDirection: "column", gap: "12px", alignItems: "center" }}>
        <button
          title="Settings & Key Vault"
          style={{
            width: "40px",
            height: "40px",
            borderRadius: "10px",
            border: "none",
            background: "transparent",
            color: "var(--text-muted)",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
            <circle cx="12" cy="12" r="3" />
          </svg>
        </button>
      </div>
    </aside>
  );
}
