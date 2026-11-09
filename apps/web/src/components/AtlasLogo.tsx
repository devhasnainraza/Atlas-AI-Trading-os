"use client";

import React from "react";

export interface AtlasLogoProps {
  size?: number | "sm" | "md" | "lg" | "xl";
  showText?: boolean;
  subtext?: string;
  badge?: string;
  glow?: boolean;
  className?: string;
  style?: React.CSSProperties;
}

export function AtlasEmblem({
  size = 24,
  glow = false,
  className,
}: {
  size?: number;
  glow?: boolean;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      style={{
        filter: glow
          ? "drop-shadow(0 0 10px rgba(56, 189, 248, 0.45)) drop-shadow(0 0 3px rgba(37, 99, 235, 0.4))"
          : "drop-shadow(0 1px 2px rgba(0, 0, 0, 0.12))",
        transition: "filter 0.25s ease, transform 0.25s ease",
        flexShrink: 0,
      }}
    >
      <defs>
        {/* Left Wing / Apex Gradient */}
        <linearGradient id="atlas-left-wing" x1="8" y1="6" x2="24" y2="42" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#38bdf8" />
          <stop offset="45%" stopColor="#2563eb" />
          <stop offset="100%" stopColor="#1e40af" />
        </linearGradient>

        {/* Right Wing / Shaded Bevel */}
        <linearGradient id="atlas-right-wing" x1="40" y1="6" x2="24" y2="42" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#60a5fa" />
          <stop offset="50%" stopColor="#1d4ed8" />
          <stop offset="100%" stopColor="#0f172a" />
        </linearGradient>

        {/* Center Keystone / Core Prism */}
        <linearGradient id="atlas-core-prism" x1="24" y1="12" x2="24" y2="34" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#93c5fd" />
          <stop offset="100%" stopColor="#3b82f6" />
        </linearGradient>

        {/* Celestial Orbital Ring (representing 24/7 Swarm & Global Markets) */}
        <linearGradient id="atlas-orbit-ring" x1="4" y1="26" x2="44" y2="28" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#38bdf8" />
          <stop offset="50%" stopColor="#00f2fe" />
          <stop offset="100%" stopColor="#10b981" />
        </linearGradient>

        {/* Shield Backing Subtle Gradient */}
        <linearGradient id="atlas-shield-bg" x1="0" y1="0" x2="48" y2="48" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="rgba(37, 99, 235, 0.15)" />
          <stop offset="100%" stopColor="rgba(15, 23, 42, 0.05)" />
        </linearGradient>
      </defs>

      {/* Hexagonal Sovereign Shield Contour */}
      <polygon
        points="24,2 44,11 44,35 24,46 4,35 4,11"
        fill="url(#atlas-shield-bg)"
        stroke="rgba(37, 99, 235, 0.3)"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />

      {/* Background Orbital Ring Arc (Behind Apex) */}
      <path
        d="M 6,24 C 8,16 40,16 42,24"
        stroke="url(#atlas-orbit-ring)"
        strokeWidth="1.8"
        strokeDasharray="2 3"
        opacity="0.4"
      />

      {/* The Sovereign Atlas 'A' — Left Wing */}
      <path
        d="M 24,7 L 9,37 L 16.5,37 L 24,21 Z"
        fill="url(#atlas-left-wing)"
      />

      {/* The Sovereign Atlas 'A' — Right Wing (with faceted depth) */}
      <path
        d="M 24,7 L 24,21 L 31.5,37 L 39,37 Z"
        fill="url(#atlas-right-wing)"
      />

      {/* Central Inner Keystone Prism */}
      <polygon
        points="24,14 27.5,22 20.5,22"
        fill="url(#atlas-core-prism)"
      />

      {/* Foreground Orbital Horizon (Dynamic Forward Ring Cutting Through Core) */}
      <path
        d="M 4,25 C 10,33 38,33 44,25"
        stroke="url(#atlas-orbit-ring)"
        strokeWidth="2.4"
        strokeLinecap="round"
      />

      {/* Apex Beacon Jewel (Quantum Spark) */}
      <circle cx="24" cy="7" r="2" fill="#ffffff" />
      <circle cx="24" cy="7" r="1" fill="#38bdf8" />
    </svg>
  );
}

export function AtlasLogo({
  size = "md",
  showText = true,
  subtext,
  badge = "OS",
  glow = false,
  className = "",
  style,
}: AtlasLogoProps) {
  let pixelSize = 24;
  let fontSize = 12;
  let badgeFontSize = 9;

  if (typeof size === "number") {
    pixelSize = size;
    fontSize = Math.max(10, Math.round(size * 0.52));
    badgeFontSize = Math.max(8, Math.round(size * 0.36));
  } else {
    switch (size) {
      case "sm":
        pixelSize = 18;
        fontSize = 11;
        badgeFontSize = 8;
        break;
      case "md":
        pixelSize = 24;
        fontSize = 13;
        badgeFontSize = 9;
        break;
      case "lg":
        pixelSize = 34;
        fontSize = 17;
        badgeFontSize = 10;
        break;
      case "xl":
        pixelSize = 52;
        fontSize = 24;
        badgeFontSize = 13;
        break;
    }
  }

  return (
    <div
      className={`atlas-brand-lockup ${className}`}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: `${Math.max(6, Math.round(pixelSize * 0.32))}px`,
        textDecoration: "none",
        userSelect: "none",
        ...style,
      }}
    >
      {/* Precision Vector Emblem */}
      <AtlasEmblem size={pixelSize} glow={glow} />

      {/* Institutional Wordmark */}
      {showText && (
        <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
            <span
              style={{
                fontWeight: 900,
                fontSize: `${fontSize}px`,
                letterSpacing: "0.08em",
                color: "var(--text-primary)",
                fontFamily: "var(--font-sans, system-ui, sans-serif)",
              }}
            >
              ATLAS
            </span>
            {badge && (
              <span
                style={{
                  fontSize: `${badgeFontSize}px`,
                  fontWeight: 800,
                  letterSpacing: "0.06em",
                  padding: "1px 5px",
                  borderRadius: "3px",
                  background: "var(--accent-blue-subtle)",
                  color: "var(--accent-blue)",
                  border: "1px solid var(--accent-blue-border)",
                  display: "inline-flex",
                  alignItems: "center",
                }}
              >
                {badge}
              </span>
            )}
          </div>
          {subtext && (
            <span
              style={{
                fontSize: `${Math.max(7.5, fontSize * 0.62)}px`,
                fontWeight: 700,
                letterSpacing: "0.08em",
                color: "var(--text-muted)",
                textTransform: "uppercase",
                marginTop: "2px",
              }}
            >
              {subtext}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

export default AtlasLogo;

