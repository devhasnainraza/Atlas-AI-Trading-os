/**
 * Atlas Broker Service
 * ─────────────────────────────────────────────────────────────────────────────
 * Supports Binance Paper Trading (default, no real money) and Real API mode.
 * All real API calls are HMAC-SHA256 signed per Binance specification.
 *
 * Paper Trading mode is active unless BINANCE_API_KEY is configured.
 */

export interface BrokerConfig {
  apiKey?: string;
  apiSecret?: string;
  testnet?: boolean; // true = use testnet.binance.vision
}

export interface OrderResult {
  success: boolean;
  mode: "PAPER" | "TESTNET" | "LIVE";
  orderId: string;
  symbol: string;
  side: "BUY" | "SELL";
  price: number;
  quantity: number;
  status: string;
  filledAt: number; // unix ms
  message: string;
  rawResponse?: any;
}

export interface AccountBalance {
  totalUsdt: number;
  availableUsdt: number;
  mode: "PAPER" | "TESTNET" | "LIVE";
}

// ─── HMAC-SHA256 signature (Web Crypto API — works in Next.js edge/node) ─────
async function signQuery(secret: string, queryString: string): Promise<string> {
  const encoder = new TextEncoder();
  const keyData = encoder.encode(secret);
  const msgData = encoder.encode(queryString);
  const key = await crypto.subtle.importKey(
    "raw", keyData,
    { name: "HMAC", hash: "SHA-256" },
    false, ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, msgData);
  return Array.from(new Uint8Array(sig))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

// ─── Paper Trading (no real API) ─────────────────────────────────────────────
function paperTradeFill(
  symbol: string,
  side: "BUY" | "SELL",
  sizeUsd: number,
  currentPrice: number
): OrderResult {
  const quantity = parseFloat((sizeUsd / currentPrice).toFixed(6));
  const slippage = side === "BUY" ? 1.0002 : 0.9998;
  const fillPrice = parseFloat((currentPrice * slippage).toFixed(2));

  return {
    success: true,
    mode: "PAPER",
    orderId: `PAPER-${Date.now()}`,
    symbol,
    side,
    price: fillPrice,
    quantity,
    status: "FILLED",
    filledAt: Date.now(),
    message: `Paper trade filled: ${side} ${quantity} ${symbol} @ $${fillPrice} (simulated, no real money moved)`,
  };
}

// ─── Binance Real / Testnet Market Order ──────────────────────────────────────
async function binanceMarketOrder(
  config: BrokerConfig,
  symbol: string,
  side: "BUY" | "SELL",
  quoteOrderQty: number // USDT amount
): Promise<OrderResult> {
  const baseUrl = config.testnet
    ? "https://testnet.binance.vision"
    : "https://api.binance.com";

  const timestamp = Date.now();
  const params = `symbol=${symbol}&side=${side}&type=MARKET&quoteOrderQty=${quoteOrderQty}&timestamp=${timestamp}`;
  const signature = await signQuery(config.apiSecret!, params);
  const url = `${baseUrl}/api/v3/order?${params}&signature=${signature}`;

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "X-MBX-APIKEY": config.apiKey!,
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });
    const data = await res.json();

    if (!res.ok) {
      return {
        success: false,
        mode: config.testnet ? "TESTNET" : "LIVE",
        orderId: "",
        symbol,
        side,
        price: 0,
        quantity: 0,
        status: "REJECTED",
        filledAt: Date.now(),
        message: `Binance error (${data.code}): ${data.msg}`,
        rawResponse: data,
      };
    }

    const fills = data.fills ?? [];
    const avgPrice = fills.length > 0
      ? fills.reduce((sum: number, f: any) => sum + parseFloat(f.price) * parseFloat(f.qty), 0) /
        fills.reduce((sum: number, f: any) => sum + parseFloat(f.qty), 0)
      : parseFloat(data.price ?? "0");

    return {
      success: true,
      mode: config.testnet ? "TESTNET" : "LIVE",
      orderId: String(data.orderId),
      symbol,
      side,
      price: parseFloat(avgPrice.toFixed(2)),
      quantity: parseFloat(data.executedQty ?? "0"),
      status: data.status,
      filledAt: data.transactTime ?? Date.now(),
      message: `Order ${data.status}: ${side} ${data.executedQty} ${symbol} @ avg $${avgPrice.toFixed(2)}`,
      rawResponse: data,
    };
  } catch (err: any) {
    return {
      success: false,
      mode: config.testnet ? "TESTNET" : "LIVE",
      orderId: "",
      symbol,
      side,
      price: 0,
      quantity: 0,
      status: "ERROR",
      filledAt: Date.now(),
      message: err.message ?? "Network error calling Binance API",
    };
  }
}

// ─── Public API ───────────────────────────────────────────────────────────────

/**
 * Execute a trade. Falls back to paper trading if no API key configured.
 */
export async function executeTrade(
  config: BrokerConfig | undefined,
  brokerSymbol: string,
  side: "BUY" | "SELL",
  sizeUsd: number,
  currentPrice: number
): Promise<OrderResult> {
  // Paper trading if no API key
  if (!config?.apiKey || !config?.apiSecret) {
    return paperTradeFill(brokerSymbol, side, sizeUsd, currentPrice);
  }
  return binanceMarketOrder(config, brokerSymbol, side, sizeUsd);
}

/**
 * Get Binance account USDT balance (or return paper balance).
 */
export async function getBrokerBalance(
  config: BrokerConfig | undefined,
  paperBalance = 100000
): Promise<AccountBalance> {
  if (!config?.apiKey || !config?.apiSecret) {
    return { totalUsdt: paperBalance, availableUsdt: paperBalance, mode: "PAPER" };
  }

  const baseUrl = config.testnet
    ? "https://testnet.binance.vision"
    : "https://api.binance.com";
  const timestamp = Date.now();
  const params = `timestamp=${timestamp}`;
  const signature = await signQuery(config.apiSecret, params);

  try {
    const res = await fetch(`${baseUrl}/api/v3/account?${params}&signature=${signature}`, {
      headers: { "X-MBX-APIKEY": config.apiKey },
    });
    const data = await res.json();
    const usdt = data.balances?.find((b: any) => b.asset === "USDT");
    const total = parseFloat(usdt?.free ?? "0") + parseFloat(usdt?.locked ?? "0");
    return {
      totalUsdt: total,
      availableUsdt: parseFloat(usdt?.free ?? "0"),
      mode: config.testnet ? "TESTNET" : "LIVE",
    };
  } catch {
    return { totalUsdt: 0, availableUsdt: 0, mode: "LIVE" };
  }
}
