export interface TwapSlice {
  sliceNumber: number;
  timestamp: string;
  qty: number;
  price: number;
  notional: number;
}

export interface TwapOrder {
  id: string;
  symbol: string;
  side: "BUY" | "SELL";
  totalNotional: number;
  totalQuantity: number;
  filledQuantity: number;
  filledNotional: number;
  durationMinutes: number;
  totalSlices: number;
  filledSlices: number;
  avgPrice: number;
  arrivalPrice: number;
  status: "RUNNING" | "PAUSED" | "COMPLETED";
  createdAt: string;
  sliceHistory: TwapSlice[];
}

export interface GridLevelOrder {
  id: string;
  levelIndex: number;
  price: number;
  side: "BUY" | "SELL";
  status: "PENDING" | "FILLED";
}

export interface GridBot {
  id: string;
  symbol: string;
  lowerPrice: number;
  upperPrice: number;
  gridLevels: number;
  investmentUsd: number;
  realizedProfitUsd: number;
  unrealizedPnlUsd: number;
  gridSpreadPct: number;
  status: "RUNNING" | "PAUSED";
  createdAt: string;
  orders: GridLevelOrder[];
}

export interface DcaBot {
  id: string;
  symbol: string;
  baseOrderUsd: number;
  safetyOrderUsd: number;
  maxSafetyOrders: number;
  deviationPct: number;
  tpPct: number;
  avgEntryPrice: number;
  filledOrders: number;
  totalInvested: number;
  status: "RUNNING" | "PAUSED";
  createdAt: string;
}

export interface SmartExitMandate {
  tp1Pct: number;
  tp1SizePct: number;
  autoBreakeven: boolean;
  tp2Pct: number;
  tp2SizePct: number;
  tp3AtrMultiplier: number;
  maxDailyLossUsd: number;
  newsBlackoutEnabled: boolean;
  isActive: boolean;
}

export const INITIAL_TWAP_ORDERS: TwapOrder[] = [
  {
    id: "twap-01",
    symbol: "BTC/USDT",
    side: "BUY",
    totalNotional: 50000,
    totalQuantity: 0.58,
    filledQuantity: 0.348,
    filledNotional: 30000,
    durationMinutes: 30,
    totalSlices: 10,
    filledSlices: 6,
    avgPrice: 86210.4,
    arrivalPrice: 86234.0,
    status: "RUNNING",
    createdAt: "10:15:00",
    sliceHistory: [
      { sliceNumber: 1, timestamp: "10:15:00", qty: 0.058, price: 86230.0, notional: 5001.34 },
      { sliceNumber: 2, timestamp: "10:18:00", qty: 0.058, price: 86215.5, notional: 5000.5 },
      { sliceNumber: 3, timestamp: "10:21:00", qty: 0.058, price: 86208.0, notional: 5000.06 },
      { sliceNumber: 4, timestamp: "10:24:00", qty: 0.058, price: 86195.2, notional: 4999.32 },
      { sliceNumber: 5, timestamp: "10:27:00", qty: 0.058, price: 86202.8, notional: 4999.76 },
      { sliceNumber: 6, timestamp: "10:30:00", qty: 0.058, price: 86211.0, notional: 5000.24 },
    ],
  },
  {
    id: "twap-02",
    symbol: "ETH/USDT",
    side: "SELL",
    totalNotional: 25000,
    totalQuantity: 9.1,
    filledQuantity: 9.1,
    filledNotional: 25000,
    durationMinutes: 15,
    totalSlices: 5,
    filledSlices: 5,
    avgPrice: 2748.2,
    arrivalPrice: 2745.0,
    status: "COMPLETED",
    createdAt: "09:45:00",
    sliceHistory: [
      { sliceNumber: 1, timestamp: "09:45:00", qty: 1.82, price: 2745.2, notional: 4996.26 },
      { sliceNumber: 2, timestamp: "09:48:00", qty: 1.82, price: 2747.0, notional: 4999.54 },
      { sliceNumber: 3, timestamp: "09:51:00", qty: 1.82, price: 2749.1, notional: 5003.36 },
      { sliceNumber: 4, timestamp: "09:54:00", qty: 1.82, price: 2750.0, notional: 5005.0 },
      { sliceNumber: 5, timestamp: "09:57:00", qty: 1.82, price: 2749.8, notional: 5004.64 },
    ],
  },
];

export const INITIAL_GRID_BOTS: GridBot[] = [
  {
    id: "grid-01",
    symbol: "SOL/USDT",
    lowerPrice: 110.0,
    upperPrice: 130.0,
    gridLevels: 8,
    investmentUsd: 15000,
    realizedProfitUsd: 428.5,
    unrealizedPnlUsd: 84.2,
    gridSpreadPct: 1.85,
    status: "RUNNING",
    createdAt: "08:00:00",
    orders: [
      { id: "g-1", levelIndex: 1, price: 112.5, side: "BUY", status: "PENDING" },
      { id: "g-2", levelIndex: 2, price: 115.0, side: "BUY", status: "PENDING" },
      { id: "g-3", levelIndex: 3, price: 117.5, side: "BUY", status: "FILLED" },
      { id: "g-4", levelIndex: 4, price: 120.0, side: "SELL", status: "PENDING" },
      { id: "g-5", levelIndex: 5, price: 122.5, side: "SELL", status: "PENDING" },
      { id: "g-6", levelIndex: 6, price: 125.0, side: "SELL", status: "PENDING" },
    ],
  },
];

export const INITIAL_DCA_BOTS: DcaBot[] = [
  {
    id: "dca-01",
    symbol: "BTC/USDT",
    baseOrderUsd: 2000,
    safetyOrderUsd: 4000,
    maxSafetyOrders: 4,
    deviationPct: 1.5,
    tpPct: 2.2,
    avgEntryPrice: 85920.0,
    filledOrders: 2,
    totalInvested: 6000,
    status: "RUNNING",
    createdAt: "06:30:00",
  },
];

export const DEFAULT_SMART_MANDATE: SmartExitMandate = {
  tp1Pct: 2.5,
  tp1SizePct: 50,
  autoBreakeven: true,
  tp2Pct: 5.0,
  tp2SizePct: 25,
  tp3AtrMultiplier: 1.5,
  maxDailyLossUsd: 3000,
  newsBlackoutEnabled: true,
  isActive: true,
};
