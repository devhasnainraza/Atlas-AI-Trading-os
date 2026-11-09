import { NextRequest, NextResponse } from "next/server";
import { getLatestPendingTrade, clearPendingTrade } from "../../../../lib/pendingTradeStore";
import { executeTrade, BrokerConfig } from "../../../../lib/brokerService";
import { sendMetaWhatsApp, sendTwilioWhatsApp, DEFAULT_CHANNEL_CONFIG } from "../../../../lib/channelService";
import { getSessionUser } from "../../../../lib/server/session";
import { getDatabase } from "../../../../lib/server/db";
import { decryptVaultSecret } from "../../../../lib/server/cryptoVault";

/**
 * POST /api/broker/execute
 * ─────────────────────────────────────────────────────────────
 * Called when user sends YES from WhatsApp (or from the UI).
 * Looks up the pending trade, executes it on Binance (paper or real)
 * using the user's encrypted API key from the database vault.
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    let { tradeId, userApproved, brokerConfig } = body as {
      tradeId?: string;
      userApproved: boolean;
      brokerConfig?: BrokerConfig;
    };

    // If no brokerConfig provided, check authenticated user's vault
    if (!brokerConfig) {
      const user = getSessionUser(req);
      if (user) {
        const db = getDatabase();
        const stmt = db.prepare(`
          SELECT encrypted_payload, iv, auth_tag
          FROM user_credentials
          WHERE user_id = ? AND category = 'BROKER' AND status = 'ACTIVE'
          LIMIT 1
        `);
        const cred = stmt.get(user.id) as any;
        if (cred) {
          const decrypted = decryptVaultSecret({
            encryptedData: cred.encrypted_payload,
            iv: cred.iv,
            authTag: cred.auth_tag,
          });
          const { apiKey, apiSecret } = JSON.parse(decrypted);
          brokerConfig = { apiKey, apiSecret };
        }
      }
    }

    // Get latest pending trade
    const trade = getLatestPendingTrade();

    if (!trade) {
      return NextResponse.json(
        { success: false, message: "No pending trade found. The proposal may have expired (15min TTL)." },
        { status: 404 }
      );
    }

    // If user cancelled
    if (!userApproved) {
      clearPendingTrade(trade.tradeId);
      return NextResponse.json({
        success: true,
        cancelled: true,
        message: "Trade proposal discarded. Capital preserved.",
      });
    }

    // Execute the trade
    const result = await executeTrade(
      brokerConfig,
      trade.brokerSymbol,
      trade.side,
      trade.sizeUsd,
      trade.entryPrice
    );

    // Clear the pending trade
    clearPendingTrade(trade.tradeId);

    // Build confirmation message
    const timeStr = new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit" });
    const emoji = result.success ? "✅" : "❌";
    const confirmMsg = result.success
      ? `${emoji} ORDER FILLED — ${trade.symbol}\n\n` +
        `Side: ${trade.side}\n` +
        `Fill Price: $${result.price.toLocaleString()}\n` +
        `Quantity: ${result.quantity}\n` +
        `Mode: ${result.mode}\n` +
        `Order ID: ${result.orderId}\n\n` +
        `TP Target: $${trade.tpPrice.toLocaleString()} (+${(((trade.tpPrice - result.price) / result.price) * 100).toFixed(2)}%)\n` +
        `SL Guard: $${trade.slPrice.toLocaleString()} (${(((result.price - trade.slPrice) / result.price) * 100).toFixed(2)}%)\n\n` +
        `Atlas Risk Gate: ARMED ✓\nTime: ${timeStr} UTC`
      : `${emoji} ORDER FAILED — ${trade.symbol}\n\n${result.message}\n\nTrade NOT executed. Capital preserved.`;

    // Send WhatsApp confirmation
    const cfg = DEFAULT_CHANNEL_CONFIG.whatsapp;
    const recipient = cfg.userPhoneNumber;
    if (cfg.provider === "META_CLOUD" && cfg.metaAccessToken && cfg.metaPhoneNumberId && recipient) {
      await sendMetaWhatsApp(
        cfg.metaAccessToken,
        cfg.metaPhoneNumberId,
        recipient,
        confirmMsg
      );
    } else if (cfg.accountSid && cfg.authToken && cfg.fromNumber && recipient) {
      await sendTwilioWhatsApp(
        cfg.accountSid,
        cfg.authToken,
        cfg.fromNumber,
        recipient,
        confirmMsg
      );
    }

    return NextResponse.json({
      success: result.success,
      result,
      message: confirmMsg,
    });
  } catch (err: any) {
    return NextResponse.json(
      { success: false, message: err.message ?? "Internal server error" },
      { status: 500 }
    );
  }
}
