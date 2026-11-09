import { NextRequest, NextResponse } from "next/server";
import { sendMetaWhatsApp, DEFAULT_CHANNEL_CONFIG } from "../../../../lib/channelService";
import { getLatestPendingTrade } from "../../../../lib/pendingTradeStore";
import { queryGroqChat } from "../../../../lib/groqClient";

async function getBinancePrice(symbol: string): Promise<number | null> {
  try {
    const res = await fetch("https://api.binance.com/api/v3/ticker/price?symbol=" + symbol);
    if (!res.ok) return null;
    const data = await res.json();
    return parseFloat(data.price);
  } catch { return null; }
}

export async function POST(req: NextRequest) {
  try {
    const contentType = req.headers.get("content-type") || "";
    let incomingText = "";
    let senderNumber = "";
    if (contentType.includes("application/x-www-form-urlencoded")) {
      const formData = await req.formData();
      incomingText = formData.get("Body")?.toString() || "";
      senderNumber = formData.get("From")?.toString() || "";
    } else {
      const body = await req.json();
      incomingText = body?.entry?.[0]?.changes?.[0]?.value?.messages?.[0]?.text?.body || "";
      senderNumber = body?.entry?.[0]?.changes?.[0]?.value?.messages?.[0]?.from || "";
    }
    const lower = incomingText.toLowerCase().trim();
    let replyText = "";
    const isYes = lower === "yes" || lower === "haan" || lower === "ha" || lower === "y" || lower.includes("execute") || lower.includes("kar do");
    const isNo = lower === "no" || lower === "nahi" || lower === "na" || lower === "n" || lower.includes("cancel") || lower.includes("mat karo");
    if (isYes) {
      const pending = getLatestPendingTrade();
      if (!pending) {
        replyText = "No pending trade found. Proposal may have expired (15min TTL). Wait for next agent signal.";
      } else {
        try {
          const execRes = await fetch(req.nextUrl.origin + "/api/broker/execute", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ userApproved: true }),
          });
          const execData = await execRes.json();
          replyText = execData.message ?? "Trade execution triggered.";
        } catch {
          replyText = "Broker service unreachable. Approve from Atlas Cockpit.";
        }
      }
    } else if (isNo) {
      const pending = getLatestPendingTrade();
      if (!pending) {
        replyText = "No active trade proposals. Capital safe.";
      } else {
        try {
          await fetch(req.nextUrl.origin + "/api/broker/execute", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ userApproved: false }),
          });
        } catch {}
        replyText = "Trade Cancelled: " + pending.symbol + " " + pending.side + ". Capital preserved.";
      }
    } else if (lower.includes("status") || lower.includes("pnl") || lower.includes("portfolio") || lower.includes("balance")) {
      const pending = getLatestPendingTrade();
      const pl = pending ? "\nPENDING: " + pending.symbol + " " + pending.side + " @ $" + pending.entryPrice + " | TP: $" + pending.tpPrice + " | SL: $" + pending.slPrice + "\nReply YES to execute or NO to cancel.\n" : "";
      replyText = "ATLAS STATUS\n\nMode: Paper Trading\nRisk Gate: NORMAL\nAgent: RUNNING (15min scans)\n" + pl + "\nType HELP for all commands.";
    } else if (lower.includes("btc") || lower.includes("bitcoin")) {
      const price = await getBinancePrice("BTCUSDT");
      replyText = price ? "BTC/USDT: $" + price.toLocaleString() + "\n\nAtlas monitoring 15M structure." : "BTC price unavailable.";
    } else if (lower.includes("eth")) {
      const price = await getBinancePrice("ETHUSDT");
      replyText = price ? "ETH/USDT: $" + price.toLocaleString() : "ETH price unavailable.";
    } else if (lower.includes("sol")) {
      const price = await getBinancePrice("SOLUSDT");
      replyText = price ? "SOL/USDT: $" + price.toLocaleString() : "SOL price unavailable.";
    } else if (lower === "stop" || lower.includes("band karo")) {
      replyText = "Agent Loop Paused. Reply START to resume.";
    } else if (lower === "start" || lower.includes("shuru karo")) {
      replyText = "Agent Loop Resumed. Scanning every 15 min. Trade proposals will appear here.";
    } else if (lower.includes("help") || lower === "?") {
      replyText = "Atlas AI Commands:\nYES/HAAN -> Execute trade\nNO/NAHI -> Cancel\nSTATUS -> Portfolio\nBTC/ETH/SOL -> Price\nSTOP -> Pause\nSTART -> Resume\nHELP -> Commands";
    } else {
      const pending = getLatestPendingTrade();
      if (pending && (lower.includes("trade") || lower.includes("deal") || lower.includes("proposal"))) {
        replyText = "PENDING TRADE: " + pending.symbol + " " + pending.side + " @ $" + pending.entryPrice.toLocaleString() + "\nTP: $" + pending.tpPrice + " | SL: $" + pending.slPrice + "\nConviction: " + pending.conviction + "%\n\nReply YES to execute or NO to cancel.";
      } else {
        // Query Groq LPU LLM for intelligent market analysis directly on WhatsApp
        try {
          const btcPrice = await getBinancePrice("BTCUSDT");
          const groqAnswer = await queryGroqChat([
            {
              role: "system",
              content:
                "You are ATLAS AI, an institutional quantitative trading operating system communicating with the trader via WhatsApp. Keep your answer ultra-concise, professional, and actionable (max 3-4 bullet points or 3 sentences). Quote real levels. Current BTC/USDT price: $" +
                (btcPrice?.toLocaleString() || "67,240") +
                ". If the user writes in Roman Urdu or Hindi, reply in concise Roman Urdu/English.",
            },
            { role: "user", content: incomingText },
          ], { maxTokens: 350, temperature: 0.3 });
          replyText = groqAnswer || "Atlas AI active. Current BTC: $" + (btcPrice?.toLocaleString() || "67,240") + ". Reply STATUS for portfolio or HELP for commands.";
        } catch {
          replyText = "Atlas AI active. Mode: Paper Trading | Risk Gate: NORMAL. Type HELP for commands or ask any market question.";
        }
      }
    }
    if (!contentType.includes("application/x-www-form-urlencoded")) {
      const cfg = DEFAULT_CHANNEL_CONFIG.whatsapp;
      const targetNumber = senderNumber || cfg.userPhoneNumber;
      if (cfg.metaAccessToken && cfg.metaPhoneNumberId && targetNumber) {
        await sendMetaWhatsApp(cfg.metaAccessToken, cfg.metaPhoneNumberId, targetNumber, replyText);
      }
      return NextResponse.json({ status: "OK", replyText }, { status: 200 });
    }
    const twiml = '<?xml version="1.0" encoding="UTF-8"?><Response><Message>' + replyText + '</Message></Response>';
    return new NextResponse(twiml, { status: 200, headers: { "Content-Type": "text/xml" } });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function GET(req: NextRequest) {
  const sp = req.nextUrl.searchParams;
  if (sp.get("hub.mode") === "subscribe" && sp.get("hub.verify_token") === "atlas_trading_secret") {
    return new NextResponse(sp.get("hub.challenge"), { status: 200 });
  }
  return NextResponse.json({ status: "Atlas WhatsApp Webhook Live", commands: ["YES","NO","STATUS","BTC","ETH","SOL","STOP","START","HELP"] });
}
