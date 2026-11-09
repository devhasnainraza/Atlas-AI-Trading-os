"use client";

import React, { useState, useMemo, useEffect, useRef } from "react";
import { StarIcon, CloseIcon, SearchIcon, SortIcon, TrendingUpIcon, TrendingDownIcon } from "./Icons";

export interface AssetDef {
  symbol: string;
  name: string;
  category: "CRYPTO" | "FOREX" | "COMMODITIES" | "INDICES" | "STOCKS";
  quote: "USDT" | "USD" | "EUR" | "BTC" | "OTHER";
  tvSymbol: string;
  binanceSymbol?: string;
  price: string;
  rawPrice: number;
  change: string;
  rawChange: number;
  isPositive: boolean;
  leverage: string;
  flash?: "UP" | "DOWN" | null;
}

const INITIAL_ASSETS: AssetDef[] = [
  // CRYPTO (Connected to Live Binance WebSocket)
  { symbol: "BTC/USDT", name: "Bitcoin", category: "CRYPTO", quote: "USDT", tvSymbol: "BINANCE:BTCUSDT", binanceSymbol: "BTCUSDT", price: "86,234.00", rawPrice: 86234.0, change: "+1.24%", rawChange: 1.24, isPositive: true, leverage: "10x" },
  { symbol: "ETH/USDT", name: "Ethereum", category: "CRYPTO", quote: "USDT", tvSymbol: "BINANCE:ETHUSDT", binanceSymbol: "ETHUSDT", price: "2,747.50", rawPrice: 2747.5, change: "+0.85%", rawChange: 0.85, isPositive: true, leverage: "10x" },
  { symbol: "SOL/USDT", name: "Solana", category: "CRYPTO", quote: "USDT", tvSymbol: "BINANCE:SOLUSDT", binanceSymbol: "SOLUSDT", price: "118.10", rawPrice: 118.1, change: "+2.40%", rawChange: 2.4, isPositive: true, leverage: "10x" },
  { symbol: "BNB/USDT", name: "Binance Coin", category: "CRYPTO", quote: "USDT", tvSymbol: "BINANCE:BNBUSDT", binanceSymbol: "BNBUSDT", price: "790.10", rawPrice: 790.1, change: "+1.15%", rawChange: 1.15, isPositive: true, leverage: "5x" },
  { symbol: "XRP/USDT", name: "Ripple", category: "CRYPTO", quote: "USDT", tvSymbol: "BINANCE:XRPUSDT", binanceSymbol: "XRPUSDT", price: "1.6130", rawPrice: 1.613, change: "+3.20%", rawChange: 3.2, isPositive: true, leverage: "5x" },
  { symbol: "DOGE/USDT", name: "Dogecoin", category: "CRYPTO", quote: "USDT", tvSymbol: "BINANCE:DOGEUSDT", binanceSymbol: "DOGEUSDT", price: "0.1013", rawPrice: 0.1013, change: "+0.65%", rawChange: 0.65, isPositive: true, leverage: "5x" },
  { symbol: "SUI/USDT", name: "Sui Network", category: "CRYPTO", quote: "USDT", tvSymbol: "BINANCE:SUIUSDT", binanceSymbol: "SUIUSDT", price: "2.1450", rawPrice: 2.145, change: "+4.10%", rawChange: 4.1, isPositive: true, leverage: "5x" },
  { symbol: "AVAX/USDT", name: "Avalanche", category: "CRYPTO", quote: "USDT", tvSymbol: "BINANCE:AVAXUSDT", binanceSymbol: "AVAXUSDT", price: "24.60", rawPrice: 24.6, change: "-0.80%", rawChange: -0.8, isPositive: false, leverage: "5x" },
  { symbol: "PEPE/USDT", name: "Pepe Coin", category: "CRYPTO", quote: "USDT", tvSymbol: "BINANCE:PEPEUSDT", binanceSymbol: "PEPEUSDT", price: "0.0000094", rawPrice: 0.0000094, change: "+2.10%", rawChange: 2.1, isPositive: true, leverage: "3x" },
  { symbol: "NEAR/USDT", name: "NEAR Protocol", category: "CRYPTO", quote: "USDT", tvSymbol: "BINANCE:NEARUSDT", binanceSymbol: "NEARUSDT", price: "3.840", rawPrice: 3.84, change: "+1.60%", rawChange: 1.6, isPositive: true, leverage: "5x" },
  { symbol: "LINK/USDT", name: "Chainlink", category: "CRYPTO", quote: "USDT", tvSymbol: "BINANCE:LINKUSDT", binanceSymbol: "LINKUSDT", price: "14.85", rawPrice: 14.85, change: "+1.95%", rawChange: 1.95, isPositive: true, leverage: "5x" },

  // FOREX
  { symbol: "EUR/USD", name: "Euro / US Dollar", category: "FOREX", quote: "USD", tvSymbol: "FX:EURUSD", price: "1.14170", rawPrice: 1.1417, change: "+0.15%", rawChange: 0.15, isPositive: true, leverage: "20x" },
  { symbol: "GBP/USD", name: "British Pound / USD", category: "FOREX", quote: "USD", tvSymbol: "FX:GBPUSD", price: "1.29850", rawPrice: 1.2985, change: "+0.35%", rawChange: 0.35, isPositive: true, leverage: "20x" },
  { symbol: "USD/JPY", name: "USD / Japanese Yen", category: "FOREX", quote: "USD", tvSymbol: "FX:USDJPY", price: "148.850", rawPrice: 148.85, change: "-0.40%", rawChange: -0.4, isPositive: false, leverage: "20x" },
  { symbol: "GBP/JPY", name: "British Pound / Yen", category: "FOREX", quote: "OTHER", tvSymbol: "FX:GBPJPY", price: "192.450", rawPrice: 192.45, change: "-0.12%", rawChange: -0.12, isPositive: false, leverage: "20x" },
  { symbol: "USD/CHF", name: "USD / Swiss Franc", category: "FOREX", quote: "USD", tvSymbol: "FX:USDCHF", price: "0.85240", rawPrice: 0.8524, change: "+0.15%", rawChange: 0.15, isPositive: true, leverage: "20x" },
  { symbol: "AUD/USD", name: "Australian Dollar / USD", category: "FOREX", quote: "USD", tvSymbol: "FX:AUDUSD", price: "0.67450", rawPrice: 0.6745, change: "+0.52%", rawChange: 0.52, isPositive: true, leverage: "20x" },
  { symbol: "USD/CAD", name: "USD / Canadian Dollar", category: "FOREX", quote: "USD", tvSymbol: "FX:USDCAD", price: "1.35900", rawPrice: 1.359, change: "-0.18%", rawChange: -0.18, isPositive: false, leverage: "20x" },

  // COMMODITIES
  { symbol: "XAU/USD", name: "Gold Spot / US Dollar", category: "COMMODITIES", quote: "USD", tvSymbol: "OANDA:XAUUSD", price: "4,319.40", rawPrice: 4319.4, change: "+0.95%", rawChange: 0.95, isPositive: true, leverage: "10x" },
  { symbol: "XAG/USD", name: "Silver Spot / US Dollar", category: "COMMODITIES", quote: "USD", tvSymbol: "OANDA:XAGUSD", price: "31.450", rawPrice: 31.45, change: "+1.40%", rawChange: 1.4, isPositive: true, leverage: "10x" },
  { symbol: "USOIL", name: "WTI Crude Oil", category: "COMMODITIES", quote: "USD", tvSymbol: "TVC:USOIL", price: "71.20", rawPrice: 71.2, change: "-1.10%", rawChange: -1.1, isPositive: false, leverage: "10x" },
  { symbol: "UKOIL", name: "Brent Crude Oil", category: "COMMODITIES", quote: "USD", tvSymbol: "TVC:UKOIL", price: "74.80", rawPrice: 74.8, change: "-0.95%", rawChange: -0.95, isPositive: false, leverage: "10x" },
  { symbol: "NATGAS", name: "Natural Gas", category: "COMMODITIES", quote: "USD", tvSymbol: "TVC:NATURALGAS", price: "2.854", rawPrice: 2.854, change: "+2.40%", rawChange: 2.4, isPositive: true, leverage: "5x" },

  // INDICES
  { symbol: "US100", name: "Nasdaq 100", category: "INDICES", quote: "USD", tvSymbol: "NASDAQ:NDX", price: "19,840.50", rawPrice: 19840.5, change: "+1.25%", rawChange: 1.25, isPositive: true, leverage: "20x" },
  { symbol: "US500", name: "S&P 500", category: "INDICES", quote: "USD", tvSymbol: "OANDA:SPX500USD", price: "5,745.20", rawPrice: 5745.2, change: "+0.88%", rawChange: 0.88, isPositive: true, leverage: "20x" },
  { symbol: "US30", name: "Dow Jones 30", category: "INDICES", quote: "USD", tvSymbol: "OANDA:US30USD", price: "42,150.00", rawPrice: 42150.0, change: "+0.45%", rawChange: 0.45, isPositive: true, leverage: "20x" },
  { symbol: "GER40", name: "German DAX 40", category: "INDICES", quote: "EUR", tvSymbol: "INDEX:DAX", price: "19,210.00", rawPrice: 19210.0, change: "+0.65%", rawChange: 0.65, isPositive: true, leverage: "20x" },
  { symbol: "UK100", name: "FTSE 100", category: "INDICES", quote: "OTHER", tvSymbol: "OANDA:UK100GBP", price: "8,280.40", rawPrice: 8280.4, change: "-0.20%", rawChange: -0.2, isPositive: false, leverage: "20x" },

  // STOCKS
  { symbol: "NVDA", name: "NVIDIA Corp", category: "STOCKS", quote: "USD", tvSymbol: "NASDAQ:NVDA", price: "128.40", rawPrice: 128.4, change: "+4.20%", rawChange: 4.2, isPositive: true, leverage: "5x" },
  { symbol: "TSLA", name: "Tesla Inc", category: "STOCKS", quote: "USD", tvSymbol: "NASDAQ:TSLA", price: "248.50", rawPrice: 248.5, change: "+3.10%", rawChange: 3.1, isPositive: true, leverage: "5x" },
  { symbol: "AAPL", name: "Apple Inc", category: "STOCKS", quote: "USD", tvSymbol: "NASDAQ:AAPL", price: "228.20", rawPrice: 228.2, change: "+0.95%", rawChange: 0.95, isPositive: true, leverage: "5x" },
  { symbol: "MSFT", name: "Microsoft Corp", category: "STOCKS", quote: "USD", tvSymbol: "NASDAQ:MSFT", price: "432.10", rawPrice: 432.1, change: "+1.15%", rawChange: 1.15, isPositive: true, leverage: "5x" },
  { symbol: "COIN", name: "Coinbase Global", category: "STOCKS", quote: "USD", tvSymbol: "NASDAQ:COIN", price: "182.40", rawPrice: 182.4, change: "+5.40%", rawChange: 5.4, isPositive: true, leverage: "5x" },
];

type MainCategory = "ALL" | "FAVORITES" | "CRYPTO" | "FOREX" | "COMMODITIES" | "INDICES" | "STOCKS";
type SortField = "NAME" | "PRICE" | "CHANGE";
type SortOrder = "ASC" | "DESC" | null;

export interface MarketScannerProps {
  selectedSymbol: string;
  onSelectSymbol: (asset: AssetDef) => void;
  onInitiateOrder: (side: "BUY" | "SELL", asset: AssetDef, riskPct: number) => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export function MarketScanner({
  selectedSymbol,
  onSelectSymbol,
  onInitiateOrder,
  isCollapsed = false,
  onToggleCollapse,
}: MarketScannerProps) {
  const [assets, setAssets] = useState<AssetDef[]>(INITIAL_ASSETS);
  const [activeCategory, setActiveCategory] = useState<MainCategory>("ALL");
  const [quoteFilter, setQuoteFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [favorites, setFavorites] = useState<Set<string>>(new Set(["BTC/USDT", "ETH/USDT", "EUR/USD", "XAU/USD"]));
  const [sortField, setSortField] = useState<SortField | null>(null);
  const [sortOrder, setSortOrder] = useState<SortOrder>(null);
  const [showCustomInput, setShowCustomInput] = useState(false);
  const [customTicker, setCustomTicker] = useState("");
  const [riskPct, setRiskPct] = useState(1.0);
  const [isWsConnected, setIsWsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  // 1. Real Live Binance WebSocket connection for live price streaming
  useEffect(() => {
    let ws: WebSocket;
    try {
      ws = new WebSocket("wss://stream.binance.com:9443/ws/!miniTicker@arr");
      wsRef.current = ws;

      ws.onopen = () => {
        setIsWsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const tickers = JSON.parse(event.data);
          if (!Array.isArray(tickers)) return;

          const tickerMap = new Map<string, { c: number; o: number }>();
          for (const t of tickers) {
            tickerMap.set(t.s, { c: parseFloat(t.c), o: parseFloat(t.o) });
          }

          setAssets((prevAssets) =>
            prevAssets.map((asset) => {
              if (asset.binanceSymbol && tickerMap.has(asset.binanceSymbol)) {
                const live = tickerMap.get(asset.binanceSymbol)!;
                const newPrice = live.c;
                const oldPrice = asset.rawPrice;
                const pctChange = ((live.c - live.o) / live.o) * 100;
                const flash = newPrice > oldPrice ? "UP" : newPrice < oldPrice ? "DOWN" : null;

                let formattedPrice = newPrice.toLocaleString("en-US", {
                  minimumFractionDigits: newPrice < 1 ? 4 : 2,
                  maximumFractionDigits: newPrice < 1 ? 7 : 2,
                });

                return {
                  ...asset,
                  rawPrice: newPrice,
                  price: formattedPrice,
                  rawChange: pctChange,
                  change: `${pctChange >= 0 ? "+" : ""}${pctChange.toFixed(2)}%`,
                  isPositive: pctChange >= 0,
                  flash,
                };
              }
              return asset;
            })
          );
        } catch {
          // Ignore parse errors on individual frames
        }
      };

      ws.onerror = () => {
        setIsWsConnected(false);
      };

      ws.onclose = () => {
        setIsWsConnected(false);
      };
    } catch {
      setIsWsConnected(false);
    }

    return () => {
      if (ws) ws.close();
    };
  }, []);

  // Micro-tick simulation for Forex/Metals so they live tick too
  useEffect(() => {
    const timer = setInterval(() => {
      setAssets((prevAssets) =>
        prevAssets.map((asset) => {
          if (asset.category === "FOREX" || asset.category === "COMMODITIES") {
            const jitter = (Math.random() - 0.49) * 0.0004;
            const newPrice = asset.rawPrice * (1 + jitter);
            const formattedPrice =
              asset.category === "FOREX"
                ? newPrice.toFixed(asset.symbol.includes("JPY") ? 3 : 5)
                : newPrice.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            return {
              ...asset,
              rawPrice: newPrice,
              price: formattedPrice,
            };
          }
          return asset;
        })
      );
    }, 2000);

    return () => clearInterval(timer);
  }, []);

  const mainCategories: { id: MainCategory; label: string }[] = [
    { id: "FAVORITES", label: "Favorites" },
    { id: "ALL", label: "All" },
    { id: "CRYPTO", label: "Crypto" },
    { id: "FOREX", label: "Forex" },
    { id: "COMMODITIES", label: "Metals" },
    { id: "INDICES", label: "Indices" },
    { id: "STOCKS", label: "Stocks" },
  ];

  const quoteTabs = ["ALL", "USDT", "USD", "EUR"];

  const toggleFavorite = (symbol: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setFavorites((prev) => {
      const next = new Set(prev);
      if (next.has(symbol)) {
        next.delete(symbol);
      } else {
        next.add(symbol);
      }
      return next;
    });
  };

  const handleSort = (field: SortField) => {
    if (sortField !== field) {
      setSortField(field);
      setSortOrder("DESC");
    } else if (sortOrder === "DESC") {
      setSortOrder("ASC");
    } else {
      setSortField(null);
      setSortOrder(null);
    }
  };

  const handleLoadCustom = (e: React.FormEvent) => {
    e.preventDefault();
    if (!customTicker.trim()) return;

    const raw = customTicker.trim().toUpperCase();
    let resolvedTv = raw;
    let bSymbol: string | undefined = undefined;

    if (!raw.includes(":")) {
      if (raw.endsWith("USDT") || raw.endsWith("BTC")) {
        resolvedTv = `BINANCE:${raw}`;
        bSymbol = raw;
      } else if (raw.length === 6 && (raw.startsWith("EUR") || raw.startsWith("GBP") || raw.startsWith("USD"))) {
        resolvedTv = `FX:${raw}`;
      } else {
        resolvedTv = `NASDAQ:${raw}`;
      }
    }

    const newAsset: AssetDef = {
      symbol: raw,
      name: raw,
      category: "CRYPTO",
      quote: "USDT",
      tvSymbol: resolvedTv,
      binanceSymbol: bSymbol,
      price: "100.00",
      rawPrice: 100.0,
      change: "+0.00%",
      rawChange: 0,
      isPositive: true,
      leverage: "5x",
    };

    setAssets((prev) => [newAsset, ...prev]);
    onSelectSymbol(newAsset);
    setCustomTicker("");
    setShowCustomInput(false);
  };

  const filteredAssets = useMemo(() => {
    let list = assets.filter((a) => {
      if (activeCategory === "FAVORITES") {
        if (!favorites.has(a.symbol)) return false;
      } else if (activeCategory !== "ALL" && a.category !== activeCategory) {
        return false;
      }

      if (quoteFilter !== "ALL" && a.quote !== quoteFilter) {
        return false;
      }

      if (searchQuery.trim()) {
        const q = searchQuery.trim().toLowerCase();
        const matchSymbol = a.symbol.toLowerCase().includes(q);
        const matchName = a.name.toLowerCase().includes(q);
        if (!matchSymbol && !matchName) return false;
      }

      return true;
    });

    if (sortField && sortOrder) {
      list = [...list].sort((a, b) => {
        let valA: string | number = 0;
        let valB: string | number = 0;

        if (sortField === "NAME") {
          valA = a.symbol;
          valB = b.symbol;
          return sortOrder === "ASC"
            ? (valA as string).localeCompare(valB as string)
            : (valB as string).localeCompare(valA as string);
        } else if (sortField === "PRICE") {
          valA = a.rawPrice;
          valB = b.rawPrice;
        } else if (sortField === "CHANGE") {
          valA = a.rawChange;
          valB = b.rawChange;
        }

        return sortOrder === "ASC"
          ? (valA as number) - (valB as number)
          : (valB as number) - (valA as number);
      });
    }

    return list;
  }, [assets, activeCategory, quoteFilter, searchQuery, favorites, sortField, sortOrder]);

  const currentSelectedAsset: AssetDef = useMemo(() => {
    return assets.find((a) => a.symbol === selectedSymbol) ?? assets[0] ?? INITIAL_ASSETS[0]!;
  }, [assets, selectedSymbol]);

  const calculatedRiskUsd = Math.round(128940 * (riskPct / 100));

  if (isCollapsed) {
    return (
      <div
        className="panel"
        style={{
          width: "36px",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          padding: "8px 0",
          gap: "12px",
          background: "var(--bg-surface)",
          borderRight: "1px solid var(--border-subtle)",
          cursor: "pointer",
        }}
        onClick={onToggleCollapse}
        title="Expand Market Watch ([)"
      >
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggleCollapse?.();
          }}
          className="btn-sober"
          style={{ width: "24px", height: "24px", padding: 0, display: "flex", alignItems: "center", justifyContent: "center" }}
          title="Expand Market Watch ([)"
        >
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polyline points="9 18 15 12 9 6" />
          </svg>
        </button>

        <span className={isWsConnected ? "live-dot-green" : "live-dot-amber"} />

        <div
          style={{
            writingMode: "vertical-rl",
            transform: "rotate(180deg)",
            fontSize: "10px",
            fontWeight: 700,
            letterSpacing: "0.08em",
            color: "var(--text-secondary)",
            whiteSpace: "nowrap",
          }}
        >
          MARKET WATCH
        </div>

        <div
          style={{
            marginTop: "auto",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "4px",
          }}
        >
          <span style={{ fontSize: "9px", fontFamily: "var(--font-mono)", fontWeight: 700, color: "var(--accent-blue)" }}>
            {currentSelectedAsset.symbol.split("/")[0]}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div
      className="panel"
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        overflow: "hidden",
        fontSize: "12px",
      }}
    >
      {/* 1. Search Bar + Live WebSocket Status Pill */}
      <div style={{ padding: "8px 10px 6px 10px", background: "var(--bg-surface-elevated)", borderBottom: "1px solid var(--border-subtle)" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "6px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ fontSize: "10px", color: "var(--text-muted)", fontWeight: 700, letterSpacing: "0.06em" }}>MARKET WATCH</span>
            <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
              <span className={isWsConnected ? "live-dot-green" : "live-dot-amber"} />
              <span style={{ fontSize: "9px", color: isWsConnected ? "var(--accent-green)" : "var(--text-muted)", fontWeight: 600 }}>
                {isWsConnected ? "LIVE" : "SYNC"}
              </span>
            </div>
          </div>
          {onToggleCollapse && (
            <button
              onClick={onToggleCollapse}
              className="btn-sober"
              style={{ width: "20px", height: "20px", padding: 0, display: "flex", alignItems: "center", justifyContent: "center" }}
              title="Collapse Market Watch ([)"
            >
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <polyline points="15 18 9 12 15 6" />
              </svg>
            </button>
          )}
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            background: "var(--bg-surface-card)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "4px",
            padding: "4px 8px",
          }}
        >
          <SearchIcon size={12} color="var(--text-muted)" />
          <input
            type="text"
            placeholder="Search symbol..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              flex: 1,
              background: "transparent",
              border: "none",
              color: "var(--text-primary)",
              fontSize: "11px",
              outline: "none",
              fontFamily: "var(--font-sans)",
            }}
          />
          {searchQuery && (
            <span
              onClick={() => setSearchQuery("")}
              style={{ color: "#64748b", cursor: "pointer", display: "inline-flex", alignItems: "center" }}
            >
              <CloseIcon size={10} color="#64748b" />
            </span>
          )}
        </div>
      </div>

      {/* 2. Top Asset Class Tabs (Favorites All Crypto Forex Metals Indices Stocks) */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "12px",
          padding: "2px 10px",
          borderBottom: "1px solid var(--border-subtle)",
          overflowX: "auto",
          whiteSpace: "nowrap",
          background: "var(--bg-surface-card)",
        }}
      >
        {mainCategories.map((c) => {
          const isSelected = activeCategory === c.id;
          return (
            <button
              key={c.id}
              onClick={() => setActiveCategory(c.id)}
              style={{
                background: "transparent",
                border: "none",
                padding: "6px 0",
                fontSize: "11px",
                fontWeight: isSelected ? 600 : 500,
                color: isSelected ? "var(--text-primary)" : "var(--text-muted)",
                cursor: "pointer",
                position: "relative",
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
                transition: "color 0.1s ease",
              }}
            >
              {c.id === "FAVORITES" ? (
                <StarIcon size={12} filled={isSelected} color={isSelected ? "var(--accent-blue)" : "var(--text-muted)"} />
              ) : (
                c.label
              )}
              {isSelected && (
                <div
                  style={{
                    position: "absolute",
                    bottom: 0,
                    left: 0,
                    right: 0,
                    height: "2px",
                    background: "#3b82f6",
                  }}
                />
              )}
            </button>
          );
        })}

        <button
          onClick={() => setShowCustomInput(!showCustomInput)}
          title="Add Custom Asset Ticker"
          style={{
            marginLeft: "auto",
            background: showCustomInput ? "rgba(255, 255, 255, 0.08)" : "transparent",
            border: "1px solid var(--border-subtle)",
            color: "#94a3b8",
            borderRadius: "3px",
            padding: "1px 5px",
            fontSize: "10px",
            fontWeight: 700,
            cursor: "pointer",
          }}
        >
          +
        </button>
      </div>

      {/* Custom Ticker Flyout */}
      {showCustomInput && (
        <form
          onSubmit={handleLoadCustom}
          style={{
            background: "var(--bg-surface-elevated)",
            padding: "6px 10px",
            borderBottom: "1px solid var(--border-subtle)",
            display: "flex",
            gap: "4px",
          }}
        >
          <input
            type="text"
            placeholder="e.g. SOLUSDT, NVDA, EURUSD"
            value={customTicker}
            onChange={(e) => setCustomTicker(e.target.value)}
            autoFocus
            style={{
              flex: 1,
              background: "var(--bg-surface-card)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "3px",
              padding: "3px 6px",
              color: "var(--text-primary)",
              fontSize: "11px",
              outline: "none",
            }}
          />
          <button
            type="submit"
            style={{
              background: "#3b82f6",
              border: "none",
              borderRadius: "3px",
              color: "#ffffff",
              padding: "0 8px",
              fontSize: "10px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Load
          </button>
        </form>
      )}

      {/* 3. Quote Filter Pills (Inline compact) */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "3px 10px",
          background: "var(--bg-surface)",
          borderBottom: "1px solid var(--border-subtle)",
          fontSize: "9.5px",
        }}
      >
        <span style={{ color: "var(--text-muted)", fontSize: "9px" }}>QUOTE CURRENCY</span>
        <div style={{ display: "flex", alignItems: "center", gap: "3px" }}>
          {quoteTabs.map((q) => {
            const isQuoteActive = quoteFilter === q;
            return (
              <span
                key={q}
                onClick={() => setQuoteFilter(q)}
                style={{
                  color: isQuoteActive ? "#38bdf8" : "#64748b",
                  fontWeight: isQuoteActive ? 700 : 500,
                  cursor: "pointer",
                  padding: "1px 5px",
                  borderRadius: "3px",
                  background: isQuoteActive ? "rgba(56, 189, 248, 0.12)" : "transparent",
                  border: isQuoteActive ? "1px solid rgba(56, 189, 248, 0.25)" : "1px solid transparent",
                }}
              >
                {q}
              </span>
            );
          })}
        </div>
      </div>

      {/* 4. Table Header (Name ⇅ | Last Price / 24h Chg ⇅) */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "4px 10px",
          background: "var(--bg-surface)",
          borderBottom: "1px solid var(--border-subtle)",
          fontSize: "10px",
          color: "#64748b",
          userSelect: "none",
        }}
      >
        <div
          onClick={() => handleSort("NAME")}
          style={{ display: "flex", alignItems: "center", gap: "4px", cursor: "pointer" }}
        >
          <span>Name</span>
          <SortIcon active={sortField === "NAME"} order={sortOrder || undefined} size={10} color={sortField === "NAME" ? "var(--accent-blue)" : "var(--text-muted)"} />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <div
            onClick={() => handleSort("PRICE")}
            style={{ display: "flex", alignItems: "center", gap: "3px", cursor: "pointer" }}
          >
            <span>Last Price</span>
            <SortIcon active={sortField === "PRICE"} order={sortOrder || undefined} size={10} color={sortField === "PRICE" ? "var(--accent-blue)" : "var(--text-muted)"} />
          </div>
          <span>/</span>
          <div
            onClick={() => handleSort("CHANGE")}
            style={{ display: "flex", alignItems: "center", gap: "3px", cursor: "pointer" }}
          >
            <span>24h Chg</span>
            <SortIcon active={sortField === "CHANGE"} order={sortOrder || undefined} size={10} color={sortField === "CHANGE" ? "var(--accent-blue)" : "var(--text-muted)"} />
          </div>
        </div>
      </div>

      {/* 5. Clean Asset Rows (Live Real-Time Updating) */}
      <div style={{ flex: 1, overflowY: "auto", background: "var(--bg-surface-card)" }}>
        {filteredAssets.length === 0 ? (
          <div style={{ padding: "20px", textAlign: "center", color: "#64748b", fontSize: "11px" }}>
            No assets match filter
          </div>
        ) : (
          filteredAssets.map((a) => {
            const isSelected = selectedSymbol === a.symbol;
            const isFav = favorites.has(a.symbol);

            return (
              <div
                key={a.symbol}
                onClick={() => onSelectSymbol(a)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "5px 10px",
                  background: isSelected ? "var(--bg-surface-elevated)" : "transparent",
                  borderLeft: isSelected ? "2px solid #3b82f6" : "2px solid transparent",
                  cursor: "pointer",
                  transition: "background 0.1s ease",
                }}
                onMouseEnter={(e) => {
                  if (!isSelected) e.currentTarget.style.background = "var(--bg-surface-elevated)";
                }}
                onMouseLeave={(e) => {
                  if (!isSelected) e.currentTarget.style.background = "transparent";
                }}
              >
                {/* Left: Star + Symbol + Leverage Badge */}
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <span
                    onClick={(e) => toggleFavorite(a.symbol, e)}
                    style={{
                      cursor: "pointer",
                      display: "inline-flex",
                      alignItems: "center",
                      padding: "2px",
                    }}
                  >
                    <StarIcon size={12} color={isFav ? "var(--accent-blue)" : "var(--border-medium)"} filled={isFav} />
                  </span>

                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                        <span
                          style={{
                            fontWeight: 600,
                            fontSize: "11px",
                            color: isSelected ? "var(--accent-blue)" : "var(--text-primary)",
                          }}
                        >
                          {a.symbol}
                        </span>
                      </div>
                      <div style={{ fontSize: "9px", color: "var(--text-muted)", marginTop: "1px" }}>
                        {a.name}
                      </div>
                    </div>
                </div>

                {/* Right: Last Price + 24h Change */}
                <div style={{ textAlign: "right" }}>
                  <div
                    style={{
                      fontSize: "11px",
                      fontWeight: 600,
                      color: a.flash === "UP" ? "var(--accent-green)" : a.flash === "DOWN" ? "var(--accent-red)" : "var(--text-primary)",
                      transition: "color 0.2s ease",
                    }}
                    className="tabular-nums"
                  >
                    {a.price}
                  </div>
                  <div
                    style={{
                      fontSize: "10px",
                      fontWeight: 600,
                      color: a.isPositive ? "#22c55e" : "#ef4444",
                    }}
                    className="tabular-nums"
                  >
                    {a.change}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* 6. Active Execution & Kelly Risk Budget Widget */}
      <div
        style={{
          borderTop: "1px solid var(--border-subtle)",
          padding: "8px 10px",
          background: "var(--bg-surface-elevated)",
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "10px", marginBottom: "5px" }}>
          <span style={{ color: "var(--text-secondary)" }}>
            Trading <strong style={{ color: "var(--text-primary)" }}>{currentSelectedAsset.symbol}</strong>
          </span>
          <span className="tabular-nums" style={{ color: "var(--text-secondary)", fontWeight: 600 }}>
            Risk: <strong style={{ color: "var(--text-primary)" }}>{riskPct.toFixed(1)}%</strong> (${calculatedRiskUsd.toLocaleString()})
          </span>
        </div>

        <input
          type="range"
          min="0.5"
          max="2.5"
          step="0.1"
          value={riskPct}
          onChange={(e) => setRiskPct(parseFloat(e.target.value))}
          style={{ width: "100%", accentColor: "var(--accent-blue)", cursor: "pointer", height: "4px" }}
        />

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px", marginTop: "8px" }}>
          <button
            onClick={() => onInitiateOrder("BUY", currentSelectedAsset, riskPct)}
            style={{
              background: "rgba(16, 185, 129, 0.12)",
              border: "1px solid rgba(16, 185, 129, 0.35)",
              color: "var(--accent-green)",
              borderRadius: "4px",
              padding: "7px 0",
              fontSize: "11px",
              fontWeight: 700,
              letterSpacing: "0.03em",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "6px",
              transition: "all 0.15s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = "rgba(16, 185, 129, 0.22)";
              e.currentTarget.style.borderColor = "rgba(16, 185, 129, 0.55)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "rgba(16, 185, 129, 0.12)";
              e.currentTarget.style.borderColor = "rgba(16, 185, 129, 0.35)";
            }}
            onMouseDown={(e) => (e.currentTarget.style.transform = "scale(0.98)")}
            onMouseUp={(e) => (e.currentTarget.style.transform = "scale(1)")}
          >
            <TrendingUpIcon size={13} color="currentColor" />
            <span>BUY / LONG</span>
          </button>
          <button
            onClick={() => onInitiateOrder("SELL", currentSelectedAsset, riskPct)}
            style={{
              background: "rgba(244, 63, 94, 0.12)",
              border: "1px solid rgba(244, 63, 94, 0.35)",
              color: "var(--accent-red)",
              borderRadius: "4px",
              padding: "7px 0",
              fontSize: "11px",
              fontWeight: 700,
              letterSpacing: "0.03em",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "6px",
              transition: "all 0.15s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = "rgba(244, 63, 94, 0.22)";
              e.currentTarget.style.borderColor = "rgba(244, 63, 94, 0.55)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "rgba(244, 63, 94, 0.12)";
              e.currentTarget.style.borderColor = "rgba(244, 63, 94, 0.35)";
            }}
            onMouseDown={(e) => (e.currentTarget.style.transform = "scale(0.98)")}
            onMouseUp={(e) => (e.currentTarget.style.transform = "scale(1)")}
          >
            <TrendingDownIcon size={13} color="currentColor" />
            <span>SELL / SHORT</span>
          </button>
        </div>
      </div>
    </div>
  );
}
