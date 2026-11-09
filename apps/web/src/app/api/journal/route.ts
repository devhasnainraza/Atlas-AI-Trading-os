import { NextRequest, NextResponse } from "next/server";
import { getSessionUser } from "@/lib/server/session";
import { getDatabase } from "@/lib/server/db";

export interface DBJournalTrade {
  id: string;
  time: string;
  symbol: string;
  side: "LONG" | "SHORT";
  entryPrice: number;
  exitPrice: number;
  sizeStr: string;
  pnlUsd: number;
  pnlPct: number;
  tags: string[];
  status: "CLOSED" | "FLATTENED";
}

const SEED_TRADES: Omit<DBJournalTrade, "id">[] = [
  {
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
    time: "11:50:00",
    symbol: "BTC/USDT",
    side: "LONG",
    entryPrice: 84250.0,
    exitPrice: 86120.0,
    sizeStr: "0.20 BTC",
    pnlUsd: 374.0,
    pnlPct: 2.22,
    tags: ["A+ Setup", "Rule Followed"],
    status: "CLOSED",
  },
];

export async function GET(req: NextRequest) {
  try {
    const user = getSessionUser(req);
    if (!user) {
      return NextResponse.json({ trades: [] });
    }

    const db = getDatabase();
    const rows = db.prepare(`
      SELECT id, time, symbol, side, entry_price, exit_price, size_str, pnl_usd, pnl_pct, tags, status
      FROM user_journal
      WHERE user_id = ?
      ORDER BY rowid DESC
    `).all(user.id) as any[];

    const trades: DBJournalTrade[] = rows.map((r) => ({
      id: r.id,
      time: r.time,
      symbol: r.symbol,
      side: r.side as "LONG" | "SHORT",
      entryPrice: r.entry_price,
      exitPrice: r.exit_price,
      sizeStr: r.size_str,
      pnlUsd: r.pnl_usd,
      pnlPct: r.pnl_pct,
      tags: r.tags ? JSON.parse(r.tags) : [],
      status: r.status as "CLOSED" | "FLATTENED",
    }));

    return NextResponse.json({ trades });
  } catch (error: any) {
    console.error("GET /api/journal error:", error);
    return NextResponse.json({ error: error.message || "Failed to fetch journal" }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  try {
    const user = getSessionUser(req);
    if (!user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await req.json();
    const { action } = body;

    const db = getDatabase();

    // Action: Seed sample trades for this user
    if (action === "SEED") {
      const insert = db.prepare(`
        INSERT INTO user_journal (id, user_id, time, symbol, side, entry_price, exit_price, size_str, pnl_usd, pnl_pct, tags, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `);

      for (const t of SEED_TRADES) {
        insert.run(
          "tr-" + Math.random().toString(36).substring(2, 9),
          user.id,
          t.time,
          t.symbol,
          t.side,
          t.entryPrice,
          t.exitPrice,
          t.sizeStr,
          t.pnlUsd,
          t.pnlPct,
          JSON.stringify(t.tags),
          t.status
        );
      }

      return NextResponse.json({ success: true, message: "Sample trades loaded into journal" });
    }

    // Action: Clear all journal trades
    if (action === "CLEAR") {
      db.prepare("DELETE FROM user_journal WHERE user_id = ?").run(user.id);
      return NextResponse.json({ success: true, message: "Journal cleared" });
    }

    // Action: Add new trade
    const trade = body.trade;
    if (!trade || !trade.symbol) {
      return NextResponse.json({ error: "Invalid trade payload" }, { status: 400 });
    }

    const tradeId = trade.id || "tr-" + Date.now();
    const now = new Date();
    const timeStr = trade.time || `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`;

    db.prepare(`
      INSERT INTO user_journal (id, user_id, time, symbol, side, entry_price, exit_price, size_str, pnl_usd, pnl_pct, tags, status)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      tradeId,
      user.id,
      timeStr,
      trade.symbol,
      trade.side || "LONG",
      Number(trade.entryPrice) || 0,
      Number(trade.exitPrice) || 0,
      trade.sizeStr || "1.00 Unit",
      Number(trade.pnlUsd) || 0,
      Number(trade.pnlPct) || 0,
      JSON.stringify(trade.tags || ["Rule Followed"]),
      trade.status || "CLOSED"
    );

    return NextResponse.json({ success: true, id: tradeId });
  } catch (error: any) {
    console.error("POST /api/journal error:", error);
    return NextResponse.json({ error: error.message || "Failed to update journal" }, { status: 500 });
  }
}

export async function PUT(req: NextRequest) {
  try {
    const user = getSessionUser(req);
    if (!user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await req.json();
    const { tradeId, tags } = body;
    if (!tradeId || !tags) {
      return NextResponse.json({ error: "Missing tradeId or tags" }, { status: 400 });
    }

    const db = getDatabase();
    db.prepare(`
      UPDATE user_journal
      SET tags = ?
      WHERE id = ? AND user_id = ?
    `).run(JSON.stringify(tags), tradeId, user.id);

    return NextResponse.json({ success: true });
  } catch (error: any) {
    console.error("PUT /api/journal error:", error);
    return NextResponse.json({ error: error.message || "Failed to update trade tags" }, { status: 500 });
  }
}
