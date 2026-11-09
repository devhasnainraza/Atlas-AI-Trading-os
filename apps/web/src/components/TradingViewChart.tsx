"use client";

import React, { useEffect, useRef, useState, memo } from "react";
import { AtlasNativeChart } from "./AtlasNativeChart";
import { soundManager } from "../lib/soundEffects";
import { ZapIcon, RefreshIcon, AlertTriangleIcon } from "./Icons";

interface TradingViewChartProps {
  symbol?: string;
  theme?: "dark" | "light";
  interval?: string;
  minHeight?: string;
  initialEngine?: "native" | "tradingview";
}

export const TradingViewChart = memo(function TradingViewChart({
  symbol = "BINANCE:BTCUSDT",
  theme = "light",
  interval = "15",
  minHeight = "200px",
  initialEngine = "native", // Default to resilient native chart to prevent DNS/ad-blocker white box
}: TradingViewChartProps) {
  const containerId = useRef(`tv_chart_${Math.random().toString(36).substring(2, 9)}`).current;
  const [engine, setEngine] = useState<"native" | "tradingview">(initialEngine);
  const [isWidgetLoaded, setIsWidgetLoaded] = useState(false);
  const [hasTvError, setHasTvError] = useState(false);
  const [tvErrorMessage, setTvErrorMessage] = useState<string | null>(null);

  // Clean symbol for native chart (e.g. BINANCE:BTCUSDT -> BTC/USDT)
  const cleanNativeSymbol = React.useMemo(() => {
    const raw = symbol || "BTCUSDT";
    const s = (raw.includes(":") ? raw.split(":")[1] : raw) || raw;
    if (s.endsWith("USDT")) {
      const base = s.replace("USDT", "");
      return `${base}/USDT`;
    }
    if (s === "EURUSD") return "EUR/USD";
    if (s === "XAUUSD") return "XAU/USD";
    return s;
  }, [symbol]);

  // Handle TradingView Widget initialization when engine === 'tradingview'
  useEffect(() => {
    if (engine !== "tradingview") return;

    let isMounted = true;
    setHasTvError(false);
    setTvErrorMessage(null);

    const initWidget = () => {
      if (!isMounted) return;
      const tv = (window as unknown as { TradingView?: { widget: new (config: Record<string, unknown>) => unknown } }).TradingView;

      if (tv && typeof tv.widget === "function") {
        const container = document.getElementById(containerId);
        if (container) {
          container.innerHTML = "";
        }

        try {
          new tv.widget({
            autosize: true,
            symbol: symbol,
            interval: interval,
            timezone: "Etc/UTC",
            theme: theme,
            style: "1",
            locale: "en",
            toolbar_bg: theme === "light" ? "#ffffff" : "#080c14",
            enable_publishing: false,
            allow_symbol_change: true,
            container_id: containerId,
            hide_side_toolbar: false,
            studies: ["MASimple@tv-basicstudies"],
            save_image: false,
            backgroundColor: theme === "light" ? "#ffffff" : "#080c14",
            gridColor: theme === "light" ? "rgba(0, 0, 0, 0.05)" : "rgba(255, 255, 255, 0.04)",
          });
          setIsWidgetLoaded(true);
        } catch (err: any) {
          if (isMounted) {
            setHasTvError(true);
            setTvErrorMessage(err?.message || "TradingView initialization failed");
          }
        }
      } else {
        if (isMounted) {
          setHasTvError(true);
          setTvErrorMessage("TradingView script failed to load from s3.tradingview.com");
        }
      }
    };

    const scriptId = "tradingview-tv-js";
    let script = document.getElementById(scriptId) as HTMLScriptElement;

    if (!script) {
      script = document.createElement("script");
      script.id = scriptId;
      script.src = "https://s3.tradingview.com/tv.js";
      script.type = "text/javascript";
      script.async = true;
      script.onload = () => {
        initWidget();
      };
      script.onerror = () => {
        if (isMounted) {
          setHasTvError(true);
          setTvErrorMessage("s.tradingview.com server unreachable or blocked by network/ad-blocker");
        }
      };
      document.head.appendChild(script);
    } else {
      initWidget();
    }

    // 4-second timeout watchdog: if iframe doesn't load or is blocked, show fallback prompt
    const timer = setTimeout(() => {
      if (isMounted && !isWidgetLoaded) {
        // If still not loaded after 4 seconds, mark as possible DNS block
        setHasTvError(true);
        setTvErrorMessage("s.tradingview.com connection timed out (likely DNS or ad-blocker filter)");
      }
    }, 4000);

    return () => {
      isMounted = false;
      clearTimeout(timer);
      const container = document.getElementById(containerId);
      if (container) {
        container.innerHTML = "";
      }
    };
  }, [engine, symbol, theme, interval, containerId, isWidgetLoaded]);

  // If Native Engine is selected, render the resilient Atlas Native Chart
  if (engine === "native") {
    return (
      <div style={{ position: "relative", width: "100%", height: "100%", minHeight }}>
        {/* Engine Switcher Floating Pill */}
        <div
          style={{
            position: "absolute",
            top: "6px",
            right: "42px",
            zIndex: 10,
            display: "flex",
            alignItems: "center",
            gap: "4px",
            background: theme === "light" ? "var(--bg-surface-elevated, #f8fafc)" : "rgba(11, 16, 27, 0.85)",
            backdropFilter: "blur(6px)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "4px",
            padding: "2px 5px",
          }}
        >
          <button
            onClick={() => {
              soundManager.playClick();
              setEngine("native");
            }}
            style={{
              background: "rgba(56, 189, 248, 0.18)",
              border: "1px solid rgba(56, 189, 248, 0.4)",
              color: "#38bdf8",
              fontSize: "9px",
              fontWeight: 700,
              padding: "2px 6px",
              borderRadius: "3px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "3px",
            }}
          >
            <ZapIcon size={10} color="#38bdf8" />
            Atlas Native
          </button>
          <button
            onClick={() => {
              soundManager.playClick();
              setEngine("tradingview");
            }}
            style={{
              background: "transparent",
              border: "1px solid transparent",
              color: "var(--text-muted)",
              fontSize: "9px",
              fontWeight: 500,
              padding: "2px 6px",
              borderRadius: "3px",
              cursor: "pointer",
            }}
          >
            TradingView
          </button>
        </div>

        <AtlasNativeChart
          symbol={cleanNativeSymbol}
          interval={interval}
          theme={theme}
          minHeight={minHeight}
        />
      </div>
    );
  }

  // TradingView Engine Selected
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        minHeight: minHeight,
        background: theme === "light" ? "var(--bg-surface, #ffffff)" : "#080c14",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Engine Switcher Floating Pill */}
      <div
        style={{
          position: "absolute",
          top: "6px",
          right: "42px",
          zIndex: 10,
          display: "flex",
          alignItems: "center",
          gap: "4px",
          background: theme === "light" ? "var(--bg-surface-elevated, #f8fafc)" : "rgba(11, 16, 27, 0.85)",
          backdropFilter: "blur(6px)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "4px",
          padding: "2px 5px",
        }}
      >
        <button
          onClick={() => {
            soundManager.playClick();
            setEngine("native");
          }}
          style={{
            background: "transparent",
            border: "1px solid transparent",
            color: "#64748b",
            fontSize: "9px",
            fontWeight: 500,
            padding: "2px 6px",
            borderRadius: "3px",
            cursor: "pointer",
          }}
        >
          Atlas Native
        </button>
        <button
          onClick={() => {
            soundManager.playClick();
            setEngine("tradingview");
          }}
          style={{
            background: "rgba(59, 130, 246, 0.18)",
            border: "1px solid rgba(59, 130, 246, 0.4)",
            color: "#60a5fa",
            fontSize: "9px",
            fontWeight: 700,
            padding: "2px 6px",
            borderRadius: "3px",
            cursor: "pointer",
          }}
        >
          TradingView
        </button>
      </div>

      {/* TradingView Container */}
      <div
        id={containerId}
        style={{
          width: "100%",
          height: "100%",
          minHeight: minHeight,
          background: "#080c14",
          position: "relative",
          zIndex: 2,
        }}
      />

      {/* Error Fallback Overlay if TradingView is blocked or fails */}
      {hasTvError && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: "rgba(8, 12, 20, 0.96)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 20,
            padding: "24px",
            textAlign: "center",
          }}
        >
          <div
            style={{
              width: "44px",
              height: "44px",
              borderRadius: "10px",
              background: "rgba(239, 68, 68, 0.12)",
              border: "1px solid rgba(239, 68, 68, 0.25)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              marginBottom: "12px",
            }}
          >
            <AlertTriangleIcon size={22} color="#ef4444" />
          </div>

          <span style={{ fontSize: "14px", fontWeight: 700, color: "#f8fafc", marginBottom: "6px" }}>
            TradingView Cloud Feed Blocked
          </span>

          <p style={{ fontSize: "11px", color: "#94a3b8", maxWidth: "420px", lineHeight: "1.5", marginBottom: "16px" }}>
            Your network or browser ad-blocker blocked <code>s.tradingview.com</code>. Switch to the built-in Atlas Native Direct Feed for instant, unblocked live Binance order flow.
          </p>

          <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
            <button
              onClick={() => {
                soundManager.playClick();
                setEngine("native");
              }}
              style={{
                background: "linear-gradient(135deg, #0284c7 0%, #2563eb 100%)",
                border: "none",
                color: "#ffffff",
                padding: "8px 16px",
                borderRadius: "5px",
                fontSize: "11px",
                fontWeight: 700,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                boxShadow: "0 4px 12px rgba(37, 99, 235, 0.3)",
              }}
            >
              <ZapIcon size={13} color="#ffffff" />
              Switch to Atlas Native Feed
            </button>

            <button
              onClick={() => {
                soundManager.playClick();
                setHasTvError(false);
                setIsWidgetLoaded(false);
              }}
              style={{
                background: "rgba(255, 255, 255, 0.06)",
                border: "1px solid rgba(255, 255, 255, 0.12)",
                color: "#cbd5e1",
                padding: "8px 14px",
                borderRadius: "5px",
                fontSize: "11px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Retry Connection
            </button>
          </div>
        </div>
      )}
    </div>
  );
});
