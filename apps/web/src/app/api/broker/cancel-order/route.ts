import { NextRequest, NextResponse } from "next/server";
import crypto from "node:crypto";
import { getSessionUser } from "@/lib/server/session";
import { getDatabase } from "@/lib/server/db";
import { decryptVaultSecret } from "@/lib/server/cryptoVault";

export async function POST(req: NextRequest) {
  try {
    const user = getSessionUser(req);
    const body = await req.json();
    const { symbol, orderId } = body;

    if (!orderId) {
      return NextResponse.json({ error: "Missing orderId" }, { status: 400 });
    }

    if (!user) {
      // Unauthenticated / paper order cancel
      return NextResponse.json({ success: true, mode: "PAPER", orderId });
    }

    const db = getDatabase();
    const stmt = db.prepare(`
      SELECT encrypted_payload, iv, auth_tag
      FROM user_credentials
      WHERE user_id = ? AND category = 'BROKER' AND status = 'ACTIVE'
      LIMIT 1
    `);
    const cred = stmt.get(user.id) as any;

    if (!cred) {
      // Paper cancel
      return NextResponse.json({ success: true, mode: "PAPER", orderId });
    }

    // Decrypt credentials in-memory
    const decrypted = decryptVaultSecret({
      encryptedData: cred.encrypted_payload,
      iv: cred.iv,
      authTag: cred.auth_tag,
    });
    const { apiKey, apiSecret } = JSON.parse(decrypted);

    // Call Binance cancel order API
    const formattedSymbol = (symbol || "BTCUSDT").replace(/[\/-]/g, "").toUpperCase();
    const timestamp = Date.now();
    const queryString = `symbol=${formattedSymbol}&orderId=${orderId}&timestamp=${timestamp}`;
    const signature = crypto.createHmac("sha256", apiSecret).update(queryString).digest("hex");

    const binanceRes = await fetch(`https://api.binance.com/api/v3/order?${queryString}&signature=${signature}`, {
      method: "DELETE",
      headers: {
        "X-MBX-APIKEY": apiKey,
      },
    });

    const data = await binanceRes.json();
    if (!binanceRes.ok) {
      // If order not found or already filled, still release in UI
      console.warn("Binance cancel order warning:", data);
      return NextResponse.json({
        success: true,
        mode: "LIVE_REMOVED",
        orderId,
        warning: data.msg || "Order removed from local active telemetry",
      });
    }

    return NextResponse.json({ success: true, mode: "LIVE", orderId, binance: data });
  } catch (error: any) {
    console.error("Cancel order error:", error);
    return NextResponse.json({ error: error.message || "Failed to cancel order" }, { status: 500 });
  }
}
