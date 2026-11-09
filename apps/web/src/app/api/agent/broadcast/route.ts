import { NextRequest, NextResponse } from "next/server";
import {
  DEFAULT_CHANNEL_CONFIG,
  sendMetaWhatsApp,
  sendDiscordAlert,
} from "../../../../lib/channelService";

/**
 * POST /api/agent/broadcast
 * ─────────────────────────────────────────────────────────────
 * Manager Agent hourly broadcast endpoint.
 * Called by the client-side AgentLoop every hour to post a
 * live portfolio + market summary to all enabled social channels.
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const {
      balance = 100000,
      equity = 100000,
      dailyPnl = 0,
      dailyPnlPct = 0,
      positionCount = 0,
      positions = [],
      topSignal = null,
      riskStatus = "NORMAL",
      nextScanMin = 15,
    } = body;

    const now = new Date();
    const timeStr = now.toLocaleTimeString("en-US", {
      hour12: false, hour: "2-digit", minute: "2-digit", timeZone: "UTC"
    });
    const dateStr = now.toLocaleDateString("en-US", {
      month: "short", day: "numeric", timeZone: "UTC"
    });

    const pnlSign = dailyPnl >= 0 ? "+" : "";
    const riskEmoji = riskStatus === "NORMAL" ? "✅" : riskStatus === "ALERT" ? "⚠️" : "🚨";
    const pnlEmoji = dailyPnl >= 0 ? "📈" : "📉";

    // Build position list
    const posLines = positions.slice(0, 3).map((p: any) => {
      const pnlStr = p.pnlUsd >= 0 ? `+$${p.pnlUsd.toFixed(2)}` : `-$${Math.abs(p.pnlUsd).toFixed(2)}`;
      const side = p.side === "LONG" ? "🔵" : "🔴";
      return `${side} ${p.symbol} ${p.side}: ${pnlStr} (${p.pnlPct >= 0 ? "+" : ""}${p.pnlPct.toFixed(2)}%)`;
    });

    const topSignalLine = topSignal
      ? `\n🎯 Top Signal: ${topSignal.symbol} ${topSignal.side} (${topSignal.conviction}% conviction)\n`
      : "";

    const whatsappMsg =
      `📊 *ATLAS MANAGER REPORT — ${timeStr} UTC (${dateStr})*\n\n` +
      `Balance: $${balance.toLocaleString()}\n` +
      `Equity:  $${equity.toLocaleString()} (${pnlEmoji} ${pnlSign}${dailyPnlPct.toFixed(2)}% today)\n` +
      `Realized P&L: ${pnlSign}$${Math.abs(dailyPnl).toFixed(2)}\n` +
      `Open Positions: ${positionCount}\n` +
      (posLines.length > 0 ? `\n${posLines.join("\n")}\n` : "") +
      topSignalLine +
      `\n${riskEmoji} Risk Gate: ${riskStatus}\n` +
      `⏱ Next Scan: ${nextScanMin} min\n\n` +
      `Reply *STATUS* for live prices | *STOP* to pause agent`;

    const results: string[] = [];

    // Send to WhatsApp
    const waCfg = DEFAULT_CHANNEL_CONFIG.whatsapp;
    if (waCfg.isEnabled && waCfg.metaAccessToken && waCfg.metaPhoneNumberId && waCfg.userPhoneNumber) {
      const waResult = await sendMetaWhatsApp(
        waCfg.metaAccessToken,
        waCfg.metaPhoneNumberId,
        waCfg.userPhoneNumber,
        whatsappMsg
      );
      results.push(`WhatsApp: ${waResult.success ? "OK" : waResult.message}`);
    }

    // Send to Discord
    const discordCfg = DEFAULT_CHANNEL_CONFIG.discord;
    if (discordCfg.isEnabled && discordCfg.webhookUrl) {
      const discordResult = await sendDiscordAlert(
        discordCfg.webhookUrl,
        `📊 Atlas Manager Report — ${timeStr} UTC`,
        whatsappMsg.replace(/\*/g, "**"),
        dailyPnl >= 0 ? 0x22c55e : 0xef4444
      );
      results.push(`Discord: ${discordResult.success ? "OK" : discordResult.message}`);
    }

    return NextResponse.json({
      success: true,
      dispatched: results,
      message: whatsappMsg,
      timestamp: now.toISOString(),
    });
  } catch (err: any) {
    return NextResponse.json(
      { success: false, message: err.message ?? "Broadcast failed" },
      { status: 500 }
    );
  }
}
