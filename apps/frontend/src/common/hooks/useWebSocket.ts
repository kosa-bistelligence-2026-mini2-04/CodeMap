import { useEffect, useRef, useState } from "react";
import type { WsEvent } from "@/common/types/contracts";

interface UseWebSocketOptions {
  url: string | null;
  onEvent: (event: WsEvent) => void;
  enabled: boolean;
  maxRetries?: number;
}

export interface UseWebSocketState {
  connected: boolean;
  retries: number;
  lastError?: string;
}

const BACKOFF_MS = [500, 1000, 2000, 4000, 8000] as const;

export function useWebSocket({
  url,
  onEvent,
  enabled,
  maxRetries = BACKOFF_MS.length,
}: UseWebSocketOptions): UseWebSocketState {
  const [state, setState] = useState<UseWebSocketState>({
    connected: false,
    retries: 0,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const timerRef = useRef<number | null>(null);
  const onEventRef = useRef(onEvent);

  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    if (!enabled || !url) {
      return;
    }

    let cancelled = false;

    const cleanupTimer = () => {
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };

    const connect = () => {
      if (cancelled) return;

      let ws: WebSocket;
      try {
        ws = new WebSocket(url);
      } catch (err) {
        setState((s) => ({
          ...s,
          connected: false,
          lastError: err instanceof Error ? err.message : "ws_construct_failed",
        }));
        scheduleReconnect();
        return;
      }

      wsRef.current = ws;

      ws.onopen = () => {
        if (cancelled) return;
        retryRef.current = 0;
        setState({ connected: true, retries: 0 });
      };

      ws.onmessage = (ev) => {
        if (cancelled) return;
        try {
          const data = JSON.parse(ev.data) as WsEvent;
          onEventRef.current(data);
        } catch (err) {
          console.warn("[ws] invalid payload", err);
        }
      };

      ws.onerror = () => {
        if (cancelled) return;
        setState((s) => ({ ...s, lastError: "connection_error" }));
      };

      ws.onclose = (ev) => {
        if (cancelled) return;
        setState((s) => ({ ...s, connected: false }));
        if (ev.code === 1000) return;
        scheduleReconnect();
      };
    };

    const scheduleReconnect = () => {
      if (cancelled) return;
      if (retryRef.current >= maxRetries) return;
      const delay = BACKOFF_MS[Math.min(retryRef.current, BACKOFF_MS.length - 1)];
      retryRef.current += 1;
      setState((s) => ({ ...s, retries: retryRef.current }));
      timerRef.current = window.setTimeout(connect, delay);
    };

    connect();

    return () => {
      cancelled = true;
      cleanupTimer();
      const ws = wsRef.current;
      if (ws && ws.readyState <= WebSocket.OPEN) {
        ws.close(1000, "unmount");
      }
      wsRef.current = null;
      retryRef.current = 0;
    };
  }, [url, enabled, maxRetries]);

  return state;
}
