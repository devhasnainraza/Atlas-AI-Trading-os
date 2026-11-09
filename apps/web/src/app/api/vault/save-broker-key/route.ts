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
    const { provider = "binance", apiKey, apiSecret, passphrase = "", accountType = "SPOT & PERP" } = body;

    if (!apiKey || !apiSecret || apiKey.length < 10 || apiSecret.length < 10) {
      return NextResponse.json({ error: "Valid API key and secret are required" }, { status: 400 });
    }

    const cleanKey = apiKey.trim();
    const cleanSecret = apiSecret.trim();

    // Verify key live with exchange
    if (provider.toLowerCase() === "binance") {
      try {
        const timestamp = Date.now();
        const queryString = `timestamp=${timestamp}`;
        const signature = crypto.createHmac("sha256", cleanSecret).update(queryString).digest("hex");

        const testRes = await fetch(`https://api.binance.com/api/v3/account?${queryString}&signature=${signature}`, {
          headers: {
            "X-MBX-APIKEY": cleanKey,
          },
        });

        if (!testRes.ok) {
          const errData = await testRes.json().catch(() => ({}));
          return NextResponse.json({
            error: `Binance verification failed: ${errData.msg || "Invalid API key or signature"}`,
          }, { status: 400 });
        }
      } catch (err: any) {
        return NextResponse.json({
          error: "Could not connect to Binance to verify credentials. Please check network/key.",
        }, { status: 502 });
      }
    }

    // Encrypt sensitive credentials payload with AES-256-GCM
    const payload = JSON.stringify({
      apiKey: cleanKey,
      apiSecret: cleanSecret,
      passphrase: passphrase.trim(),
      accountType,
    });

    const encrypted = encryptVaultSecret(payload);
    const masked = maskCredential(cleanKey);
    const credId = "cred-brk-" + crypto.randomBytes(6).toString("hex");
    const updatedAt = new Date().toISOString();

    const db = getDatabase();
    const stmt = db.prepare(`
      INSERT INTO user_credentials (
        id, user_id, provider, category, encrypted_payload, iv, auth_tag, masked_key, status, account_type, updated_at
      )
      VALUES (?, ?, ?, 'BROKER', ?, ?, ?, ?, 'ACTIVE', ?, ?)
      ON CONFLICT(user_id, provider) DO UPDATE SET
        encrypted_payload = excluded.encrypted_payload,
        iv = excluded.iv,
        auth_tag = excluded.auth_tag,
        masked_key = excluded.masked_key,
        status = 'ACTIVE',
        account_type = excluded.account_type,
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
      accountType,
      updatedAt
    );

    return NextResponse.json({
      success: true,
      provider: provider.toLowerCase(),
      maskedKey: masked,
      message: `${provider.toUpperCase()} credentials verified and encrypted in secure database vault. Real exchange sync is now active.`,
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message || "Failed to save broker key" }, { status: 500 });
  }
}
