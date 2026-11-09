/**
 * Real mathematical technical analysis engine for live Binance OHLCV candle data.
 * Computes authentic RSI, EMA (20/50/200), MACD (12/26/9), Bollinger Bands (20, 2),
 * ATR (14), Fair Value Gaps (SMC), and Cumulative Volume Delta (CVD).
 */

export interface KlineData {
  openTime: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  closeTime: number;
  quoteVolume: number;
  trades: number;
  takerBuyBaseVolume: number;
  takerBuyQuoteVolume: number;
}

export interface RealMarketAnalysis {
  lastPrice: number;
  priceChangePct: number;
  rsi: number;
  rsiStatus: "OVERBOUGHT" | "OVERSOLD" | "BULLISH" | "BEARISH" | "NEUTRAL";
  ema20: number;
  ema50: number;
  ema200: number;
  trend: "STRONG_BULLISH" | "BULLISH" | "BEARISH" | "STRONG_BEARISH" | "RANGING";
  macd: {
    macd: number;
    signal: number;
    histogram: number;
    cross: "BULLISH_CROSS" | "BEARISH_CROSS" | "NEUTRAL";
  };
  bollinger: {
    upper: number;
    middle: number;
    lower: number;
    bandwidthPct: number;
  };
  atr: number;
  recommendedSl: number;
  recommendedTp: number;
  fvg: {
    detected: boolean;
    type: "BULLISH_FVG" | "BEARISH_FVG" | "NONE";
    top: number;
    bottom: number;
  };
  cvd: {
    totalVolume: number;
    takerBuyVolume: number;
    takerSellVolume: number;
    buyRatioPct: number;
    absorption: "STRONG_BUY_ABSORPTION" | "STRONG_SELL_ABSORPTION" | "BALANCED";
  };
  confidenceScore: number;
  consensusSignal: "STRONG_BUY" | "BUY" | "NEUTRAL" | "SELL" | "STRONG_SELL";
}

export function parseBinanceKlines(raw: (string | number)[][]): KlineData[] {
  return raw.map((k) => ({
    openTime: Number(k[0]),
    open: parseFloat(String(k[1])),
    high: parseFloat(String(k[2])),
    low: parseFloat(String(k[3])),
    close: parseFloat(String(k[4])),
    volume: parseFloat(String(k[5])),
    closeTime: Number(k[6]),
    quoteVolume: parseFloat(String(k[7])),
    trades: Number(k[8]),
    takerBuyBaseVolume: parseFloat(String(k[9])),
    takerBuyQuoteVolume: parseFloat(String(k[10])),
  }));
}

export function calculateEMA(values: number[], period: number): number[] {
  if (values.length < period) return values;
  const k = 2 / (period + 1);
  const emaArray: number[] = [];

  // Start with simple moving average for the first period
  let sum = 0;
  for (let i = 0; i < period; i++) {
    sum += values[i]!;
  }
  let prevEma = sum / period;
  emaArray.push(prevEma);

  for (let i = period; i < values.length; i++) {
    const currentEma = values[i]! * k + prevEma * (1 - k);
    emaArray.push(currentEma);
    prevEma = currentEma;
  }

  return emaArray;
}

export function calculateRSI(closes: number[], period: number = 14): number {
  if (closes.length <= period) return 50;

  let gains = 0;
  let losses = 0;

  for (let i = 1; i <= period; i++) {
    const diff = closes[i]! - closes[i - 1]!;
    if (diff >= 0) gains += diff;
    else losses += Math.abs(diff);
  }

  let avgGain = gains / period;
  let avgLoss = losses / period;

  for (let i = period + 1; i < closes.length; i++) {
    const diff = closes[i]! - closes[i - 1]!;
    if (diff >= 0) {
      avgGain = (avgGain * (period - 1) + diff) / period;
      avgLoss = (avgLoss * (period - 1)) / period;
    } else {
      avgGain = (avgGain * (period - 1)) / period;
      avgLoss = (avgLoss * (period - 1) + Math.abs(diff)) / period;
    }
  }

  if (avgLoss === 0) return 100;
  const rs = avgGain / avgLoss;
  return parseFloat((100 - 100 / (1 + rs)).toFixed(2));
}

export function calculateMACD(closes: number[]): { macd: number; signal: number; histogram: number } {
  if (closes.length < 26) return { macd: 0, signal: 0, histogram: 0 };

  const ema12 = calculateEMA(closes, 12);
  const ema26 = calculateEMA(closes, 26);

  // Align length of ema12 with ema26
  const offset = ema12.length - ema26.length;
  const macdLine: number[] = [];
  for (let i = 0; i < ema26.length; i++) {
    macdLine.push(ema12[i + offset]! - ema26[i]!);
  }

  const signalLine = calculateEMA(macdLine, 9);
  const latestMacd = macdLine[macdLine.length - 1] || 0;
  const latestSignal = signalLine[signalLine.length - 1] || 0;
  const histogram = latestMacd - latestSignal;

  return {
    macd: parseFloat(latestMacd.toFixed(4)),
    signal: parseFloat(latestSignal.toFixed(4)),
    histogram: parseFloat(histogram.toFixed(4)),
  };
}

export function calculateBollingerBands(
  closes: number[],
  period: number = 20,
  multiplier: number = 2
): { upper: number; middle: number; lower: number; bandwidthPct: number } {
  if (closes.length < period) {
    const last = closes[closes.length - 1] || 0;
    return { upper: last, middle: last, lower: last, bandwidthPct: 0 };
  }

  const slice = closes.slice(-period);
  const mean = slice.reduce((a, b) => a + b, 0) / period;
  const variance = slice.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / period;
  const stdDev = Math.sqrt(variance);

  const upper = mean + multiplier * stdDev;
  const lower = mean - multiplier * stdDev;
  const bandwidthPct = mean > 0 ? ((upper - lower) / mean) * 100 : 0;

  return {
    upper: parseFloat(upper.toFixed(2)),
    middle: parseFloat(mean.toFixed(2)),
    lower: parseFloat(lower.toFixed(2)),
    bandwidthPct: parseFloat(bandwidthPct.toFixed(2)),
  };
}

export function calculateATR(candles: KlineData[], period: number = 14): number {
  if (candles.length < 2) return 0;

  const trs: number[] = [];
  for (let i = 1; i < candles.length; i++) {
    const high = candles[i]!.high;
    const low = candles[i]!.low;
    const prevClose = candles[i - 1]!.close;

    const tr = Math.max(high - low, Math.abs(high - prevClose), Math.abs(low - prevClose));
    trs.push(tr);
  }

  const atrSlice = trs.slice(-period);
  const atr = atrSlice.reduce((a, b) => a + b, 0) / atrSlice.length;
  return parseFloat(atr.toFixed(4));
}

export function detectFairValueGap(candles: KlineData[]): {
  detected: boolean;
  type: "BULLISH_FVG" | "BEARISH_FVG" | "NONE";
  top: number;
  bottom: number;
} {
  if (candles.length < 3) return { detected: false, type: "NONE", top: 0, bottom: 0 };

  // Check the last 3 closed candles
  const c1 = candles[candles.length - 3]!;
  const c2 = candles[candles.length - 2]!;
  const c3 = candles[candles.length - 1]!;

  // Bullish FVG: Candle 1 high < Candle 3 low
  if (c3.low > c1.high) {
    return {
      detected: true,
      type: "BULLISH_FVG",
      top: c3.low,
      bottom: c1.high,
    };
  }

  // Bearish FVG: Candle 1 low > Candle 3 high
  if (c1.low > c3.high) {
    return {
      detected: true,
      type: "BEARISH_FVG",
      top: c1.low,
      bottom: c3.high,
    };
  }

  return { detected: false, type: "NONE", top: 0, bottom: 0 };
}

export function analyzeRealMarketData(rawKlines: (string | number)[][]): RealMarketAnalysis {
  const candles = parseBinanceKlines(rawKlines);
  const closes = candles.map((c) => c.close);
  const lastPrice = closes[closes.length - 1] || 1;
  const firstPrice = closes[0] || lastPrice;
  const priceChangePct = parseFloat((((lastPrice - firstPrice) / firstPrice) * 100).toFixed(2));

  // 1. RSI
  const rsi = calculateRSI(closes, 14);
  let rsiStatus: RealMarketAnalysis["rsiStatus"] = "NEUTRAL";
  if (rsi >= 70) rsiStatus = "OVERBOUGHT";
  else if (rsi <= 30) rsiStatus = "OVERSOLD";
  else if (rsi > 55) rsiStatus = "BULLISH";
  else if (rsi < 45) rsiStatus = "BEARISH";

  // 2. EMAs
  const ema20Arr = calculateEMA(closes, 20);
  const ema50Arr = calculateEMA(closes, 50);
  const ema200Arr = calculateEMA(closes, Math.min(200, closes.length));

  const ema20 = ema20Arr[ema20Arr.length - 1] || lastPrice;
  const ema50 = ema50Arr[ema50Arr.length - 1] || lastPrice;
  const ema200 = ema200Arr[ema200Arr.length - 1] || lastPrice;

  let trend: RealMarketAnalysis["trend"] = "RANGING";
  if (lastPrice > ema20 && ema20 > ema50 && ema50 > ema200) trend = "STRONG_BULLISH";
  else if (lastPrice > ema20 && ema20 > ema50) trend = "BULLISH";
  else if (lastPrice < ema20 && ema20 < ema50 && ema50 < ema200) trend = "STRONG_BEARISH";
  else if (lastPrice < ema20 && ema20 < ema50) trend = "BEARISH";

  // 3. MACD
  const macdData = calculateMACD(closes);
  let macdCross: RealMarketAnalysis["macd"]["cross"] = "NEUTRAL";
  if (macdData.histogram > 0 && macdData.macd > macdData.signal) macdCross = "BULLISH_CROSS";
  else if (macdData.histogram < 0 && macdData.macd < macdData.signal) macdCross = "BEARISH_CROSS";

  // 4. Bollinger Bands
  const bollinger = calculateBollingerBands(closes, 20, 2);

  // 5. ATR and Risk recommendations
  const atr = calculateATR(candles, 14);
  const recommendedSl = parseFloat(Math.max(0.0001, lastPrice - 1.5 * atr).toFixed(lastPrice < 1 ? 4 : 2));
  const recommendedTp = parseFloat((lastPrice + 3.0 * atr).toFixed(lastPrice < 1 ? 4 : 2));

  // 6. Fair Value Gap (SMC)
  const fvg = detectFairValueGap(candles);

  // 7. Cumulative Volume Delta (CVD)
  const totalVolume = candles.reduce((acc, c) => acc + c.volume, 0);
  const takerBuyVolume = candles.reduce((acc, c) => acc + c.takerBuyBaseVolume, 0);
  const takerSellVolume = totalVolume - takerBuyVolume;
  const buyRatioPct = totalVolume > 0 ? parseFloat(((takerBuyVolume / totalVolume) * 100).toFixed(1)) : 50;

  let absorption: RealMarketAnalysis["cvd"]["absorption"] = "BALANCED";
  if (buyRatioPct >= 55) absorption = "STRONG_BUY_ABSORPTION";
  else if (buyRatioPct <= 45) absorption = "STRONG_SELL_ABSORPTION";

  // Synthesize authentic consensus confidence score
  let score = 50;
  if (trend === "STRONG_BULLISH") score += 20;
  else if (trend === "BULLISH") score += 12;
  else if (trend === "BEARISH") score -= 12;
  else if (trend === "STRONG_BEARISH") score -= 20;

  if (rsiStatus === "BULLISH") score += 10;
  else if (rsiStatus === "BEARISH") score -= 10;
  else if (rsiStatus === "OVERSOLD") score += 15; // Mean-reversion long bounce setup
  else if (rsiStatus === "OVERBOUGHT") score -= 15;

  if (macdCross === "BULLISH_CROSS") score += 10;
  else if (macdCross === "BEARISH_CROSS") score -= 10;

  if (absorption === "STRONG_BUY_ABSORPTION") score += 10;
  else if (absorption === "STRONG_SELL_ABSORPTION") score -= 10;

  if (fvg.type === "BULLISH_FVG") score += 8;
  else if (fvg.type === "BEARISH_FVG") score -= 8;

  const confidenceScore = Math.max(10, Math.min(98, score));

  let consensusSignal: RealMarketAnalysis["consensusSignal"] = "NEUTRAL";
  if (confidenceScore >= 80) consensusSignal = "STRONG_BUY";
  else if (confidenceScore >= 62) consensusSignal = "BUY";
  else if (confidenceScore <= 25) consensusSignal = "STRONG_SELL";
  else if (confidenceScore <= 40) consensusSignal = "SELL";

  return {
    lastPrice,
    priceChangePct,
    rsi,
    rsiStatus,
    ema20: parseFloat(ema20.toFixed(2)),
    ema50: parseFloat(ema50.toFixed(2)),
    ema200: parseFloat(ema200.toFixed(2)),
    trend,
    macd: {
      ...macdData,
      cross: macdCross,
    },
    bollinger,
    atr,
    recommendedSl,
    recommendedTp,
    fvg,
    cvd: {
      totalVolume: parseFloat(totalVolume.toFixed(2)),
      takerBuyVolume: parseFloat(takerBuyVolume.toFixed(2)),
      takerSellVolume: parseFloat(takerSellVolume.toFixed(2)),
      buyRatioPct,
      absorption,
    },
    confidenceScore,
    consensusSignal,
  };
}
