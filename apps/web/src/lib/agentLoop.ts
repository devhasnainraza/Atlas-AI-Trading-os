/**
 * Atlas Autonomous Agent Loop
 * ──────────────────────────────────────────────────────────────
 * 24/7 client-side autonomous trading agent.
 * Runs setInterval scans, generates signals, stores pending trades,
 * dispatches proposals to WhatsApp and broadcasts hourly reports.
 *
 * Usage:
 *   const loop = new AgentLoop({ scanIntervalMs: 15 * 60 * 1000 });
 *   loop.start();
 *   loop.stop();
 */

export interface AgentLoopConfig {
  scanIntervalMs?: number;      // default 15 min
  broadcastIntervalMs?: number; // default 60 min
  minConviction?: number;       // 0-100, default 75
  riskPctPerTrade?: number;     // default 1.0%
  enableWhatsApp?: boolean;
  enableDiscord?: boolean;
}

export interface AgentActivity {
  id: string;
  timestamp: string;
  type: "SCAN" | "SIGNAL" | "DISPATCH" | "BROADCAST" | "ERROR" | "INFO";
  message: string;
  symbol?: string;
  conviction?: number;
}

export interface AgentState {
  status: "IDLE" | "RUNNING" | "ANALYZING" | "DISPATCHING" | "PAUSED";
  lastScan: string | null;
  nextScanIn: number; // seconds
  scanCount: number;
  signalsGenerated: number;
  tradesDispatched: number;
  lastSignal: { symbol: string; side: string; conviction: number } | null;
  activities: AgentActivity[];
}

type StateListener = (state: AgentState) => void;

export class AgentLoop {
  private config: Required<AgentLoopConfig>;
  private scanTimer: ReturnType<typeof setInterval> | null = null;
  private broadcastTimer: ReturnType<typeof setInterval> | null = null;
  private countdownTimer: ReturnType<typeof setInterval> | null = null;
  private listeners: StateListener[] = [];
  private state: AgentState;
  private nextScanAt = 0;

  constructor(config: AgentLoopConfig = {}) {
    this.config = {
      scanIntervalMs: config.scanIntervalMs ?? 15 * 60 * 1000,
      broadcastIntervalMs: config.broadcastIntervalMs ?? 60 * 60 * 1000,
      minConviction: config.minConviction ?? 75,
      riskPctPerTrade: config.riskPctPerTrade ?? 1.0,
      enableWhatsApp: config.enableWhatsApp ?? true,
      enableDiscord: config.enableDiscord ?? false,
    };
    this.state = {
      status: "IDLE",
      lastScan: null,
      nextScanIn: Math.round(this.config.scanIntervalMs / 1000),
      scanCount: 0,
      signalsGenerated: 0,
      tradesDispatched: 0,
      lastSignal: null,
      activities: [],
    };
  }

  /** Subscribe to state updates */
  onStateChange(listener: StateListener): () => void {
    this.listeners.push(listener);
    listener(this.state);
    return () => { this.listeners = this.listeners.filter((l) => l !== listener); };
  }

  private emit() {
    const s = { ...this.state, activities: [...this.state.activities] };
    this.listeners.forEach((l) => l(s));
  }

  private addActivity(type: AgentActivity["type"], message: string, extra: Partial<AgentActivity> = {}) {
    const now = new Date();
    const ts = now.toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
    const act: AgentActivity = { id: Date.now().toString(), timestamp: ts, type, message, ...extra };
    // Keep max 50 activities
    this.state.activities = [act, ...this.state.activities].slice(0, 50);
  }

  /** Start the agent loop */
  start() {
    if (this.state.status === "RUNNING") return;
    this.state.status = "RUNNING";
    this.addActivity("INFO", "Atlas Autonomous Agent Loop started. Scanning every " + Math.round(this.config.scanIntervalMs / 60000) + " minutes.");
    this.emit();

    // Run first scan immediately
    this.runScan();

    // Set recurring scan interval
    this.scanTimer = setInterval(() => this.runScan(), this.config.scanIntervalMs);

    // Hourly broadcast
    this.broadcastTimer = setInterval(() => this.runBroadcast(), this.config.broadcastIntervalMs);

    // Countdown ticker (every second)
    this.nextScanAt = Date.now() + this.config.scanIntervalMs;
    this.countdownTimer = setInterval(() => {
      const remaining = Math.max(0, Math.round((this.nextScanAt - Date.now()) / 1000));
      this.state.nextScanIn = remaining;
      this.emit();
    }, 1000);
  }

  /** Stop the agent loop */
  stop() {
    if (this.scanTimer) { clearInterval(this.scanTimer); this.scanTimer = null; }
    if (this.broadcastTimer) { clearInterval(this.broadcastTimer); this.broadcastTimer = null; }
    if (this.countdownTimer) { clearInterval(this.countdownTimer); this.countdownTimer = null; }
    this.state.status = "PAUSED";
    this.addActivity("INFO", "Agent loop paused by user.");
    this.emit();
  }

  isRunning() { return this.state.status === "RUNNING" || this.state.status === "ANALYZING"; }

  /** Force an immediate scan */
  async forceScanning() {
    this.nextScanAt = Date.now() + this.config.scanIntervalMs;
    await this.runScan();
  }

  // ─── Internal: Market Scan ────────────────────────────────────────────────
  private async runScan() {
    if (this.state.status === "PAUSED") return;
    this.state.status = "ANALYZING";
    this.state.scanCount += 1;
    const now = new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit" });
    this.state.lastScan = now;
    this.addActivity("SCAN", "Market scan #" + this.state.scanCount + " started...");
    this.emit();

    const watchlist = ["BTC/USDT", "ETH/USDT", "SOL/USDT"];

    let bestSignal: { symbol: string; side: "BUY" | "SELL"; conviction: number; entryPrice: number; tpPrice: number; slPrice: number; brokerSymbol: string } | null = null;

    for (const symbol of watchlist) {
      try {
        const binanceSymbol = symbol.replace("/", "");
        const klinesRes = await fetch(
          "https://api.binance.com/api/v3/klines?symbol=" + binanceSymbol + "&interval=15m&limit=50"
        );
        if (!klinesRes.ok) continue;
        const klines = await klinesRes.json();

        // Simple signal generation from klines
        const closes = klines.map((k: any) => parseFloat(k[4]));
        const volumes = klines.map((k: any) => parseFloat(k[5]));

        if (closes.length < 20) continue;

        const last = closes[closes.length - 1];
        const prev20 = closes.slice(-20);
        const ema20 = prev20.reduce((a: number, b: number) => a + b, 0) / 20;
        const lastVol = volumes[volumes.length - 1];
        const avgVol = volumes.slice(-10).reduce((a: number, b: number) => a + b, 0) / 10;

        // RSI (14)
        const rsiPeriod = 14;
        let gains = 0, losses = 0;
        for (let i = closes.length - rsiPeriod; i < closes.length; i++) {
          const diff = closes[i] - closes[i - 1];
          if (diff > 0) gains += diff;
          else losses += Math.abs(diff);
        }
        const rs = gains / (losses || 0.001);
        const rsi = 100 - 100 / (1 + rs);

        // Conviction scoring
        let conviction = 50;
        let side: "BUY" | "SELL" = "BUY";

        if (last > ema20 && rsi > 50 && rsi < 70 && lastVol > avgVol * 1.2) {
          conviction = Math.min(95, 60 + (rsi - 50) * 0.8 + (lastVol / avgVol - 1) * 10);
          side = "BUY";
        } else if (last < ema20 && rsi < 50 && rsi > 30 && lastVol > avgVol * 1.1) {
          conviction = Math.min(95, 60 + (50 - rsi) * 0.8 + (lastVol / avgVol - 1) * 10);
          side = "SELL";
        }

        if (conviction >= this.config.minConviction) {
          const tp = side === "BUY" ? last * 1.035 : last * 0.965;
          const sl = side === "BUY" ? last * 0.982 : last * 1.018;
          if (!bestSignal || conviction > bestSignal.conviction) {
            bestSignal = {
              symbol, side, conviction: Math.round(conviction),
              entryPrice: parseFloat(last.toFixed(2)),
              tpPrice: parseFloat(tp.toFixed(2)),
              slPrice: parseFloat(sl.toFixed(2)),
              brokerSymbol: binanceSymbol,
            };
          }
        }
      } catch {
        // Skip this symbol
      }
    }

    if (bestSignal) {
      this.state.signalsGenerated += 1;
      this.state.lastSignal = { symbol: bestSignal.symbol, side: bestSignal.side, conviction: bestSignal.conviction };
      this.addActivity("SIGNAL", bestSignal.symbol + " " + bestSignal.side + " — Conviction " + bestSignal.conviction + "%", { symbol: bestSignal.symbol, conviction: bestSignal.conviction });
      this.emit();
      await this.dispatchTradeProposal(bestSignal);
    } else {
      this.addActivity("SCAN", "No high-conviction signals found. Market neutral — skipping dispatch.");
    }

    this.state.status = "RUNNING";
    this.nextScanAt = Date.now() + this.config.scanIntervalMs;
    this.emit();
  }

  // ─── Internal: Dispatch Trade Proposal ────────────────────────────────────
  private async dispatchTradeProposal(signal: NonNullable<{ symbol: string; side: "BUY" | "SELL"; conviction: number; entryPrice: number; tpPrice: number; slPrice: number; brokerSymbol: string }>) {
    this.state.status = "DISPATCHING";
    this.emit();
    try {
      // Store pending trade server-side
      await fetch("/api/agent/pending-trade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol: signal.symbol,
          side: signal.side,
          entryPrice: signal.entryPrice,
          tpPrice: signal.tpPrice,
          slPrice: signal.slPrice,
          sizeUsd: 1000,
          riskPct: this.config.riskPctPerTrade,
          conviction: signal.conviction,
          source: "AGENT_LOOP",
          brokerSymbol: signal.brokerSymbol,
          note: "Auto-generated by Atlas Agent Loop",
        }),
      });

      // Dispatch via WhatsApp
      const msg =
        "ATLAS AGENT SIGNAL\n\n" +
        signal.symbol + " " + signal.side + "\n\n" +
        "Entry: $" + signal.entryPrice.toLocaleString() + "\n" +
        "TP: $" + signal.tpPrice + " (+" + (((signal.tpPrice - signal.entryPrice) / signal.entryPrice) * 100).toFixed(2) + "%)\n" +
        "SL: $" + signal.slPrice + " (-" + (((signal.entryPrice - signal.slPrice) / signal.entryPrice) * 100).toFixed(2) + "%)\n" +
        "Conviction: " + signal.conviction + "%\n" +
        "Risk: 1% (,000)\n\n" +
        "Reply YES to execute or NO to skip.\n" +
        "(Proposal expires in 15 min)";

      await fetch("/api/channels/notify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: "AGENT SIGNAL: " + signal.symbol + " " + signal.side,
          message: msg,
          category: "TRADE_PROPOSAL",
        }),
      });

      this.state.tradesDispatched += 1;
      this.addActivity("DISPATCH", "Proposal dispatched to WhatsApp: " + signal.symbol + " " + signal.side + " @ $" + signal.entryPrice, { symbol: signal.symbol });
    } catch (err: any) {
      this.addActivity("ERROR", "Dispatch failed: " + (err.message ?? "Unknown error"));
    }
    this.emit();
  }

  // ─── Internal: Hourly Manager Broadcast ──────────────────────────────────
  private async runBroadcast() {
    if (this.state.status === "PAUSED") return;
    try {
      await fetch("/api/agent/broadcast", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          balance: 100000,
          equity: 100000,
          dailyPnl: 0,
          dailyPnlPct: 0,
          positionCount: 0,
          positions: [],
          riskStatus: "NORMAL",
          nextScanMin: Math.round(this.config.scanIntervalMs / 60000),
        }),
      });
      this.addActivity("BROADCAST", "Hourly Manager Report dispatched to channels.");
    } catch {
      this.addActivity("ERROR", "Hourly broadcast failed.");
    }
    this.emit();
  }

  getState(): AgentState { return { ...this.state, activities: [...this.state.activities] }; }
}

// Singleton instance for the app
export const atlasAgent = new AgentLoop({
  scanIntervalMs: 15 * 60 * 1000,
  broadcastIntervalMs: 60 * 60 * 1000,
  minConviction: 75,
  riskPctPerTrade: 1.0,
  enableWhatsApp: true,
});
