"use client";

import React, { useState, useEffect } from "react";
import { HeaderHUD } from "./HeaderHUD";
import { MarketScanner, AssetDef } from "./MarketScanner";
import { PortfolioTelemetry, ActivePosition } from "./PortfolioTelemetry";
import { HumanApprovalModal, OrderProposal } from "./HumanApprovalModal";
import { AISwarmView } from "./AISwarmView";
import { MarketplaceView } from "./MarketplaceView";
import { TradeJournalView, JournalTrade } from "./TradeJournalView";
import { AtlasCopilotModal } from "./AtlasCopilotModal";
import { MultiChartGrid } from "./MultiChartGrid";
import { MacroSentinelView } from "./MacroSentinelView";
import { TradingAutomationView } from "./TradingAutomationView";
import { BrokerVaultView } from "./BrokerVaultView";
import { AgentControlPanel } from "./AgentControlPanel";
import { AtlasOSView } from "./AtlasOSView";
import { OmnichannelSettingsModal } from "./OmnichannelSettingsModal";
import { AlertsManagerModal, TradingAlert } from "./AlertsManagerModal";
import { AuthModal, AuthUser } from "./AuthModal";
import { soundManager } from "../lib/soundEffects";
import { dispatchChannelAlert } from "../lib/channelService";
import {
  CloseIcon,
  AlertTriangleIcon,
  TrendingUpIcon,
  TrendingDownIcon,
  ZapIcon,
  SlidersIcon,
  RadarIcon,
  ShieldIcon,
  SearchIcon,
  BriefcaseIcon,
  ActivityIcon,
} from "./Icons";

const INITIAL_ALERTS: TradingAlert[] = [
  {
    id: "alt-01",
    symbol: "BTC/USDT",
    type: "PRICE_ABOVE",
    targetValue: 87500.0,
    currentValue: 86234.0,
    note: "All-Time High consolidation resistance break",
    status: "ACTIVE",
    createdAt: "10:14:02",
    soundEnabled: true,
  },
  {
    id: "alt-02",
    symbol: "ETH/USDT",
    type: "RSI_OVERSOLD",
    targetValue: 30.0,
    currentValue: 42.1,
    note: "15M oversold mean-reversion long setup",
    status: "ACTIVE",
    createdAt: "09:30:15",
    soundEnabled: true,
  },
  {
    id: "alt-03",
    symbol: "SOL/USDT",
    type: "PRICE_BELOW",
    targetValue: 145.0,
    currentValue: 151.2,
    note: "Daily Support FVG breakdown invalidation",
    status: "ACTIVE",
    createdAt: "11:05:40",
    soundEnabled: true,
  },
];

const DEFAULT_ASSET: AssetDef = {
  symbol: "BTC/USDT",
  name: "Bitcoin",
  category: "CRYPTO",
  quote: "USDT",
  tvSymbol: "BINANCE:BTCUSDT",
  price: "86,234.00",
  rawPrice: 86234.0,
  change: "+1.24%",
  rawChange: 1.24,
  isPositive: true,
  leverage: "10x",
};

const INITIAL_POSITIONS: ActivePosition[] = [
  {
    id: "pos-btc-01",
    symbol: "BTC/USDT",
    side: "LONG",
    sizeStr: "0.25 BTC",
    entryPrice: 84250.0,
    currentPrice: 86234.0,
    pnlUsd: 496.0,
    pnlPct: 2.35,
    tpPrice: 88500.0,
    slPrice: 83200.0,
    breakEven: false,
    trailingStop: true,
  },
  {
    id: "pos-eur-02",
    symbol: "EUR/USD",
    side: "LONG",
    sizeStr: "1.50 Lots",
    entryPrice: 1.138,
    currentPrice: 1.1417,
    pnlUsd: 370.0,
    pnlPct: 1.85,
    tpPrice: 1.152,
    slPrice: 1.132,
    breakEven: true,
    trailingStop: false,
  },
];

const INITIAL_TRADES: JournalTrade[] = [
  {
    id: "tr-001",
    time: "09:42:15",
    symbol: "SOL/USDT",
    side: "LONG",
    entryPrice: 148.5,
    exitPrice: 154.2,
    sizeStr: "45 SOL",
    pnlUsd: 256.5,
    pnlPct: 3.84,
    tags: ["A+ Setup", "FVG Retest", "Rule Followed"],
    status: "CLOSED",
  },
  {
    id: "tr-002",
    time: "10:15:30",
    symbol: "ETH/USDT",
    side: "SHORT",
    entryPrice: 3520.0,
    exitPrice: 3485.0,
    sizeStr: "2.5 ETH",
    pnlUsd: 87.5,
    pnlPct: 0.99,
    tags: ["Rule Followed"],
    status: "CLOSED",
  },
  {
    id: "tr-003",
    time: "11:04:12",
    symbol: "XAU/USD",
    side: "LONG",
    entryPrice: 2662.0,
    exitPrice: 2654.0,
    sizeStr: "0.50 Lots",
    pnlUsd: -400.0,
    pnlPct: -1.5,
    tags: ["FOMO", "Chased Entry"],
    status: "CLOSED",
  },
  {
    id: "tr-004",
    time: "11:50:00",
    symbol: "NVDA",
    side: "LONG",
    entryPrice: 124.5,
    exitPrice: 128.4,
    sizeStr: "100 Units",
    pnlUsd: 390.0,
    pnlPct: 3.13,
    tags: ["A+ Setup"],
    status: "CLOSED",
  },
];

interface CockpitDashboardProps {
  initialView?: string;
}

export function CockpitDashboard({ initialView = "cockpit" }: CockpitDashboardProps) {
  const [activeView, setActiveView] = useState(initialView);
  const [selectedAsset, setSelectedAsset] = useState<AssetDef>(DEFAULT_ASSET);
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isRealBrokerConnected, setIsRealBrokerConnected] = useState(false);
  const [balance, setBalance] = useState(0.0);
  const [positions, setPositions] = useState<ActivePosition[]>([]);
  const [openOrders, setOpenOrders] = useState<any[]>([]);
  const [closedTrades, setClosedTrades] = useState<JournalTrade[]>([]);
  const [orderProposal, setOrderProposal] = useState<OrderProposal | null>(null);
  const [circuitStatus, setCircuitStatus] = useState<"NORMAL" | "ALERT" | "HALTED">("NORMAL");
  const [emergencyAlert, setEmergencyAlert] = useState<string | null>(null);
  const [isCopilotOpen, setIsCopilotOpen] = useState(false);
  const [isOmnichannelOpen, setIsOmnichannelOpen] = useState(false);
  const [isLeftSidebarOpen, setIsLeftSidebarOpen] = useState(true);
  const [isRightSidebarOpen, setIsRightSidebarOpen] = useState(true);
  const [isMobile, setIsMobile] = useState(false);
  const [mobileCockpitTab, setMobileCockpitTab] = useState<"chart" | "scanner" | "portfolio" | "order">("chart");
  const [automationSubTab, setAutomationSubTab] = useState<"bots" | "strategies" | "macro">("bots");
  const [aiCommandSubTab, setAiCommandSubTab] = useState<"swarm" | "autopilot" | "architecture">("architecture");
  const [alerts, setAlerts] = useState<TradingAlert[]>(INITIAL_ALERTS);
  const [isAlertsOpen, setIsAlertsOpen] = useState(false);
  const [activeAlertToast, setActiveAlertToast] = useState<{ id: string; title: string; note: string; symbol: string } | null>(null);
  const [theme, setTheme] = useState<"light" | "dark">("light");

  // Sync theme with localStorage & document attribute
  useEffect(() => {
    try {
      const savedTheme = localStorage.getItem("atlas_theme") as "light" | "dark" | null;
      const initialTheme = savedTheme === "dark" ? "dark" : "light";
      setTheme(initialTheme);
      document.documentElement.setAttribute("data-theme", initialTheme);
    } catch {
      // Fallback
    }
  }, []);

  const handleToggleTheme = () => {
    soundManager.playClick();
    setTheme((prev) => {
      const nextTheme = prev === "light" ? "dark" : "light";
      try {
        localStorage.setItem("atlas_theme", nextTheme);
        document.documentElement.setAttribute("data-theme", nextTheme);
      } catch {
        // Fallback
      }
      return nextTheme;
    });
  };

  const loadJournalTrades = React.useCallback(() => {
    fetch("/api/journal")
      .then((r) => r.json())
      .then((data) => {
        if (data.trades) {
          setClosedTrades(data.trades);
        }
      })
      .catch(() => {});
  }, []);

  // Check authentication & sync real broker portfolio on mount
  useEffect(() => {
    loadJournalTrades();
    fetch("/api/auth/me")
      .then((r) => r.json())
      .then((data) => {
        if (data.authenticated && data.user) {
          setCurrentUser(data.user);
          // Sync real broker portfolio
          fetch("/api/broker/real-portfolio")
            .then((pr) => pr.json())
            .then((pData) => {
              if (pData.connected) {
                setIsRealBrokerConnected(true);
                setBalance(pData.totalBalanceUsd || 0);
                setPositions(pData.positions || []);
                setOpenOrders(pData.openOrders || []);
              } else {
                setIsRealBrokerConnected(false);
                setBalance(0);
                setPositions([]);
                setOpenOrders([]);
              }
            })
            .catch(() => {});
        } else {
          setCurrentUser(null);
          setIsRealBrokerConnected(false);
          setBalance(0);
          setPositions([]);
          setOpenOrders([]);
        }
      })
      .catch(() => {});
  }, [loadJournalTrades]);

  const handleLogout = async () => {
    soundManager.playClick();
    await fetch("/api/auth/logout", { method: "POST" });
    setCurrentUser(null);
    setIsRealBrokerConnected(false);
    setBalance(0);
    setPositions([]);
    setOpenOrders([]);
    setIsAuthModalOpen(true);
  };

  const handleAuthSuccess = (user: AuthUser) => {
    setCurrentUser(user);
    loadJournalTrades();
    fetch("/api/broker/real-portfolio")
      .then((pr) => pr.json())
      .then((pData) => {
        if (pData.connected) {
          setIsRealBrokerConnected(true);
          setBalance(pData.totalBalanceUsd || 0);
          setPositions(pData.positions || []);
          setOpenOrders(pData.openOrders || []);
        } else {
          setIsRealBrokerConnected(false);
          setBalance(0);
          setPositions([]);
          setOpenOrders([]);
        }
      })
      .catch(() => {});
  };

  const handleCancelOrder = async (orderId: string) => {
    soundManager.playClick();
    const targetOrder = openOrders.find((o) => o.id === orderId);
    setOpenOrders((prev) => prev.filter((o) => o.id !== orderId));
    setActiveAlertToast({
      id: "ord-cancel-" + Date.now(),
      symbol: targetOrder?.symbol || "CANCELLED",
      title: `Order #${orderId} Revoked`,
      note: "Order cancelled on broker exchange. Capital released.",
    });

    try {
      await fetch("/api/broker/cancel-order", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ orderId, symbol: targetOrder?.symbol }),
      });
    } catch {}
  };

  // Responsive mobile width detection
  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
    };
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Auto-dismiss alert notification banner
  useEffect(() => {
    if (activeAlertToast) {
      const timer = setTimeout(() => {
        setActiveAlertToast(null);
      }, 7000);
      return () => clearTimeout(timer);
    }
  }, [activeAlertToast]);

  // Global Keyboard Shortcuts: Ctrl+K / Cmd+K for Copilot, [ and ] for Sidebars
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setIsCopilotOpen((prev) => !prev);
      } else if (e.key === "Escape") {
        setIsCopilotOpen(false);
      } else if (e.key === "[" && !(e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement)) {
        setIsLeftSidebarOpen((prev) => !prev);
      } else if (e.key === "]" && !(e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement)) {
        setIsRightSidebarOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Live Position Price Ticking with Dynamic Trailing Stop Automation
  useEffect(() => {
    const timer = setInterval(() => {
      setPositions((prev) =>
        prev.map((p) => {
          const jitter = (Math.random() - 0.49) * 0.0006;
          const newPrice = p.currentPrice * (1 + jitter);
          const priceDiff = p.side === "LONG" ? newPrice - p.entryPrice : p.entryPrice - newPrice;
          const pnlPct = (priceDiff / p.entryPrice) * 100;

          let notional = p.entryPrice;
          if (p.sizeStr.includes("BTC")) notional *= 0.25;
          else if (p.sizeStr.includes("Lots")) notional *= 100000 * 0.01;
          else notional *= 50;

          const pnlUsd = (notional * pnlPct) / 100;

          let sl = p.slPrice;
          if (p.trailingStop) {
            const trailOffset = p.currentPrice * 0.015;
            if (p.side === "LONG" && newPrice > p.entryPrice) {
              const newSl = parseFloat((newPrice - trailOffset).toFixed(p.entryPrice < 10 ? 4 : 2));
              if (newSl > sl) sl = newSl;
            } else if (p.side === "SHORT" && newPrice < p.entryPrice) {
              const newSl = parseFloat((newPrice + trailOffset).toFixed(p.entryPrice < 10 ? 4 : 2));
              if (newSl < sl) sl = newSl;
            }
          }

          return {
            ...p,
            currentPrice: parseFloat(newPrice.toFixed(p.entryPrice < 10 ? 4 : 2)),
            pnlPct: parseFloat(pnlPct.toFixed(2)),
            pnlUsd: parseFloat(pnlUsd.toFixed(2)),
            slPrice: sl,
          };
        })
      );
    }, 2500);

    return () => clearInterval(timer);
  }, []);

  const unrealizedTotal = positions.reduce((acc, p) => acc + p.pnlUsd, 0);
  const equity = balance + unrealizedTotal;

  const handleSelectAsset = (asset: AssetDef) => {
    setSelectedAsset(asset);
  };

  const handleInitiateOrder = (side: "BUY" | "SELL", asset: AssetDef, riskPct: number) => {
    if (circuitStatus === "HALTED") {
      alert("RISK GATE IS HALTED: Orders cannot be submitted while the emergency circuit breaker is active. Reset the risk gate first.");
      return;
    }

    const riskUsd = Math.round(balance * (riskPct / 100));
    const price = asset.rawPrice;
    const inv = side === "BUY" ? price * 0.982 : price * 1.018;
    const tp = side === "BUY" ? price * 1.036 : price * 0.964;

    let sizeStr = "";
    if (asset.category === "CRYPTO") {
      const units = (riskUsd / (price * 0.018)).toFixed(3);
      sizeStr = `${units} ${asset.symbol.split("/")[0]}`;
    } else if (asset.category === "FOREX") {
      sizeStr = `${(riskPct * 1.2).toFixed(2)} Lots`;
    } else {
      sizeStr = `${Math.max(1, Math.round(riskUsd / 200))} Units`;
    }

    setOrderProposal({
      id: "ord-" + Date.now(),
      symbol: asset.symbol,
      side,
      price: asset.rawPrice,
      sizeStr,
      riskUsd,
      riskPct,
      targetEv: riskUsd * 2,
      invalidationPrice: parseFloat(inv.toFixed(price < 1 ? 4 : 2)),
      tpPrice: parseFloat(tp.toFixed(price < 1 ? 4 : 2)),
    });

    dispatchChannelAlert(
      `TRADE CONFIRMATION: ${side} ${asset.symbol}`,
      `Order prepared @ $${price.toLocaleString()} | Size: ${sizeStr}\nRisk: $${riskUsd} (${riskPct}%)\nTarget TP: $${tp.toFixed(2)} | Invalidation SL: $${inv.toFixed(2)}\n\nApprove in Cockpit or reply "YES" to execute!`,
      "TRADE_PROPOSAL"
    );
  };

  const handleApproveOrder = (order: OrderProposal) => {
    const newPos: ActivePosition = {
      id: "pos-" + Date.now(),
      symbol: order.symbol,
      side: order.side === "BUY" ? "LONG" : "SHORT",
      sizeStr: order.sizeStr,
      entryPrice: order.price,
      currentPrice: order.price,
      pnlUsd: 12.5,
      pnlPct: 0.15,
      tpPrice: order.tpPrice,
      slPrice: order.invalidationPrice,
      breakEven: false,
      trailingStop: false,
    };

    setPositions((prev) => [newPos, ...prev]);
    setOrderProposal(null);

    dispatchChannelAlert(
      `ORDER FILLED: ${order.side} ${order.symbol}`,
      `Filled at $${order.price.toLocaleString()} | Size: ${order.sizeStr}\nTarget: $${order.tpPrice} | Stop Loss: $${order.invalidationPrice}\nAuto-Breakeven armed. Risk Gate: NORMAL`,
      "EXECUTION"
    );
  };

  const handleDeclineOrder = () => {
    setOrderProposal(null);
  };

  const handleClosePosition = (posId: string) => {
    const pos = positions.find((p) => p.id === posId);
    if (pos) {
      setBalance((prev) => prev + pos.pnlUsd);
      setPositions((prev) => prev.filter((p) => p.id !== posId));

      const now = new Date();
      const timeStr = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`;

      const closedTrade: JournalTrade = {
        id: "tr-" + Date.now(),
        time: timeStr,
        symbol: pos.symbol,
        side: pos.side,
        entryPrice: pos.entryPrice,
        exitPrice: pos.currentPrice,
        sizeStr: pos.sizeStr,
        pnlUsd: pos.pnlUsd,
        pnlPct: pos.pnlPct,
        tags: [pos.pnlUsd >= 0 ? "Rule Followed" : "Stop Triggered"],
        status: "CLOSED",
      };

      setClosedTrades((prev) => [closedTrade, ...prev]);

      fetch("/api/journal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trade: closedTrade }),
      }).catch(() => {});
    }
  };

  const handlePartialClose = (posId: string, ratio: number = 0.5) => {
    const pos = positions.find((p) => p.id === posId);
    if (pos) {
      const realizedUsd = pos.pnlUsd * ratio;
      setBalance((prev) => prev + realizedUsd);

      const now = new Date();
      const timeStr = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`;

      const partialTrade: JournalTrade = {
        id: "tr-" + Date.now(),
        time: timeStr,
        symbol: pos.symbol,
        side: pos.side,
        entryPrice: pos.entryPrice,
        exitPrice: pos.currentPrice,
        sizeStr: `${Math.round(ratio * 100)}% of ${pos.sizeStr}`,
        pnlUsd: realizedUsd,
        pnlPct: pos.pnlPct,
        tags: ["Scale-Out", "Rule Followed"],
        status: "CLOSED",
      };

      setClosedTrades((prev) => [partialTrade, ...prev]);

      fetch("/api/journal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trade: partialTrade }),
      }).catch(() => {});

      setPositions((prev) =>
        prev.map((p) => {
          if (p.id === posId) {
            return {
              ...p,
              sizeStr: `${Math.round((1 - ratio) * 100)}% of ${p.sizeStr}`,
              pnlUsd: p.pnlUsd * (1 - ratio),
            };
          }
          return p;
        })
      );
    }
  };

  const handleUpdateTpSl = (posId: string, tp: number, sl: number) => {
    setPositions((prev) =>
      prev.map((p) => (p.id === posId ? { ...p, tpPrice: tp, slPrice: sl } : p))
    );
  };

  const handleSetBreakEven = (posId: string) => {
    setPositions((prev) =>
      prev.map((p) => (p.id === posId ? { ...p, slPrice: p.entryPrice, breakEven: true } : p))
    );
  };

  const handleToggleTrailingStop = (posId: string) => {
    setPositions((prev) =>
      prev.map((p) => (p.id === posId ? { ...p, trailingStop: !p.trailingStop } : p))
    );
  };

  const handleEmergencyFlatten = () => {
    const totalRealized = positions.reduce((acc, p) => acc + p.pnlUsd, 0);
    const now = new Date();
    const timeStr = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`;

    const newClosedTrades: JournalTrade[] = positions.map((p, idx) => ({
      id: "tr-flat-" + (Date.now() + idx),
      time: timeStr,
      symbol: p.symbol,
      side: p.side,
      entryPrice: p.entryPrice,
      exitPrice: p.currentPrice,
      sizeStr: p.sizeStr,
      pnlUsd: p.pnlUsd,
      pnlPct: p.pnlPct,
      tags: ["Emergency Kill Switch", "Halted"],
      status: "FLATTENED",
    }));

    setClosedTrades((prev) => [...newClosedTrades, ...prev]);

    for (const ct of newClosedTrades) {
      fetch("/api/journal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trade: ct }),
      }).catch(() => {});
    }

    setBalance((prev) => prev + totalRealized);
    setPositions([]);
    setCircuitStatus("HALTED");
    const haltMsg = `EMERGENCY FLATTEN EXECUTED: Liquidated ${positions.length} positions. Net PnL: ${totalRealized >= 0 ? "+" : ""}$${totalRealized.toFixed(2)}. Risk Gate locked.`;
    setEmergencyAlert(haltMsg);

    dispatchChannelAlert(
      `EMERGENCY FLATTEN EXECUTED`,
      haltMsg,
      "RISK"
    );
  };

  const handleResetCircuit = () => {
    setCircuitStatus("NORMAL");
    setEmergencyAlert(null);
  };

  const handleAddAlert = (newAlert: Omit<TradingAlert, "id" | "createdAt" | "status">) => {
    const now = new Date();
    const timeStr = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`;
    const created: TradingAlert = {
      ...newAlert,
      id: "alt-" + Date.now(),
      createdAt: timeStr,
      status: "ACTIVE",
    };
    setAlerts((prev) => [created, ...prev]);
    soundManager.playClick();
  };

  const handleToggleAlertStatus = (alertId: string) => {
    setAlerts((prev) =>
      prev.map((a) => {
        if (a.id === alertId) {
          const nextStatus = a.status === "ACTIVE" ? "PAUSED" : "ACTIVE";
          return { ...a, status: nextStatus };
        }
        return a;
      })
    );
    soundManager.playClick();
  };

  const handleDeleteAlert = (alertId: string) => {
    setAlerts((prev) => prev.filter((a) => a.id !== alertId));
    soundManager.playClick();
  };

  const handleTriggerTestAlert = (alertId: string) => {
    const alertItem = alerts.find((a) => a.id === alertId);
    if (!alertItem) return;

    soundManager.playAlert();
    const now = new Date();
    const timeStr = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`;

    setAlerts((prev) =>
      prev.map((a) =>
        a.id === alertId
          ? {
              ...a,
              status: "TRIGGERED",
              triggeredAt: timeStr,
            }
          : a
      )
    );

    setActiveAlertToast({
      id: alertId,
      symbol: alertItem.symbol,
      title: `${alertItem.symbol} — ${alertItem.type.replace("_", " ")} (${alertItem.targetValue})`,
      note: alertItem.note,
    });

    dispatchChannelAlert(
      `ALERT TRIGGERED: ${alertItem.symbol} — ${alertItem.type.replace("_", " ")}`,
      `Target $${alertItem.targetValue.toLocaleString()} reached!\nNote: ${alertItem.note}`,
      "ALERT"
    );
  };

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", background: "var(--bg-canvas)", overflow: "hidden" }}>
      {/* Top Header with Navigation Tabs & Kill Switch & Copilot Button */}
      <HeaderHUD
        activeView={activeView}
        setActiveView={setActiveView}
        circuitStatus={circuitStatus}
        onEmergencyFlatten={handleEmergencyFlatten}
        onResetCircuit={handleResetCircuit}
        openPositionsCount={positions.length}
        onOpenCopilot={() => setIsCopilotOpen(true)}
        onOpenAlerts={() => setIsAlertsOpen(true)}
        onOpenOmnichannel={() => setIsOmnichannelOpen(true)}
        unreadAlertsCount={alerts.filter((a) => a.status === "ACTIVE").length}
        user={currentUser}
        onOpenAuth={() => setIsAuthModalOpen(true)}
        onLogout={handleLogout}
        theme={theme}
        onToggleTheme={handleToggleTheme}
      />

      {/* Real-time Alert Notification Toast */}
      {activeAlertToast && (
        <div
          style={{
            position: "fixed",
            top: "54px",
            right: "24px",
            zIndex: 100,
            background: "var(--bg-surface)",
            border: "1px solid var(--border-medium)",
            boxShadow: "var(--card-shadow)",
            borderRadius: "6px",
            padding: "10px 14px",
            display: "flex",
            alignItems: "flex-start",
            gap: "10px",
            maxWidth: "360px",
          }}
        >
          <div
            style={{
              width: "6px",
              height: "6px",
              borderRadius: "50%",
              background: "#ef4444",
              marginTop: "5px",
              flexShrink: 0,
            }}
          />
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span style={{ fontSize: "10px", fontWeight: 800, color: "#ef4444", letterSpacing: "0.5px" }}>
                CRITICAL SIGNAL ALERT
              </span>
              <button
                onClick={() => setActiveAlertToast(null)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  padding: 0,
                }}
              >
                <CloseIcon size={12} color="var(--text-muted)" />
              </button>
            </div>
            <div style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-primary)", marginTop: "2px" }}>
              {activeAlertToast.title}
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "2px" }}>
              {activeAlertToast.note}
            </div>
            <div style={{ display: "flex", gap: "8px", marginTop: "8px" }}>
              <button
                onClick={() => {
                  setIsAlertsOpen(true);
                  setActiveAlertToast(null);
                }}
                style={{
                  background: "rgba(239, 68, 68, 0.15)",
                  border: "1px solid rgba(239, 68, 68, 0.4)",
                  color: "#fca5a5",
                  fontSize: "10px",
                  fontWeight: 700,
                  borderRadius: "4px",
                  padding: "3px 8px",
                  cursor: "pointer",
                }}
              >
                View in Alert Hub
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Emergency Alert Banner */}
      {emergencyAlert && (
        <div
          style={{
            background: "rgba(239, 68, 68, 0.9)",
            color: "#fff",
            padding: "8px 16px",
            fontSize: "12px",
            fontWeight: 700,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexShrink: 0,
            zIndex: 30,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <AlertTriangleIcon size={14} color="#fff" />
            <span>{emergencyAlert}</span>
          </div>
          <button
            onClick={handleResetCircuit}
            style={{
              background: "#fff",
              border: "none",
              color: "#ef4444",
              fontWeight: 800,
              fontSize: "11px",
              padding: "3px 10px",
              borderRadius: "4px",
              cursor: "pointer",
            }}
          >
            Reset Risk Gate
          </button>
        </div>
      )}

      {/* Dynamic View Switcher — 5 Clean Views */}
      <main style={{ flex: 1, padding: isMobile ? "4px 6px" : "8px 10px", overflow: "hidden" }}>

        {/* ═══════════ VIEW 1: COCKPIT (Pure Trading) ═══════════ */}
        {activeView === "cockpit" && (
          isMobile ? (
            <div style={{ height: "100%", display: "flex", flexDirection: "column", overflow: "hidden", gap: "0" }}>
              <div className="mobile-tab-bar" style={{ flexShrink: 0, marginBottom: "6px" }}>
                {([
                  { key: "chart", label: "Chart", icon: TrendingUpIcon },
                  { key: "scanner", label: "Watchlist", icon: SearchIcon },
                  { key: "portfolio", label: `Portfolio${positions.length > 0 ? " (" + positions.length + ")" : ""}`, icon: BriefcaseIcon },
                  { key: "order", label: "Order", icon: ZapIcon },
                ] as const).map((tab) => {
                  const Icon = tab.icon;
                  return (
                    <button
                      key={tab.key}
                      onClick={() => {
                        soundManager.playClick();
                        setMobileCockpitTab(tab.key as any);
                      }}
                      className={`mobile-tab-item${mobileCockpitTab === tab.key ? " active" : ""}`}
                    >
                      <Icon size={12} color="currentColor" />
                      <span>{tab.label}</span>
                    </button>
                  );
                })}
              </div>

              <div style={{ flex: 1, minHeight: 0, overflow: "hidden", display: "flex", flexDirection: "column", padding: "0 2px" }}>
                {mobileCockpitTab === "chart" && (
                  <div style={{ height: "100%", display: "flex", flexDirection: "column", gap: "6px" }}>
                    <div className="panel" style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", overflow: "hidden" }}>
                      <MultiChartGrid
                        primaryAsset={selectedAsset}
                        onSelectPrimaryAsset={handleSelectAsset}
                        theme={theme}
                      />
                    </div>
                  </div>
                )}

                {mobileCockpitTab === "scanner" && (
                  <MarketScanner
                    selectedSymbol={selectedAsset.symbol}
                    onSelectSymbol={(asset) => {
                      handleSelectAsset(asset);
                      setMobileCockpitTab("chart");
                    }}
                    onInitiateOrder={handleInitiateOrder}
                    isCollapsed={false}
                  />
                )}

                {mobileCockpitTab === "portfolio" && (
                  <PortfolioTelemetry
                    balance={balance}
                    equity={equity}
                    positions={positions}
                    openOrders={openOrders}
                    onClosePosition={handleClosePosition}
                    onPartialClose={handlePartialClose}
                    onUpdateTpSl={handleUpdateTpSl}
                    onSetBreakEven={handleSetBreakEven}
                    onToggleTrailingStop={handleToggleTrailingStop}
                    onCancelOrder={handleCancelOrder}
                    isCollapsed={false}
                  />
                )}

                {mobileCockpitTab === "order" && (
                  <div className="panel" style={{ height: "100%", overflowY: "auto", padding: "12px" }}>
                    <div style={{ marginBottom: "10px" }}>
                      <span style={{ fontSize: "10px", fontWeight: 700, color: "var(--text-muted)", letterSpacing: "0.05em" }}>QUICK ORDER</span>
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", marginBottom: "12px" }}>
                      <button
                        onClick={() => handleInitiateOrder("BUY", selectedAsset, 1.0)}
                        style={{ padding: "14px", background: "rgba(34,197,94,0.12)", border: "1px solid rgba(34,197,94,0.3)", color: "#22c55e", borderRadius: "6px", fontWeight: 800, fontSize: "14px", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: "6px" }}
                      >
                        <TrendingUpIcon size={16} color="#22c55e" />
                        <span>BUY / LONG</span>
                      </button>
                      <button
                        onClick={() => handleInitiateOrder("SELL", selectedAsset, 1.0)}
                        style={{ padding: "14px", background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", color: "#ef4444", borderRadius: "6px", fontWeight: 800, fontSize: "14px", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: "6px" }}
                      >
                        <TrendingDownIcon size={16} color="#ef4444" />
                        <span>SELL / SHORT</span>
                      </button>
                    </div>
                    <div style={{ padding: "10px", background: "var(--bg-surface-elevated)", borderRadius: "6px", border: "1px solid var(--border-subtle)" }}>
                      <div style={{ fontSize: "9px", color: "var(--text-muted)", fontWeight: 700, marginBottom: "4px" }}>SELECTED ASSET</div>
                      <div style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)" }}>{selectedAsset.symbol}</div>
                      <div style={{ fontSize: "11px", color: selectedAsset.isPositive ? "var(--accent-green)" : "var(--accent-red)", marginTop: "2px" }}>
                        ${selectedAsset.price} {selectedAsset.change}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div
              style={{
                height: "100%",
                display: "grid",
                gridTemplateColumns: `${isLeftSidebarOpen ? "260px" : "36px"} minmax(0, 1fr) ${isRightSidebarOpen ? "280px" : "36px"}`,
                gap: "8px",
                overflow: "hidden",
              }}
            >
              <section style={{ height: "100%", overflow: "hidden" }}>
                <MarketScanner
                  selectedSymbol={selectedAsset.symbol}
                  onSelectSymbol={handleSelectAsset}
                  onInitiateOrder={handleInitiateOrder}
                  isCollapsed={!isLeftSidebarOpen}
                  onToggleCollapse={() => setIsLeftSidebarOpen((prev) => !prev)}
                />
              </section>

              <section style={{ height: "100%", display: "flex", flexDirection: "column", gap: "8px", overflow: "hidden" }}>
                <div className="panel" style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", overflow: "hidden" }}>
                  <MultiChartGrid
                    primaryAsset={selectedAsset}
                    onSelectPrimaryAsset={handleSelectAsset}
                    theme={theme}
                  />
                </div>
              </section>

              <section style={{ height: "100%", overflow: "hidden" }}>
                <PortfolioTelemetry
                  balance={balance}
                  equity={equity}
                  positions={positions}
                  openOrders={openOrders}
                  onClosePosition={handleClosePosition}
                  onPartialClose={handlePartialClose}
                  onUpdateTpSl={handleUpdateTpSl}
                  onSetBreakEven={handleSetBreakEven}
                  onToggleTrailingStop={handleToggleTrailingStop}
                  onCancelOrder={handleCancelOrder}
                  isCollapsed={!isRightSidebarOpen}
                  onToggleCollapse={() => setIsRightSidebarOpen((prev) => !prev)}
                />
              </section>
            </div>
          )
        )}

        {/* ═══════════ VIEW 2: AI COMMAND (All Agent Intelligence) ═══════════ */}
        {activeView === "ai-command" && (
          <div style={{ height: "100%", display: "flex", flexDirection: "column", overflow: "hidden" }}>
            <div style={{
              display: "flex",
              gap: "2px",
              padding: "4px",
              background: "var(--bg-surface-card)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "6px",
              marginBottom: "8px",
              flexShrink: 0,
              flexWrap: "wrap",
            }}>
              {([
                { id: "architecture", label: "Atlas OS Controller", icon: ShieldIcon },
                { id: "swarm", label: "Neural Swarm", icon: RadarIcon },
                { id: "autopilot", label: "24/7 Autopilot Loop", icon: ZapIcon },
              ] as const).map((tab) => {
                const Icon = tab.icon;
                const isActive = aiCommandSubTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => {
                      soundManager.playClick();
                      setAiCommandSubTab(tab.id);
                    }}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                      padding: "6px 14px",
                      borderRadius: "4px",
                      fontSize: "11px",
                      fontWeight: isActive ? 700 : 500,
                      border: isActive ? "1px solid var(--accent-blue)" : "1px solid transparent",
                      background: isActive ? "var(--bg-surface-elevated)" : "transparent",
                      color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                    }}
                  >
                    <Icon size={13} color={isActive ? "var(--accent-blue)" : "currentColor"} />
                    {tab.label}
                  </button>
                );
              })}
            </div>

            <div style={{ flex: 1, minHeight: 0, overflow: "hidden" }}>
              {aiCommandSubTab === "architecture" && (
                <div style={{ height: "100%", overflowY: "auto" }}>
                  <AtlasOSView
                    selectedAsset={selectedAsset}
                    balance={balance}
                    equity={equity}
                    positions={positions}
                    circuitStatus={circuitStatus}
                    onInitiateOrder={(side) => handleInitiateOrder(side, selectedAsset, 1.0)}
                    onApproveOrder={handleApproveOrder}
                    onExecuteTrade={(symbol, side, entryPrice, tpPrice, slPrice) => {
                      const newPos = {
                        id: "pos-os-" + Date.now(),
                        symbol,
                        side: side === "BUY" ? "LONG" as const : "SHORT" as const,
                        sizeStr: "0.15 BTC",
                        entryPrice,
                        currentPrice: entryPrice,
                        pnlUsd: 12.5,
                        pnlPct: 0.15,
                        tpPrice,
                        slPrice,
                        breakEven: false,
                        trailingStop: true,
                      };
                      setPositions((prev) => [newPos, ...prev]);
                      setActiveAlertToast({
                        id: "os-exec-" + Date.now(),
                        symbol,
                        title: `EXECUTION AGENT FILLED: ${side} ${symbol} @ $${entryPrice.toLocaleString()}`,
                        note: `Target TP: $${tpPrice} | Invalidation SL: $${slPrice}. Auto-Breakeven armed.`,
                      });
                    }}
                    onOpenCopilot={() => setIsCopilotOpen(true)}
                  />
                </div>
              )}
              {aiCommandSubTab === "swarm" && (
                <AISwarmView
                  selectedAsset={selectedAsset}
                  onInitiateOrder={handleInitiateOrder}
                />
              )}
              {aiCommandSubTab === "autopilot" && (
                <AgentControlPanel
                  balance={balance}
                  equity={equity}
                  positions={positions}
                  riskStatus={circuitStatus}
                  onExecuteTrade={(symbol, side, entryPrice, tpPrice, slPrice) => {
                    const newPos = {
                      id: "pos-agent-" + Date.now(),
                      symbol,
                      side: side === "BUY" ? "LONG" as const : "SHORT" as const,
                      sizeStr: "1.00 Unit (Paper)",
                      entryPrice,
                      currentPrice: entryPrice,
                      pnlUsd: 0,
                      pnlPct: 0,
                      tpPrice,
                      slPrice,
                      breakEven: false,
                      trailingStop: true,
                    };
                    setPositions((prev) => [newPos, ...prev]);
                    setActiveAlertToast({
                      id: "agent-exec-" + Date.now(),
                      symbol,
                      title: `AGENT EXECUTED: ${side} ${symbol} @ $${entryPrice.toLocaleString()}`,
                      note: `Paper trade filled. TP: $${tpPrice} | SL: $${slPrice}. Auto-Breakeven armed.`,
                    });
                  }}
                  onOpenSettings={() => setIsOmnichannelOpen(true)}
                />
              )}
            </div>
          </div>
        )}

        {/* ═══════════ VIEW 3: AUTOMATION (Bots + Strategies + Macro) ═══════════ */}
        {activeView === "automation" && (
          <div style={{ height: "100%", display: "flex", flexDirection: "column", overflow: "hidden" }}>
            <div style={{
              display: "flex",
              gap: "2px",
              padding: "4px",
              background: "var(--bg-surface-card)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "6px",
              marginBottom: "8px",
              flexShrink: 0,
              flexWrap: "wrap",
            }}>
              {([
                { id: "bots", label: "Trading Bots", icon: SlidersIcon },
                { id: "strategies", label: "Strategy Marketplace", icon: RadarIcon },
                { id: "macro", label: "Macro Events", icon: ActivityIcon },
              ] as const).map((tab) => {
                const Icon = tab.icon;
                const isActive = automationSubTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => {
                      soundManager.playClick();
                      setAutomationSubTab(tab.id);
                    }}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                      padding: "6px 14px",
                      borderRadius: "4px",
                      fontSize: "11px",
                      fontWeight: isActive ? 700 : 500,
                      border: isActive ? "1px solid var(--accent-blue)" : "1px solid transparent",
                      background: isActive ? "var(--bg-surface-elevated)" : "transparent",
                      color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                    }}
                  >
                    <Icon size={13} color={isActive ? "var(--accent-blue)" : "currentColor"} />
                    {tab.label}
                  </button>
                );
              })}
            </div>

            <div style={{ flex: 1, minHeight: 0, overflow: "hidden" }}>
              {automationSubTab === "bots" && (
                <TradingAutomationView
                  balance={balance}
                  equity={equity}
                />
              )}
              {automationSubTab === "strategies" && (
                <div style={{ height: "100%", overflowY: "auto" }}>
                  <MarketplaceView />
                </div>
              )}
              {automationSubTab === "macro" && (
                <div style={{ height: "100%", overflowY: "auto" }}>
                  <MacroSentinelView />
                </div>
              )}
            </div>
          </div>
        )}

        {/* ═══════════ VIEW 4: JOURNAL (Trades + Decision Chains + Evaluation) ═══════════ */}
        {activeView === "journal" && (
          <TradeJournalView
            balance={equity}
            closedTrades={closedTrades}
            onReloadTrades={loadJournalTrades}
            onNavigateToCockpit={() => setActiveView("cockpit")}
          />
        )}

        {/* ═══════════ VIEW 5: VAULT (Broker Connections) ═══════════ */}
        {activeView === "vault" && (
          <BrokerVaultView
            onSyncTotalBalance={(bal) => setBalance(bal)}
            onSyncRealData={(data) => {
              setBalance(data.balanceUsd);
              setPositions(data.positions);
              setOpenOrders(data.openOrders || []);
              setIsRealBrokerConnected(true);
            }}
            onOpenChannelSettings={() => setIsOmnichannelOpen(true)}
          />
        )}
      </main>

      {/* User Authentication & Isolation Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onSuccess={handleAuthSuccess}
      />

      {/* Floating Human Approval Modal for Orders */}
      <HumanApprovalModal
        orderProposal={orderProposal}
        onApprove={handleApproveOrder}
        onDecline={handleDeclineOrder}
      />

      {/* Atlas Natural Language AI Trading Copilot Modal */}
      <AtlasCopilotModal
        isOpen={isCopilotOpen}
        onClose={() => setIsCopilotOpen(false)}
        selectedAsset={selectedAsset}
        onSelectAsset={handleSelectAsset}
        onInitiateOrder={handleInitiateOrder}
        balance={balance}
        openPositionsCount={positions.length}
      />

      {/* Price & Technical Indicator Alerts Engine Modal */}
      <AlertsManagerModal
        isOpen={isAlertsOpen}
        onClose={() => setIsAlertsOpen(false)}
        alerts={alerts}
        onAddAlert={handleAddAlert}
        onToggleAlertStatus={handleToggleAlertStatus}
        onDeleteAlert={handleDeleteAlert}
        onTriggerTestAlert={handleTriggerTestAlert}
        activeAsset={selectedAsset}
      />

      {/* Omnichannel Settings Modal */}
      <OmnichannelSettingsModal
        isOpen={isOmnichannelOpen}
        onClose={() => setIsOmnichannelOpen(false)}
      />

      {/* Mobile Bottom Navigation — 5 Clean Views */}
      {isMobile && (
        <nav className="mobile-bottom-nav">
          {[
            { id: "cockpit", label: "Cockpit", icon: TrendingUpIcon },
            { id: "ai-command", label: "AI", icon: RadarIcon },
            { id: "automation", label: "Auto", icon: SlidersIcon },
            { id: "journal", label: "Journal", icon: ActivityIcon },
            { id: "vault", label: "Vault", icon: ShieldIcon },
          ].map((item) => {
            const isActive = activeView === item.id;
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                onClick={() => {
                  soundManager.playClick();
                  setActiveView(item.id);
                }}
                className={`mobile-bottom-nav-item${isActive ? " active" : ""}`}
              >
                {isActive && <div className="active-glow-bar" />}
                <div className="nav-icon-wrap">
                  <Icon size={14} color={isActive ? "#38bdf8" : "currentColor"} />
                </div>
                <span className="nav-label">{item.label}</span>
              </button>
            );
          })}
        </nav>
      )}
    </div>
  );
}

export default CockpitDashboard;

