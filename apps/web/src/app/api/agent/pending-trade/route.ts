import { NextRequest, NextResponse } from "next/server";
import {
  storePendingTrade,
  getLatestPendingTrade,
  clearAllPendingTrades,
  PendingTrade,
} from "../../../../lib/pendingTradeStore";

/** GET /api/agent/pending-trade — fetch current pending trade */
export async function GET() {
  const trade = getLatestPendingTrade();
  if (!trade) {
    return NextResponse.json({ pending: false, trade: null });
  }
  const timeLeftMs = trade.expiresAt - Date.now();
  return NextResponse.json({
    pending: true,
    trade,
    timeLeftSeconds: Math.max(0, Math.round(timeLeftMs / 1000)),
  });
}

/** POST /api/agent/pending-trade — store a new pending trade from agent loop */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const trade: PendingTrade = {
      tradeId: `trade-${Date.now()}`,
      symbol: body.symbol,
      side: body.side,
      entryPrice: body.entryPrice,
      tpPrice: body.tpPrice,
      slPrice: body.slPrice,
      sizeUsd: body.sizeUsd ?? 1000,
      riskPct: body.riskPct ?? 1.0,
      conviction: body.conviction ?? 80,
      source: body.source ?? "AGENT_LOOP",
      createdAt: Date.now(),
      expiresAt: Date.now() + 15 * 60 * 1000, // 15 minute TTL
      brokerSymbol: body.brokerSymbol ?? body.symbol.replace("/", ""),
      note: body.note ?? "",
    };
    storePendingTrade(trade);
    return NextResponse.json({ success: true, tradeId: trade.tradeId, trade });
  } catch (err: any) {
    return NextResponse.json({ success: false, message: err.message }, { status: 400 });
  }
}

/** DELETE /api/agent/pending-trade — clear all pending trades */
export async function DELETE() {
  clearAllPendingTrades();
  return NextResponse.json({ success: true, message: "All pending trades cleared." });
}
