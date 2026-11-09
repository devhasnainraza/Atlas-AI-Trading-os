"use client";

import { useEffect, useState, useRef, useCallback } from "react";

export interface StreamQuote {
  venue_code: string;
  symbol: string;
  bid: number;
  ask: number;
  last: number;
  observed_at: string;
  age_seconds: number;
  freshness: "fresh" | "stale";
  session_state?: "open" | "closed" | "pre" | "halted" | "suspended";
}

export type StreamStatus = "connecting" | "connected" | "degraded" | "reconnecting" | "offline";

export function useMarketDataStream(connectionId: string, symbols: string[]) {
  const [quotes, setQuotes] = useState<Record<string, StreamQuote>>({});
  const [status, setStatus] = useState<StreamStatus>("connecting");
  const [lastHeartbeat, setLastHeartbeat] = useState<number>(Date.now());
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const retryCountRef = useRef<number>(0);

  const connect = useCallback(() => {
    if (!symbols || symbols.length === 0) return;

    setStatus("connecting");
    const symbolsParam = encodeURIComponent(symbols.join(","));
    const url = `/api/v1/market-data/stream?connection_id=${encodeURIComponent(connectionId)}&symbols=${symbolsParam}`;

    try {
      const es = new EventSource(url);
      eventSourceRef.current = es;

      es.onopen = () => {
        setStatus("connected");
        retryCountRef.current = 0;
        setLastHeartbeat(Date.now());
      };

      es.addEventListener("quote", (event) => {
        try {
          const data: StreamQuote = JSON.parse(event.data);
          setQuotes((prev) => ({
            ...prev,
            [data.symbol]: {
              ...data,
              age_seconds: 0.1,
              freshness: "fresh",
            },
          }));
          setLastHeartbeat(Date.now());
          setStatus("connected");
        } catch {
          // ignore malformed frame
        }
      });

      es.addEventListener("feed.degraded", () => {
        setStatus("degraded");
      });

      es.addEventListener("feed.recovered", () => {
        setStatus("connected");
      });

      es.onerror = () => {
        es.close();
        setStatus("reconnecting");
        const backoff = Math.min(1000 * 2 ** retryCountRef.current, 15000);
        retryCountRef.current += 1;
        reconnectTimeoutRef.current = setTimeout(connect, backoff);
      };
    } catch {
      setStatus("offline");
    }
  }, [connectionId, symbols]);

  useEffect(() => {
    connect();

    // Staleness watchdog timer: tick every second and increase age_seconds
    const interval = setInterval(() => {
      setQuotes((prev) => {
        let changed = false;
        const next: Record<string, StreamQuote> = {};
        for (const [sym, q] of Object.entries(prev)) {
          const newAge = q.age_seconds + 1.0;
          const isStale = newAge > 3.0; // Fail-closed > 3s
          if (isStale !== (q.freshness === "stale") || Math.floor(newAge) !== Math.floor(q.age_seconds)) {
            changed = true;
          }
          next[sym] = {
            ...q,
            age_seconds: Number(newAge.toFixed(1)),
            freshness: isStale ? "stale" : "fresh",
          };
        }
        return changed ? next : prev;
      });
    }, 1000);

    return () => {
      clearInterval(interval);
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [connect]);

  return { quotes, status, lastHeartbeat };
}
