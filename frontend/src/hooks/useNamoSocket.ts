import { useCallback, useEffect, useRef, useState } from "react";

const HEARTBEAT_MS = 30_000;
const MAX_BACKOFF_MS = 30_000;

export type NamoStatus = "idle" | "connecting" | "connected" | "disconnected" | "error";

export interface NamoData {
  emotion?: {
    current: string;
    intensity: number;
    visual_signal: string;
  };
  classroom?: {
    active_students: number;
    noise_level: number;
    engagement_score: number;
  };
  reasoning?: {
    thinking: boolean;
    step?: string;
  };
  transcript?: {
    text: string;
    is_final: boolean;
    speaker: "user" | "namo";
  };
  ts: number;
}

export function useNamoSocket(wsUrl: string | null) {
  const [data, setData] = useState<NamoData | null>(null);
  const [status, setStatus] = useState<NamoStatus>("idle");

  const wsRef = useRef<WebSocket | null>(null);
  const backoffRef = useRef(1000);
  const heartbeatRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);
  const intentRef = useRef(false);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const connectRef = useRef<() => void>(() => {});

  const stopHeartbeat = useCallback(() => {
    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current);
      heartbeatRef.current = null;
    }
  }, []);

  const startHeartbeat = useCallback((ws: WebSocket) => {
    stopHeartbeat();
    heartbeatRef.current = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send("ping");
      }
    }, HEARTBEAT_MS);
  }, [stopHeartbeat]);

  const clearReconnect = useCallback(() => {
    if (reconnectRef.current) {
      clearTimeout(reconnectRef.current);
      reconnectRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;
    if (!wsUrl) {
      setStatus("error");
      return;
    }
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;

    intentRef.current = true;
    clearReconnect();
    setStatus("connecting");

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        backoffRef.current = 1000;
        setStatus("connected");
        startHeartbeat(ws);
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        if (event.data === "pong") return;
        try {
          const parsed = JSON.parse(event.data);
          setData(parsed);
        } catch { /* ignore non-json messages */ }
      };

      ws.onerror = () => {
        if (!mountedRef.current) return;
        setStatus("error");
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        stopHeartbeat();

        if (intentRef.current) {
          setStatus("disconnected");
          const delay = backoffRef.current;
          backoffRef.current = Math.min(backoffRef.current * 2, MAX_BACKOFF_MS);
          
          reconnectRef.current = setTimeout(() => {
            connectRef.current();
          }, delay);
        } else {
          setStatus("idle");
        }
      };
    } catch (err) {
      setStatus("error");
      console.error("WS Connection Error:", err);
    }
  }, [wsUrl, startHeartbeat, stopHeartbeat, clearReconnect]);

  // Keep connectRef up to date
  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  const disconnect = useCallback(() => {
    intentRef.current = false;
    clearReconnect();
    stopHeartbeat();
    if (wsRef.current) {
      wsRef.current.onclose = () => {
        if (mountedRef.current) setStatus("idle");
      };
      wsRef.current.close();
      wsRef.current = null;
    } else {
      setStatus("idle");
    }
  }, [clearReconnect, stopHeartbeat]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      intentRef.current = false;
      clearReconnect();
      stopHeartbeat();
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
  }, [clearReconnect, stopHeartbeat]);

  return { data, status, connect, disconnect };
}
