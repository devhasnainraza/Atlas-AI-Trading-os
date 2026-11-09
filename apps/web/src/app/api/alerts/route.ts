import { NextRequest, NextResponse } from "next/server";
import { getSessionUser } from "@/lib/server/session";
import { getDatabase } from "@/lib/server/db";

export async function GET(req: NextRequest) {
  try {
    const user = getSessionUser(req);
    if (!user) {
      return NextResponse.json({ alerts: [] });
    }

    const db = getDatabase();
    const rows = db.prepare(`
      SELECT id, symbol, type, target_value, current_value, note, status, created_at, sound_enabled
      FROM user_alerts
      WHERE user_id = ?
      ORDER BY rowid DESC
    `).all(user.id) as any[];

    const alerts = rows.map((r) => ({
      id: r.id,
      symbol: r.symbol,
      type: r.type,
      targetValue: r.target_value,
      currentValue: r.current_value,
      note: r.note,
      status: r.status,
      createdAt: r.created_at,
      soundEnabled: Boolean(r.sound_enabled),
    }));

    return NextResponse.json({ alerts });
  } catch (error: any) {
    console.error("GET /api/alerts error:", error);
    return NextResponse.json({ error: error.message || "Failed to fetch alerts" }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  try {
    const user = getSessionUser(req);
    if (!user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await req.json();
    const { alert } = body;
    if (!alert || !alert.symbol) {
      return NextResponse.json({ error: "Invalid alert data" }, { status: 400 });
    }

    const db = getDatabase();
    const alertId = alert.id || "alt-" + Date.now();
    const now = new Date();
    const timeStr = alert.createdAt || `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`;

    db.prepare(`
      INSERT INTO user_alerts (id, user_id, symbol, type, target_value, current_value, note, status, created_at, sound_enabled)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      alertId,
      user.id,
      alert.symbol,
      alert.type,
      Number(alert.targetValue) || 0,
      Number(alert.currentValue || alert.targetValue) || 0,
      alert.note || "Alert",
      alert.status || "ACTIVE",
      timeStr,
      alert.soundEnabled !== false ? 1 : 0
    );

    return NextResponse.json({ success: true, id: alertId });
  } catch (error: any) {
    console.error("POST /api/alerts error:", error);
    return NextResponse.json({ error: error.message || "Failed to save alert" }, { status: 500 });
  }
}

export async function PUT(req: NextRequest) {
  try {
    const user = getSessionUser(req);
    if (!user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await req.json();
    const { alertId, status, triggeredAt } = body;
    if (!alertId) {
      return NextResponse.json({ error: "Missing alertId" }, { status: 400 });
    }

    const db = getDatabase();
    db.prepare(`
      UPDATE user_alerts
      SET status = ?
      WHERE id = ? AND user_id = ?
    `).run(status, alertId, user.id);

    return NextResponse.json({ success: true });
  } catch (error: any) {
    console.error("PUT /api/alerts error:", error);
    return NextResponse.json({ error: error.message || "Failed to update alert" }, { status: 500 });
  }
}

export async function DELETE(req: NextRequest) {
  try {
    const user = getSessionUser(req);
    if (!user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { searchParams } = new URL(req.url);
    const alertId = searchParams.get("id");
    if (!alertId) {
      return NextResponse.json({ error: "Missing alert id" }, { status: 400 });
    }

    const db = getDatabase();
    db.prepare("DELETE FROM user_alerts WHERE id = ? AND user_id = ?").run(alertId, user.id);

    return NextResponse.json({ success: true });
  } catch (error: any) {
    console.error("DELETE /api/alerts error:", error);
    return NextResponse.json({ error: error.message || "Failed to delete alert" }, { status: 500 });
  }
}
