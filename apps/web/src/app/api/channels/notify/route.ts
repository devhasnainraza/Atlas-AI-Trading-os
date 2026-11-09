import { NextRequest, NextResponse } from "next/server";
import {
  sendMetaWhatsApp,
  sendTwilioWhatsApp,
  sendTelegramMessage,
  sendDiscordAlert,
  DEFAULT_CHANNEL_CONFIG,
  ChannelConfig,
} from "../../../../lib/channelService";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { title, message, category = "ALERT", config } = body;

    if (!message) {
      return NextResponse.json(
        { success: false, error: "Message content is required" },
        { status: 400 }
      );
    }

    // Resolve channel config: merge incoming config with DEFAULT_CHANNEL_CONFIG
    const activeConfig: ChannelConfig = {
      whatsapp: {
        ...DEFAULT_CHANNEL_CONFIG.whatsapp,
        ...(config?.whatsapp || {}),
      },
      telegram: {
        ...DEFAULT_CHANNEL_CONFIG.telegram,
        ...(config?.telegram || {}),
      },
      discord: {
        ...DEFAULT_CHANNEL_CONFIG.discord,
        ...(config?.discord || {}),
      },
      twitter: {
        ...DEFAULT_CHANNEL_CONFIG.twitter,
        ...(config?.twitter || {}),
      },
    };

    const results: any[] = [];

    // 1. Dispatch to WhatsApp
    const wa = activeConfig.whatsapp;
    if (wa.isEnabled !== false) {
      const formattedTitle = title ? `⚡ ${title}\n\n` : "";
      const waText = `[ATLAS OS · ${category}]\n${formattedTitle}${message}\n\n_Auto-Breakeven & SL Armed · Risk Gate: NORMAL_`;

      if (wa.provider === "META_CLOUD") {
        const token = wa.metaAccessToken || DEFAULT_CHANNEL_CONFIG.whatsapp.metaAccessToken!;
        const phoneId = wa.metaPhoneNumberId || DEFAULT_CHANNEL_CONFIG.whatsapp.metaPhoneNumberId!;
        const recipient = wa.userPhoneNumber || DEFAULT_CHANNEL_CONFIG.whatsapp.userPhoneNumber!;

        const waRes = await sendMetaWhatsApp(token, phoneId, recipient, waText);
        results.push(waRes);
      } else if (wa.accountSid && wa.authToken && wa.fromNumber && wa.userPhoneNumber) {
        const waRes = await sendTwilioWhatsApp(wa.accountSid, wa.authToken, wa.fromNumber, wa.userPhoneNumber, waText);
        results.push(waRes);
      }
    }

    // 2. Dispatch to Telegram (if enabled)
    const tg = activeConfig.telegram;
    if (tg.isEnabled && tg.botToken && tg.chatId) {
      const tgText = `*${title || "Atlas Trading Alert"}*\n\n${message}\n\n_Atlas AI Trading OS_`;
      const isTradeProposal = category === "TRADE_PROPOSAL";
      const tgRes = await sendTelegramMessage(tg.botToken, tg.chatId, tgText, isTradeProposal);
      results.push(tgRes);
    }

    // 3. Dispatch to Discord (if enabled)
    const dc = activeConfig.discord;
    if (dc.isEnabled && dc.webhookUrl) {
      const dcRes = await sendDiscordAlert(dc.webhookUrl, title || "Atlas Alert", message);
      results.push(dcRes);
    }

    return NextResponse.json({
      success: true,
      deliveredTo: results.filter((r) => r.success).map((r) => r.channel),
      results,
    });
  } catch (err: any) {
    return NextResponse.json(
      { success: false, error: err.message || "Failed to dispatch channel notifications" },
      { status: 500 }
    );
  }
}
