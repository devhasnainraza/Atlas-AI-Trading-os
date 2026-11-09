"use client";

import React, { useState, useEffect, useCallback } from "react";
import { atlasAgent, AgentState, AgentActivity } from "../lib/agentLoop";
import { soundManager } from "../lib/soundEffects";
import { dispatchChannelAlert } from "../lib/channelService";
import {
  SearchIcon,
  PlayIcon,
  PauseIcon,
  ZapIcon,
  ShieldIcon,
  CheckIcon,
  CloseIcon,
  SettingsIcon,
  TargetIcon,
  SendIcon,
  ActivityIcon,
  AlertTriangleIcon,
  FileTextIcon,
  ClockIcon,
} from "./Icons";

interface AgentControlPanelProps {
  balance?: number;
  equity?: number;
  positions?: any[];
  riskStatus?: "NORMAL" | "ALERT" | "HALTED";
  onExecuteTrade?: (symbol: string, side: "BUY" | "SELL", entryPrice: number, tpPrice: number, slPrice: number) => void;
  onOpenSettings?: () => void;
}

export function AgentControlPanel({
  balance = 100000,
  equity = 100000,
  positions = [],
  riskStatus = "NORMAL",
  onExecuteTrade,
  onOpenSettings,
}: AgentControlPanelProps) {
  const [agentState, setAgentState] = useState<AgentState | null>(null);
  const [pendingTrade, setPendingTrade] = useState<any>(null);
  const [pendingTimeLeft, setPendingTimeLeft] = useState(0);
  const [isApproving, setIsApproving] = useState(false);
  const [lastExecResult, setLastExecResult] = useState<string | null>(null);

  useEffect(() => {
    const unsub = atlasAgent.onStateChange((state) => setAgentState(state));
    return unsub;
  }, []);

  // Poll pending trade from server
  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch("/api/agent/pending-trade");
        const data = await res.json();
        setPendingTrade(data.pending ? data.trade : null);
        setPendingTimeLeft(data.timeLeftSeconds ?? 0);
      } catch {}
    };
    check();
    const t = setInterval(check, 10000);
    return () => clearInterval(t);
  }, []);

  const handleToggleAgent = useCallback(() => {
    soundManager.playClick();
    if (atlasAgent.isRunning()) {
      atlasAgent.stop();
    } else {
      atlasAgent.start();
    }
  }, []);

  const handleForceScan = useCallback(async () => {
    soundManager.playClick();
    await atlasAgent.forceScanning();
  }, []);

  const handleApproveFromUI = async (approved: boolean) => {
    setIsApproving(true);
    soundManager.playClick();
    try {
      const res = await fetch("/api/broker/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userApproved: approved }),
      });
      const data = await res.json();
      if (approved && data.result?.success && onExecuteTrade && pendingTrade) {
        onExecuteTrade(pendingTrade.symbol, pendingTrade.side, pendingTrade.entryPrice, pendingTrade.tpPrice, pendingTrade.slPrice);
        soundManager.playExecutionSuccess();
      }
      setLastExecResult(approved ? (data.result?.success ? "FILLED" : "FAILED") : "CANCELLED");
      setPendingTrade(null);
      setTimeout(() => setLastExecResult(null), 5000);
    } catch (err: any) {
      setLastExecResult("ERROR");
    }
    setIsApproving(false);
  };

  const isRunning = agentState?.status === "RUNNING" || agentState?.status === "ANALYZING" || agentState?.status === "DISPATCHING";

  const statusColor = (s?: string) => {
    if (s === "RUNNING") return "#22c55e";
    if (s === "ANALYZING" || s === "DISPATCHING") return "#f59e0b";
    if (s === "PAUSED" || s === "IDLE") return "#64748b";
    return "#64748b";
  };

  const actIcon = (t: AgentActivity["type"]) => {
    if (t === "SIGNAL") return <TargetIcon size={12} color="var(--accent-blue)" />;
    if (t === "DISPATCH") return <SendIcon size={12} color="var(--accent-green)" />;
    if (t === "BROADCAST") return <ActivityIcon size={12} color="var(--accent-cyan)" />;
    if (t === "SCAN") return <SearchIcon size={12} color="var(--accent-amber)" />;
    if (t === "ERROR") return <AlertTriangleIcon size={12} color="var(--accent-red)" />;
    return <ZapIcon size={12} color="var(--text-muted)" />;
  };

  const fmtSec = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return m > 0 ? `${m}m ${sec}s` : `${sec}s`;
  };

  return (
    <div className="panel" style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      {/* Header */}
      <div className="panel-header" style={{ flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span className={isRunning ? "live-dot-green" : "live-dot-amber"} />
          <span style={{ color: "var(--text-primary)", fontWeight: 700 }}>ATLAS AUTONOMOUS AGENT</span>
          <span style={{ fontSize: "9px", padding: "1px 5px", borderRadius: "3px", background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", color: statusColor(agentState?.status), fontFamily: "var(--font-mono)" }}>
            {agentState?.status ?? "IDLE"}
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <button
            onClick={handleForceScan}
            disabled={!isRunning}
            className="btn-sober"
            style={{
              padding: "2px 8px",
              fontSize: "10px",
              height: "22px",
              display: "inline-flex",
              alignItems: "center",
              gap: "4px",
            }}
            title="Force Scan Now"
          >
            <SearchIcon size={10} color="var(--text-secondary)" />
            <span>Scan Now</span>
          </button>
          <button
            onClick={handleToggleAgent}
            className="btn-sober"
            style={{
              padding: "2px 10px",
              fontSize: "10px",
              height: "22px",
              display: "inline-flex",
              alignItems: "center",
              gap: "4px",
              background: isRunning ? "var(--accent-red-subtle)" : "rgba(34,197,94,0.1)",
              color: isRunning ? "var(--accent-red)" : "var(--accent-green)",
              borderColor: isRunning ? "var(--accent-red-border)" : "rgba(34,197,94,0.3)",
              fontWeight: 700,
            }}
          >
            {isRunning ? (
              <>
                <PauseIcon size={10} color="var(--accent-red)" />
                <span>Pause</span>
              </>
            ) : (
              <>
                <PlayIcon size={10} color="var(--accent-green)" />
                <span>Start</span>
              </>
            )}
          </button>
        </div>
      </div>

      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* Stats Strip */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", borderBottom: "1px solid var(--border-subtle)", flexShrink: 0 }}>
          {[
            { label: "SCANS", value: agentState?.scanCount ?? 0 },
            { label: "SIGNALS", value: agentState?.signalsGenerated ?? 0 },
            { label: "DISPATCHED", value: agentState?.tradesDispatched ?? 0 },
            { label: "NEXT SCAN", value: agentState?.nextScanIn != null && isRunning ? fmtSec(agentState.nextScanIn) : "—" },
          ].map((s) => (
            <div key={s.label} style={{ padding: "6px 10px", borderRight: "1px solid var(--border-subtle)", textAlign: "center" }}>
              <div style={{ fontSize: "9px", color: "var(--text-muted)", fontWeight: 700, letterSpacing: "0.04em" }}>{s.label}</div>
              <div className="tabular-nums" style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)", marginTop: "1px" }}>{s.value}</div>
            </div>
          ))}
        </div>

        {/* Last Signal */}
        {agentState?.lastSignal && (
          <div style={{ padding: "6px 12px", borderBottom: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", gap: "10px", flexShrink: 0 }}>
            <span style={{ fontSize: "9.5px", color: "var(--text-muted)", fontWeight: 700 }}>LAST SIGNAL:</span>
            <span style={{ fontSize: "11px", fontWeight: 700, color: agentState.lastSignal.side === "BUY" ? "var(--accent-green)" : "var(--accent-red)" }}>
              {agentState.lastSignal.symbol} {agentState.lastSignal.side}
            </span>
            <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>·</span>
            <span className="tabular-nums" style={{ fontSize: "10px", color: "var(--accent-blue)", fontWeight: 600 }}>
              {agentState.lastSignal.conviction}% conviction
            </span>
          </div>
        )}

        {/* Pending Trade Approval Card */}
        {pendingTrade && (
          <div style={{
            margin: "8px",
            padding: "10px 12px",
            background: "rgba(59,130,246,0.07)",
            border: "1px solid rgba(59,130,246,0.3)",
            borderRadius: "6px",
            flexShrink: 0,
          }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <ZapIcon size={12} color="#f59e0b" />
                <span style={{ fontSize: "10px", fontWeight: 800, color: "#f59e0b", letterSpacing: "0.05em" }}>TRADE PROPOSAL — AWAITING APPROVAL</span>
              </div>
              <span className="tabular-nums" style={{ fontSize: "9px", color: "var(--text-muted)" }}>
                Expires: {fmtSec(pendingTimeLeft)}
              </span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "8px", marginBottom: "10px" }}>
              <div>
                <div style={{ fontSize: "9px", color: "var(--text-muted)", fontWeight: 700 }}>SYMBOL / SIDE</div>
                <div style={{ fontSize: "13px", fontWeight: 800, color: pendingTrade.side === "BUY" ? "var(--accent-green)" : "var(--accent-red)" }}>
                  {pendingTrade.symbol} {pendingTrade.side}
                </div>
              </div>
              <div>
                <div style={{ fontSize: "9px", color: "var(--text-muted)", fontWeight: 700 }}>ENTRY PRICE</div>
                <div className="tabular-nums" style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)" }}>
                  ${pendingTrade.entryPrice?.toLocaleString()}
                </div>
              </div>
              <div>
                <div style={{ fontSize: "9px", color: "var(--text-muted)", fontWeight: 700 }}>CONVICTION</div>
                <div className="tabular-nums" style={{ fontSize: "13px", fontWeight: 700, color: "var(--accent-blue)" }}>
                  {pendingTrade.conviction}%
                </div>
              </div>
              <div>
                <div style={{ fontSize: "9px", color: "var(--text-muted)", fontWeight: 700 }}>TAKE PROFIT</div>
                <div className="tabular-nums" style={{ fontSize: "11px", fontWeight: 700, color: "var(--accent-green)" }}>
                  ${pendingTrade.tpPrice?.toLocaleString()}
                </div>
              </div>
              <div>
                <div style={{ fontSize: "9px", color: "var(--text-muted)", fontWeight: 700 }}>STOP LOSS</div>
                <div className="tabular-nums" style={{ fontSize: "11px", fontWeight: 700, color: "var(--accent-red)" }}>
                  ${pendingTrade.slPrice?.toLocaleString()}
                </div>
              </div>
              <div>
                <div style={{ fontSize: "9px", color: "var(--text-muted)", fontWeight: 700 }}>MODE</div>
                <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--accent-amber)", display: "flex", alignItems: "center", gap: "4px" }}>
                  <ShieldIcon size={11} color="var(--accent-amber)" />
                  <span>PAPER</span>
                </div>
              </div>
            </div>

            <div style={{ display: "flex", gap: "8px" }}>
              <button
                onClick={() => handleApproveFromUI(true)}
                disabled={isApproving}
                style={{
                  flex: 1,
                  padding: "8px",
                  background: "rgba(34,197,94,0.15)",
                  border: "1px solid rgba(34,197,94,0.4)",
                  color: "#22c55e",
                  borderRadius: "5px",
                  fontWeight: 800,
                  fontSize: "12px",
                  cursor: "pointer",
                  transition: "all 0.1s ease",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "6px",
                }}
              >
                <CheckIcon size={13} color="#22c55e" strokeWidth={2.5} />
                <span>{isApproving ? "Executing..." : "YES — EXECUTE TRADE"}</span>
              </button>
              <button
                onClick={() => handleApproveFromUI(false)}
                disabled={isApproving}
                style={{
                  flex: 1,
                  padding: "8px",
                  background: "rgba(239,68,68,0.1)",
                  border: "1px solid rgba(239,68,68,0.3)",
                  color: "var(--accent-red)",
                  borderRadius: "5px",
                  fontWeight: 800,
                  fontSize: "12px",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "6px",
                }}
              >
                <CloseIcon size={13} color="var(--accent-red)" strokeWidth={2.5} />
                <span>NO — CANCEL</span>
              </button>
            </div>

            <p style={{ margin: "6px 0 0", fontSize: "9.5px", color: "var(--text-muted)", textAlign: "center" }}>
              You can also reply <strong>YES</strong> or <strong>NO</strong> directly on WhatsApp
            </p>
          </div>
        )}

        {/* Execution Result Flash */}
        {lastExecResult && !pendingTrade && (
          <div style={{
            margin: "0 8px 8px",
            padding: "8px 12px",
            background: lastExecResult === "FILLED" ? "rgba(34,197,94,0.1)" : lastExecResult === "CANCELLED" ? "rgba(100,116,139,0.1)" : "rgba(239,68,68,0.1)",
            border: `1px solid ${lastExecResult === "FILLED" ? "rgba(34,197,94,0.3)" : lastExecResult === "CANCELLED" ? "var(--border-medium)" : "rgba(239,68,68,0.3)"}`,
            borderRadius: "5px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "6px",
            flexShrink: 0,
          }}>
            {lastExecResult === "FILLED" && <CheckIcon size={13} color="var(--accent-green)" />}
            {lastExecResult === "CANCELLED" && <ShieldIcon size={13} color="var(--text-secondary)" />}
            {lastExecResult === "ERROR" && <AlertTriangleIcon size={13} color="var(--accent-red)" />}
            <span style={{ fontSize: "11px", fontWeight: 700, color: lastExecResult === "FILLED" ? "var(--accent-green)" : lastExecResult === "CANCELLED" ? "var(--text-secondary)" : "var(--accent-red)" }}>
              {lastExecResult === "FILLED" ? "Paper Trade Filled! Check Portfolio Telemetry." : lastExecResult === "CANCELLED" ? "Trade cancelled. Capital preserved." : "Execution failed. Check broker config."}
            </span>
          </div>
        )}

        {/* Activity Feed */}
        <div style={{ flex: 1, overflowY: "auto", padding: "4px 0" }}>
          {!agentState || agentState.activities.length === 0 ? (
            <div style={{ padding: "20px", textAlign: "center", color: "var(--text-muted)", fontSize: "11px", display: "flex", alignItems: "center", justifyContent: "center", gap: "6px" }}>
              {isRunning ? (
                <>
                  <ClockIcon size={12} color="var(--accent-amber)" />
                  <span>First scan in progress...</span>
                </>
              ) : (
                <>
                  <PlayIcon size={12} color="var(--text-muted)" />
                  <span>Click Start to begin autonomous market scanning</span>
                </>
              )}
            </div>
          ) : (
            agentState.activities.map((act) => (
              <div key={act.id} style={{ padding: "4px 12px", borderBottom: "1px solid var(--border-subtle)", display: "flex", gap: "8px", alignItems: "flex-start" }}>
                <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: "16px", height: "16px", flexShrink: 0, marginTop: "2px" }}>
                  {actIcon(act.type)}
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: "10.5px", color: act.type === "SIGNAL" ? "var(--accent-blue)" : act.type === "ERROR" ? "var(--accent-red)" : act.type === "DISPATCH" ? "var(--accent-green)" : "var(--text-secondary)", lineHeight: 1.4 }}>
                    {act.message}
                  </div>
                </div>
                <span className="tabular-nums" style={{ fontSize: "9px", color: "var(--text-muted)", flexShrink: 0, paddingTop: "1px" }}>{act.timestamp}</span>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div style={{ padding: "6px 12px", borderTop: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
          <span style={{ fontSize: "9.5px", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "5px" }}>
            <FileTextIcon size={11} color="var(--text-muted)" />
            <span>Paper Mode · WhatsApp: YES/NO</span>
          </span>
          <button
            onClick={onOpenSettings}
            className="btn-sober"
            style={{ padding: "2px 8px", fontSize: "9.5px", height: "20px", display: "inline-flex", alignItems: "center", gap: "4px" }}
          >
            <SettingsIcon size={11} />
            <span>Channel Settings</span>
          </button>
        </div>
      </div>
    </div>
  );
}
