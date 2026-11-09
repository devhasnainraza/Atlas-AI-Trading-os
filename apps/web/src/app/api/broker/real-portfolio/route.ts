import { NextRequest, NextResponse } from "next/server";
import crypto from "node:crypto";
import { getSessionUser } from "../../../../lib/server/session";
import { getDatabase } from "../../../../lib/server/db";
import { decryptVaultSecret } from "../../../../lib/server/cryptoVault";

export async function GET(req: NextRequest) {
  try {
    const user = getSessionUser(req);
    if (!user) {
      return NextResponse.json({
        connected: false,
        totalBalanceUsd: 0,
        equityUsd: 0,
        positions: [],
        openOrders: [],
        message: "Please log in to view your real portfolio.",
      }, { status: 200 });
    }

    const db = getDatabase();
    const stmt = db.prepare(`
      SELECT provider, encrypted_payload, iv, auth_tag, masked_key, account_type
      FROM user_credentials
      WHERE user_id = ? AND category = 'BROKER' AND status = 'ACTIVE'
      LIMIT 1
    `);

    const brokerCred = stmt.get(user.id) as any;
    if (!brokerCred) {
      return NextResponse.json({
        connected: false,
        provider: null,
        totalBalanceUsd: 0,
        equityUsd: 0,
        positions: [],
        openOrders: [],
        message: "No broker connected. Please enter your Binance or Bybit API key in the Vault tab to load your real portfolio.",
      });
    }

    // Decrypt credentials in-memory only
    const decryptedJson = decryptVaultSecret({
      encryptedData: brokerCred.encrypted_payload,
      iv: brokerCred.iv,
      authTag: brokerCred.auth_tag,
    });

    const { apiKey, apiSecret } = JSON.parse(decryptedJson);

    if (brokerCred.provider === "binance") {
      const timestamp = Date.now();
      const queryString = `timestamp=${timestamp}`;
      const signature = crypto.createHmac("sha256", apiSecret).update(queryString).digest("hex");

      // 1. Fetch real account balances
      const accountRes = await fetch(`https://api.binance.com/api/v3/account?${queryString}&signature=${signature}`, {
        headers: { "X-MBX-APIKEY": apiKey },
      });

      if (!accountRes.ok) {
        return NextResponse.json({
          connected: false,
          error: "Failed to authenticate with Binance using saved keys. Verify API key permissions.",
          totalBalanceUsd: 0,
          positions: [],
          openOrders: [],
        });
      }

      const accountData = await accountRes.json();
      const nonZeroBalances = (accountData.balances || []).filter((b: any) => {
        const free = parseFloat(b.free);
        const locked = parseFloat(b.locked);
        return free > 0.0000001 || locked > 0.0000001;
      });

      // 2. Fetch prices to calculate USD total
      let totalUsd = 0;
      const positions: any[] = [];

      try {
        const pricesRes = await fetch("https://api.binance.com/api/v3/ticker/price");
        const pricesData = await pricesRes.json();
        const priceMap = new Map<string, number>();
        for (const item of pricesData) {
          priceMap.set(item.symbol, parseFloat(item.price));
        }

        for (const b of nonZeroBalances) {
          const totalUnits = parseFloat(b.free) + parseFloat(b.locked);
          let usdVal = 0;
          let currentPrice = 1;

          if (b.asset === "USDT" || b.asset === "USDC" || b.asset === "BUSD") {
            usdVal = totalUnits;
            currentPrice = 1;
          } else {
            const pair = `${b.asset}USDT`;
            currentPrice = priceMap.get(pair) || 0;
            usdVal = totalUnits * currentPrice;
          }

          if (usdVal > 0.5) { // Only track assets worth > $0.50
            totalUsd += usdVal;
            positions.push({
              id: `pos-${b.asset.toLowerCase()}`,
              symbol: b.asset === "USDT" ? "USDT" : `${b.asset}/USDT`,
              side: "LONG",
              sizeStr: `${totalUnits.toFixed(4)} ${b.asset}`,
              entryPrice: currentPrice,
              currentPrice,
              pnlUsd: 0.0,
              pnlPct: 0.0,
              tpPrice: parseFloat((currentPrice * 1.05).toFixed(2)),
              slPrice: parseFloat((currentPrice * 0.95).toFixed(2)),
              breakEven: false,
              trailingStop: false,
            });
          }
        }
      } catch {
        // Fallback if price fetch fails
        totalUsd = nonZeroBalances.reduce((sum: number, b: any) => sum + (parseFloat(b.free) || 0), 0);
      }

      // 3. Fetch real open orders
      const ordersRes = await fetch(`https://api.binance.com/api/v3/openOrders?${queryString}&signature=${signature}`, {
        headers: { "X-MBX-APIKEY": apiKey },
      });

      const openOrders = ordersRes.ok ? await ordersRes.json() : [];

      return NextResponse.json({
        connected: true,
        provider: "Binance",
        maskedKey: brokerCred.masked_key,
        totalBalanceUsd: parseFloat(totalUsd.toFixed(2)),
        equityUsd: parseFloat(totalUsd.toFixed(2)),
        positions,
        openOrders: openOrders.map((o: any) => ({
          id: String(o.orderId),
          symbol: o.symbol,
          side: o.side,
          price: parseFloat(o.price),
          sizeStr: `${o.origQty} ${o.symbol}`,
          status: o.status,
          type: o.type,
          time: new Date(o.time).toLocaleTimeString(),
        })),
        message: "Real Binance portfolio and open orders synced successfully.",
      });
    }

    // Default response for other brokers
    return NextResponse.json({
      connected: true,
      provider: brokerCred.provider,
      maskedKey: brokerCred.masked_key,
      totalBalanceUsd: 0,
      positions: [],
      openOrders: [],
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message || "Failed to sync real portfolio" }, { status: 500 });
  }
}
