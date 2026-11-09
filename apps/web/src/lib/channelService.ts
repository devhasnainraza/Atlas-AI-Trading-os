export interface ChannelConfig {
  // WhatsApp (Twilio or Meta Cloud API)
  whatsapp: {
    provider: "TWILIO" | "META_CLOUD";
    accountSid?: string;
    authToken?: string;
    fromNumber?: string; // e.g. "whatsapp:+14155238886"
    userPhoneNumber?: string; // e.g. "+923192004088"
    metaAccessToken?: string;
    metaPhoneNumberId?: string;
    metaBusinessAccountId?: string;
    isEnabled: boolean;
  };
  // Telegram Bot API
  telegram: {
    botToken?: string; // from @BotFather
    chatId?: string; // user's telegram chat ID
    isEnabled: boolean;
  };
  // Discord Webhook
  discord: {
    webhookUrl?: string;
    isEnabled: boolean;
  };
  // Twitter / X API
  twitter: {
    bearerToken?: string;
    isEnabled: boolean;
  };
}

export const DEFAULT_CHANNEL_CONFIG: ChannelConfig = {
  whatsapp: {
    provider: (typeof process !== "undefined" && process.env?.WHATSAPP_PROVIDER === "TWILIO") ? "TWILIO" : "META_CLOUD",
    accountSid: (typeof process !== "undefined" && process.env?.TWILIO_ACCOUNT_SID) || "",
    authToken: (typeof process !== "undefined" && process.env?.TWILIO_AUTH_TOKEN) || "",
    fromNumber: (typeof process !== "undefined" && process.env?.TWILIO_FROM_NUMBER) || "",
    userPhoneNumber: (typeof process !== "undefined" && (process.env?.NEXT_PUBLIC_WHATSAPP_PHONE || process.env?.WHATSAPP_USER_PHONE || process.env?.WHATSAPP_PHONE_NUMBER)) || "",
    metaAccessToken: (typeof process !== "undefined" && (process.env?.META_ACCESS_TOKEN || process.env?.META_WHATSAPP_TOKEN || process.env?.WHATSAPP_ACCESS_TOKEN)) || "",
    metaPhoneNumberId: (typeof process !== "undefined" && process.env?.META_PHONE_NUMBER_ID) || "",
    metaBusinessAccountId: (typeof process !== "undefined" && process.env?.META_BUSINESS_ACCOUNT_ID) || "",
    isEnabled: typeof process !== "undefined" && Boolean(process.env?.META_ACCESS_TOKEN || process.env?.TWILIO_ACCOUNT_SID),
  },
  telegram: {
    botToken: (typeof process !== "undefined" && process.env?.TELEGRAM_BOT_TOKEN) || "",
    chatId: (typeof process !== "undefined" && process.env?.TELEGRAM_CHAT_ID) || "",
    isEnabled: typeof process !== "undefined" && Boolean(process.env?.TELEGRAM_BOT_TOKEN),
  },
  discord: {
    webhookUrl: (typeof process !== "undefined" && process.env?.DISCORD_WEBHOOK_URL) || "",
    isEnabled: typeof process !== "undefined" && Boolean(process.env?.DISCORD_WEBHOOK_URL),
  },
  twitter: {
    bearerToken: (typeof process !== "undefined" && process.env?.TWITTER_BEARER_TOKEN) || "",
    isEnabled: typeof process !== "undefined" && Boolean(process.env?.TWITTER_BEARER_TOKEN),
  },
};

export interface ChannelDispatchResult {
  channel: "WHATSAPP" | "TELEGRAM" | "DISCORD" | "TWITTER";
  success: boolean;
  message: string;
  responsePayload?: any;
}

/**
 * Send real outbound trade alert or message to Telegram Bot
 */
export async function sendTelegramMessage(botToken: string, chatId: string, text: string, includeApprovalButtons = false): Promise<ChannelDispatchResult> {
  try {
    const url = `https://api.telegram.org/bot${botToken}/sendMessage`;
    const payload: any = {
      chat_id: chatId,
      text: text,
      parse_mode: "Markdown",
    };

    if (includeApprovalButtons) {
      payload.reply_markup = {
        inline_keyboard: [
          [
            { text: "[YES] EXECUTE TRADE", callback_data: "EXECUTE_TRADE_YES" },
            { text: "[NO] CANCEL", callback_data: "EXECUTE_TRADE_NO" },
          ],
        ],
      };
    }

    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok || !data.ok) {
      return {
        channel: "TELEGRAM",
        success: false,
        message: data.description || "Failed to dispatch to Telegram",
        responsePayload: data,
      };
    }

    return {
      channel: "TELEGRAM",
      success: true,
      message: "Successfully delivered to your Telegram chat!",
      responsePayload: data,
    };
  } catch (err: any) {
    return {
      channel: "TELEGRAM",
      success: false,
      message: err.message || "Network error connecting to Telegram API",
    };
  }
}

/**
 * Send real outbound alert to Discord Webhook
 */
export async function sendDiscordAlert(webhookUrl: string, title: string, content: string, color = 0x22c55e): Promise<ChannelDispatchResult> {
  try {
    const payload = {
      username: "Atlas Chief Manager Agent",
      avatar_url: "https://raw.githubusercontent.com/shadcn-ui/ui/main/apps/www/public/favicon.ico",
      embeds: [
        {
          title,
          description: content,
          color,
          timestamp: new Date().toISOString(),
          footer: {
            text: "Atlas AI Trading OS · Privacy Sanitization Guard Active",
          },
        },
      ],
    };

    const res = await fetch(webhookUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const text = await res.text();
      return {
        channel: "DISCORD",
        success: false,
        message: `Discord error (${res.status}): ${text}`,
      };
    }

    return {
      channel: "DISCORD",
      success: true,
      message: "Successfully posted alert to your Discord channel!",
    };
  } catch (err: any) {
    return {
      channel: "DISCORD",
      success: false,
      message: err.message || "Failed to reach Discord Webhook",
    };
  }
}

/**
 * Send real WhatsApp message via Twilio REST API
 */
export async function sendTwilioWhatsApp(
  accountSid: string,
  authToken: string,
  fromNumber: string,
  toNumber: string,
  body: string
): Promise<ChannelDispatchResult> {
  try {
    const url = `https://api.twilio.com/2010-04-01/Accounts/${accountSid}/Messages.json`;
    const formData = new URLSearchParams();
    formData.append("From", fromNumber.startsWith("whatsapp:") ? fromNumber : `whatsapp:${fromNumber}`);
    formData.append("To", toNumber.startsWith("whatsapp:") ? toNumber : `whatsapp:${toNumber}`);
    formData.append("Body", body);

    const authHeader = "Basic " + btoa(`${accountSid}:${authToken}`);
    const res = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: authHeader,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: formData.toString(),
    });

    const data = await res.json();
    if (!res.ok) {
      return {
        channel: "WHATSAPP",
        success: false,
        message: data.message || `Twilio error code: ${data.code}`,
        responsePayload: data,
      };
    }

    return {
      channel: "WHATSAPP",
      success: true,
      message: `Delivered to your WhatsApp phone number (${toNumber})!`,
      responsePayload: data,
    };
  } catch (err: any) {
    return {
      channel: "WHATSAPP",
      success: false,
      message: err.message || "Failed to dispatch WhatsApp message via Twilio",
    };
  }
}

/**
 * Send real WhatsApp message via Official Meta Cloud API (Graph API)
 */
export async function sendMetaWhatsApp(
  accessToken: string,
  phoneNumberId: string,
  toPhoneNumber: string,
  bodyText: string
): Promise<ChannelDispatchResult> {
  try {
    const cleanTo = toPhoneNumber.replace(/[^0-9]/g, "");
    const url = `https://graph.facebook.com/v21.0/${phoneNumberId}/messages`;

    // 1. Try sending custom interactive/text message first
    const textPayload = {
      messaging_product: "whatsapp",
      recipient_type: "individual",
      to: cleanTo,
      type: "text",
      text: {
        preview_url: false,
        body: bodyText,
      },
    };

    let res = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(textPayload),
    });

    let data = await res.json();

    // 2. If Meta rejects with 131047 (outside 24hr window requires template)
    if (!res.ok && data?.error?.code === 131047) {
      const templatePayload = {
        messaging_product: "whatsapp",
        to: cleanTo,
        type: "template",
        template: {
          name: "hello_world",
          language: { code: "en_US" },
        },
      };

      res = await fetch(url, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(templatePayload),
      });

      data = await res.json();
    }

    if (!res.ok || data.error) {
      const errMsg = data.error?.message || data.error?.error_user_msg || `Meta API Error (${res.status})`;
      return {
        channel: "WHATSAPP",
        success: false,
        message: `${errMsg} (Code: ${data.error?.code || res.status})`,
        responsePayload: data,
      };
    }

    return {
      channel: "WHATSAPP",
      success: true,
      message: `Delivered to your WhatsApp phone (+${cleanTo}) via Official Meta Cloud API! Msg ID: ${data.messages?.[0]?.id || "CONFIRMED"}`,
      responsePayload: data,
    };
  } catch (err: any) {
    return {
      channel: "WHATSAPP",
      success: false,
      message: err.message || "Network error communicating with Meta WhatsApp Cloud API",
    };
  }
}

/**
 * Universal client-side dispatcher: Sends real-time alerts to WhatsApp, Telegram & Discord
 */
export async function dispatchChannelAlert(
  title: string,
  message: string,
  category: "ALERT" | "TRADE_PROPOSAL" | "EXECUTION" | "RISK" = "ALERT"
): Promise<void> {
  try {
    let activeConfig: ChannelConfig | undefined = undefined;
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("atlas_channel_config");
      if (saved) {
        try {
          activeConfig = JSON.parse(saved);
        } catch {}
      }
    }

    await fetch("/api/channels/notify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title,
        message,
        category,
        config: activeConfig,
      }),
    });
  } catch (err) {
    console.warn("Outbound alert dispatch failed:", err);
  }
}


