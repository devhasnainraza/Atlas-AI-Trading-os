import { NextRequest, NextResponse } from "next/server";
import { runGroqAgentDeliberation } from "../../../../lib/groqClient";
import { getSessionUser } from "../../../../lib/server/session";
import { getDatabase } from "../../../../lib/server/db";
import { decryptVaultSecret } from "../../../../lib/server/cryptoVault";

/**
 * POST /api/agent/deliberate
 * ─────────────────────────────────────────────────────────────
 * Runs the 24/7 Multi-Agent Deliberation Pipeline powered by
 * user's personal Groq LPU key (stored encrypted in user's vault).
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { symbol = "BTC/USDT", price = 67240.0, rsi, atr, cvdRatio, trend, prompt } = body;

    let userApiKey: string | undefined = undefined;
    const user = getSessionUser(req);

    if (user) {
      const db = getDatabase();
      const stmt = db.prepare(`
        SELECT encrypted_payload, iv, auth_tag
        FROM user_credentials
        WHERE user_id = ? AND provider = 'groq' AND status = 'ACTIVE'
        LIMIT 1
      `);
      const cred = stmt.get(user.id) as any;

      if (cred) {
        userApiKey = decryptVaultSecret({
          encryptedData: cred.encrypted_payload,
          iv: cred.iv,
          authTag: cred.auth_tag,
        });
      } else if (!process.env.GROQ_API_KEY) {
        return NextResponse.json({
          success: false,
          error: "Please enter your Groq API Key in the Vault tab to run 24/7 AI multi-agent deliberation.",
        }, { status: 400 });
      }
    }

    const result = await runGroqAgentDeliberation({
      symbol,
      price: parseFloat(price) || 67240.0,
      rsi: rsi ? parseFloat(rsi) : undefined,
      atr: atr ? parseFloat(atr) : undefined,
      cvdRatio: cvdRatio ? parseFloat(cvdRatio) : undefined,
      trend,
      userPrompt: prompt,
      apiKey: userApiKey,
    });

    return NextResponse.json({
      success: true,
      provider: "groq",
      model: process.env.GROQ_MODEL || "llama-3.3-70b-versatile",
      deliberation: result,
    });
  } catch (err: any) {
    return NextResponse.json(
      { success: false, error: err.message || "Failed to run agent deliberation" },
      { status: 500 }
    );
  }
}
