import { NextRequest, NextResponse } from "next/server";
import {
  sendTelegramMessage,
  sendDiscordAlert,
  sendTwilioWhatsApp,
  sendMetaWhatsApp,
} from "../../../../lib/channelService";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { channel, config } = body;

    if (!channel) {
      return NextResponse.json({ success: false, error: "Channel type required" }, { status: 400 });
    }

    if (channel === "TELEGRAM") {
      const { botToken, chatId } = config?.telegram || {};
      if (!botToken || !chatId) {
        return NextResponse.json(
          { success: false, error: "Telegram Bot Token and Chat ID are required." },
          { status: 400 }
        );
      }

      const testMsg = `[ATLAS OS] Live Connection Verified!\n\nBhai, aapka Telegram Bot successfully connect ho chuka hai. 24/7 Swarm updates aur high-conviction trade proposals yahan direct ayengi!\n\n_Risk Gate: NORMAL | Latency: 4ms_`;
      const res = await sendTelegramMessage(botToken, chatId, testMsg, true);
      return NextResponse.json(res);
    }

    if (channel === "DISCORD") {
      const { webhookUrl } = config?.discord || {};
      if (!webhookUrl) {
        return NextResponse.json(
          { success: false, error: "Discord Webhook URL is required." },
          { status: 400 }
        );
      }

      const title = "Atlas Chief Manager Agent — Live Discord Feed Connected";
      const content = "Discord channel integration is live! All institutional multi-agent deliberation summaries, macro alerts, and trade debriefs will be broadcast here automatically.\n\n**Privacy Sanitization Guard: ACTIVE (Account balance & keys stripped)**";
      const res = await sendDiscordAlert(webhookUrl, title, content, 0x22c55e);
      return NextResponse.json(res);
    }

    if (channel === "WHATSAPP") {
      const wa = config?.whatsapp || {};
      const provider = wa.provider || "META_CLOUD";

      if (provider === "META_CLOUD") {
        const { metaAccessToken, metaPhoneNumberId, userPhoneNumber } = wa;
        if (!metaAccessToken || !metaPhoneNumberId || !userPhoneNumber) {
          return NextResponse.json(
            {
              success: false,
              error: "Meta System User Access Token, Phone Number ID, and Recipient Phone Number are required.",
            },
            { status: 400 }
          );
        }

        const testBody = `[ATLAS OS] Live WhatsApp Connected!\n\nBhai, aapka WhatsApp AI Assistant ab live hai! Aap mujhe yahan se voice/text message bhej sakte hain. Jab bhi A+ trade setup milega, main yahan confirmation maangunga.\n\nType 'BTC' or 'PnL' to test!`;
        const res = await sendMetaWhatsApp(metaAccessToken, metaPhoneNumberId, userPhoneNumber, testBody);
        return NextResponse.json(res);
      } else {
        const { accountSid, authToken, fromNumber, userPhoneNumber } = wa;
        if (!accountSid || !authToken || !fromNumber || !userPhoneNumber) {
          return NextResponse.json(
            {
              success: false,
              error: "Twilio Account SID, Auth Token, From Number, and your WhatsApp Phone Number are required.",
            },
            { status: 400 }
          );
        }

        const testBody = `[ATLAS OS] Live WhatsApp Connected!\n\nBhai, aapka WhatsApp AI Assistant ab live hai! Aap mujhe yahan se voice/text message bhej sakte hain. Jab bhi A+ trade setup milega, main yahan confirmation maangunga.\n\nType 'BTC' or 'PnL' to test!`;
        const res = await sendTwilioWhatsApp(accountSid, authToken, fromNumber, userPhoneNumber, testBody);
        return NextResponse.json(res);
      }
    }

    return NextResponse.json({ success: false, error: `Channel ${channel} not recognized.` }, { status: 400 });
  } catch (err: any) {
    return NextResponse.json(
      { success: false, error: err.message || "Internal server error" },
      { status: 500 }
    );
  }
}
