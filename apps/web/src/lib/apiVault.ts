export type ConnectionType = "API_KEY" | "OAUTH" | "WEB3_WALLET";
export type ConnectionStatus = "CONNECTED" | "DISCONNECTED" | "WARNING";

export interface ExchangePermissions {
  canRead: boolean;
  canTrade: boolean;
  canWithdraw: boolean; // Must be false for safe connection
}

export interface ConnectedExchange {
  id: string;
  name: string;
  category: "CRYPTO_EXCHANGE" | "FOREX_BROKER" | "DEX";
  connectionType: ConnectionType;
  status: ConnectionStatus;
  permissions: ExchangePermissions;
  latencyMs: number;
  balanceUsd: number;
  lastSynced: string;
  maskedKey: string;
  accountType: "SPOT & PERP" | "CFD / FOREX" | "NON_CUSTODIAL";
}

export interface WhatsAppTradeProposal {
  symbol: string;
  side: "LONG" | "SHORT";
  entryPrice: number;
  targetPriceTp1: number;
  targetPriceTp2: number;
  stopLossPrice: number;
  riskUsd: number;
  riskPct: number;
  estRewardUsd: number;
  convictionPct: number;
  timeframe: string;
  catalyst: string;
  exchangeName: string;
  status: "PENDING" | "APPROVED" | "REJECTED" | "EXPIRED";
}

export interface WhatsAppMessage {
  id: string;
  sender: "USER" | "ATLAS_AI";
  timestamp: string;
  text: string;
  audioDuration?: string;
  proposal?: WhatsAppTradeProposal;
  status: "SENT" | "DELIVERED" | "READ";
}

export interface SocialBroadcast {
  id: string;
  platform: "TWITTER" | "DISCORD" | "TELEGRAM_VIP";
  timestamp: string;
  title: string;
  content: string;
  tags: string[];
  reachCount: number;
  isSanitized: boolean; // Confirms user equity & account balance are stripped
}

export const ATLAS_STATIC_IPS = ["198.51.100.42", "198.51.100.43"];

export const INITIAL_EXCHANGES: ConnectedExchange[] = [
  {
    id: "binance-01",
    name: "Binance",
    category: "CRYPTO_EXCHANGE",
    connectionType: "API_KEY",
    status: "CONNECTED",
    permissions: {
      canRead: true,
      canTrade: true,
      canWithdraw: false, // 100% Safe
    },
    latencyMs: 4,
    balanceUsd: 84250.0,
    lastSynced: "Just now",
    maskedKey: "vm4K••••••••••••w9Q1",
    accountType: "SPOT & PERP",
  },
  {
    id: "bybit-01",
    name: "Bybit",
    category: "CRYPTO_EXCHANGE",
    connectionType: "API_KEY",
    status: "CONNECTED",
    permissions: {
      canRead: true,
      canTrade: true,
      canWithdraw: false, // 100% Safe
    },
    latencyMs: 6,
    balanceUsd: 41230.0,
    lastSynced: "1m ago",
    maskedKey: "xL92••••••••••••01Fa",
    accountType: "SPOT & PERP",
  },
  {
    id: "coinbase-01",
    name: "Coinbase Advanced",
    category: "CRYPTO_EXCHANGE",
    connectionType: "OAUTH",
    status: "CONNECTED",
    permissions: {
      canRead: true,
      canTrade: true,
      canWithdraw: false,
    },
    latencyMs: 12,
    balanceUsd: 15400.0,
    lastSynced: "3m ago",
    maskedKey: "OAuth2 • Authorized Token",
    accountType: "SPOT & PERP",
  },
  {
    id: "phantom-01",
    name: "Hyperliquid / Phantom",
    category: "DEX",
    connectionType: "WEB3_WALLET",
    status: "CONNECTED",
    permissions: {
      canRead: true,
      canTrade: true,
      canWithdraw: false,
    },
    latencyMs: 18,
    balanceUsd: 9500.0,
    lastSynced: "5m ago",
    maskedKey: "0x7F2a••••••••4b19",
    accountType: "NON_CUSTODIAL",
  },
];

export const INITIAL_WHATSAPP_CHAT: WhatsAppMessage[] = [
  {
    id: "wa-01",
    sender: "USER",
    timestamp: "10:14 AM",
    text: "Bhai BTC ka kya view hai abhi market mein?",
    status: "READ",
  },
  {
    id: "wa-02",
    sender: "ATLAS_AI",
    timestamp: "10:14 AM",
    text: "Bhai, BTC abhi $86,234 par consolidate kar raha hai. 4H chart par bullish flag ban raha hai aur whale outflows positive hain. Resistance $87,500 par hai aur primary support $84,200 par hai. Momentum Bullish hai (Conviction 88%).",
    status: "READ",
  },
  {
    id: "wa-03",
    sender: "USER",
    timestamp: "10:20 AM",
    text: "Aaj ka net profit kitna hua hai?",
    status: "READ",
  },
  {
    id: "wa-04",
    sender: "ATLAS_AI",
    timestamp: "10:20 AM",
    text: "Aaj aapka Realized PnL +$866.00 (+2.1%) hai. Binance aur Bybit par 2 active positions open hain (BTC Long aur EUR/USD Long). Risk Gate status NORMAL hai.",
    status: "READ",
  },
  {
    id: "wa-05",
    sender: "ATLAS_AI",
    timestamp: "10:28 AM",
    text: "Bhai! Multi-Agent Swarm ne SOL/USDT par A+ Institutional Setup detect kiya hai:",
    proposal: {
      symbol: "SOL/USDT",
      side: "LONG",
      entryPrice: 121.5,
      targetPriceTp1: 128.0,
      targetPriceTp2: 134.5,
      stopLossPrice: 117.8,
      riskUsd: 250.0,
      riskPct: 1.2,
      estRewardUsd: 680.0,
      convictionPct: 91,
      timeframe: "15M Liquidity Sweep",
      catalyst: "15M Bullish FVG Retest + Whale Inflow",
      exchangeName: "Binance Spot/Perp",
      status: "PENDING",
    },
    status: "READ",
  },
];

export const INITIAL_SOCIAL_BROADCASTS: SocialBroadcast[] = [
  {
    id: "soc-01",
    platform: "TWITTER",
    timestamp: "25m ago",
    title: "Institutional Orderflow Update: BTC Consolidation",
    content: "BTC continues compressing above the $85.8K liquidity pocket. Delta CVD divergence indicates aggressive absorption from spot desks. Resistance mapped at $87.5K. Invalidation below $84.2K.",
    tags: ["#BTC", "#OrderFlow", "#InstitutionalTrading"],
    reachCount: 4280,
    isSanitized: true,
  },
  {
    id: "soc-02",
    platform: "DISCORD",
    timestamp: "1h ago",
    title: "Macro Sentinel Alert: FOMC Prep",
    content: "FOMC Rate Decision countdown: 2h 45m. Volatility expansion expected. All automated slicers have engaged news blackout guards ±15m.",
    tags: ["#Macro", "#FOMC", "#RiskGate"],
    reachCount: 1540,
    isSanitized: true,
  },
  {
    id: "soc-03",
    platform: "TELEGRAM_VIP",
    timestamp: "3h ago",
    title: "Trade Debrief: SOL FVG Long Scale-Out",
    content: "TP1 filled (+5.3%). Stop-Loss automatically promoted to Breakeven (+0.2% to cover fees). 50% runner floating with 1.5x ATR trailing band.",
    tags: ["#Alpha", "#AtlasSwarm", "#TradeReview"],
    reachCount: 920,
    isSanitized: true,
  },
];

export function validateApiKey(apiKey: string, apiSecret: string): { isValid: boolean; permissions: ExchangePermissions; error?: string } {
  if (!apiKey || apiKey.length < 12) {
    return {
      isValid: false,
      permissions: { canRead: false, canTrade: false, canWithdraw: false },
      error: "Invalid API Key format. Must be at least 12 characters.",
    };
  }

  // Simulated permission analysis based on key pattern
  const isWithdrawalEnabled = apiKey.toLowerCase().includes("withdraw") || apiKey.startsWith("w-");
  if (isWithdrawalEnabled) {
    return {
      isValid: false,
      permissions: { canRead: true, canTrade: true, canWithdraw: true },
      error: "SECURITY VIOLATION: Withdrawal permission is enabled on this key! Atlas strictly refuses withdrawal-enabled keys to protect user capital. Please uncheck 'Enable Withdrawals' in your exchange settings.",
    };
  }

  return {
    isValid: true,
    permissions: { canRead: true, canTrade: true, canWithdraw: false },
  };
}
