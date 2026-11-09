/**
 * Server-side Pending Trade Store
 * ─────────────────────────────────
 * Stores trade proposals awaiting user YES/NO via WhatsApp.
 * Module-level singleton — persists across API calls in same Node process.
 * TTL: 15 minutes auto-expiry.
 */

export interface PendingTrade {
  tradeId: string;
  symbol: string;
  side: "BUY" | "SELL";
  entryPrice: number;
  tpPrice: number;
  slPrice: number;
  sizeUsd: number;
  riskPct: number;
  conviction: number;
  source: "AGENT_LOOP" | "MANUAL" | "SWARM";
  createdAt: number;
  expiresAt: number;
  brokerSymbol: string;
  note: string;
}

const globalStore = globalThis as unknown as { __atlasPendingTradeMap?: Map<string, PendingTrade> };
if (!globalStore.__atlasPendingTradeMap) {
  globalStore.__atlasPendingTradeMap = new Map<string, PendingTrade>();
}
const pendingTradeMap = globalStore.__atlasPendingTradeMap;

function pruneExpired() {
  const now = Date.now();
  for (const [id, trade] of pendingTradeMap) {
    if (now > trade.expiresAt) pendingTradeMap.delete(id);
  }
}

export function storePendingTrade(trade: PendingTrade): void {
  pruneExpired();
  pendingTradeMap.clear(); // only one pending proposal at a time
  pendingTradeMap.set(trade.tradeId, trade);
}

export function getLatestPendingTrade(): PendingTrade | null {
  pruneExpired();
  if (pendingTradeMap.size === 0) return null;
  const entry = pendingTradeMap.entries().next().value;
  return entry ? entry[1] : null;
}

export function getPendingTrade(tradeId: string): PendingTrade | null {
  pruneExpired();
  return pendingTradeMap.get(tradeId) ?? null;
}

export function clearPendingTrade(tradeId: string): boolean {
  return pendingTradeMap.delete(tradeId);
}

export function clearAllPendingTrades(): void {
  pendingTradeMap.clear();
}
