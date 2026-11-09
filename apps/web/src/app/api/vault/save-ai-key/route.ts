import { NextRequest, NextResponse } from "next/server";
import crypto from "node:crypto";
import { getSessionUser } from "../../../../lib/server/session";
import { getDatabase } from "../../../../lib/server/db";
import { encryptVaultSecret, maskCredential } from "../../../../lib/server/cryptoVault";

export async function POST(req: NextRequest) {
  try {
    const user = getSessionUser(req);
    if (!user) {
      return NextResponse.json({ error: "Unauthorized. Please login first." }, { status: 401 });
    }

    const body = await req.json();
    const { provider = "groq", apiKey } = body;

    if (!apiKey || typeof apiKey !== "string" || apiKey.trim().length < 10) {
      return NextResponse.json({ error: "Valid API key is required" }, { status: 400 });
    }

    const cleanKey = apiKey.trim();

    // Verify key with provider
    if (provider === "groq") {
      try {
        const testRes = await fetch("https://api.groq.com/openai/v1/models", {
          headers: { Authorization: `Bearer ${cleanKey}` },
        });
        if (!testRes.ok) {
          const errData = await testRes.json().catch(() => ({}));
          return NextResponse.json({
            error: `Groq verification failed: ${errData.error?.message || "Invalid API key"}`,
          }, { status: 400 });
        }
      } catch (err: any) {
        return NextResponse.json({
          error: "Could not reach Groq API for verification. Check internet connection.",
        }, { status: 502 });
      }
    } else if (provider === "openai") {
      try {
        const testRes = await fetch("https://api.openai.com/v1/models", {
          headers: { Authorization: `Bearer ${cleanKey}` },
        });
        if (!testRes.ok) {
          return NextResponse.json({ error: "OpenAI verification failed: Invalid API key" }, { status: 400 });
        }
      } catch (err: any) {
        return NextResponse.json({ error: "Could not reach OpenAI API" }, { status: 502 });
      }
    }

    // Encrypt key with AES-256-GCM
    const encrypted = encryptVaultSecret(cleanKey);
    const masked = maskCredential(cleanKey);
    const credId = "cred-ai-" + crypto.randomBytes(6).toString("hex");
    const updatedAt = new Date().toISOString();

    const db = getDatabase();
    const stmt = db.prepare(`
      INSERT INTO user_credentials (
        id, user_id, provider, category, encrypted_payload, iv, auth_tag, masked_key, status, account_type, updated_at
      )
      VALUES (?, ?, ?, 'AI', ?, ?, ?, ?, 'ACTIVE', 'AI_ENGINE', ?)
      ON CONFLICT(user_id, provider) DO UPDATE SET
        encrypted_payload = excluded.encrypted_payload,
        iv = excluded.iv,
        auth_tag = excluded.auth_tag,
        masked_key = excluded.masked_key,
        status = 'ACTIVE',
        updated_at = excluded.updated_at
    `);

    stmt.run(
      credId,
      user.id,
      provider.toLowerCase(),
      encrypted.encryptedData,
      encrypted.iv,
      encrypted.authTag,
      masked,
      updatedAt
    );

    return NextResponse.json({
      success: true,
      provider: provider.toLowerCase(),
      maskedKey: masked,
      message: `${provider.toUpperCase()} API key verified and encrypted in secure database vault.`,
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message || "Failed to save AI key" }, { status: 500 });
  }
}
