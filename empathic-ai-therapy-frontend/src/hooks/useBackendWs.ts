"use client";

import { useCallback, useEffect, useRef } from "react";
import type { WsEnvelope, KgDiffPayload, ServerErrorPayload } from "@/lib/types";

const WS_BASE = process.env.NEXT_PUBLIC_WS_BASE ?? "ws://localhost:8000";
const PING_INTERVAL_MS = 30_000;

interface UseBackendWsOptions {
  sessionId: string | null;
  onKgDiff: (diff: KgDiffPayload) => void;
  onError: (err: ServerErrorPayload) => void;
}

export function useBackendWs({ sessionId, onKgDiff, onError }: UseBackendWsOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const pingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const onKgDiffRef = useRef(onKgDiff);
  const onErrorRef = useRef(onError);

  // Keep callbacks stable without causing reconnects
  useEffect(() => { onKgDiffRef.current = onKgDiff; }, [onKgDiff]);
  useEffect(() => { onErrorRef.current = onError; }, [onError]);

  const sendEnvelope = useCallback((envelope: Omit<WsEnvelope, "sent_at_ms">) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ ...envelope, sent_at_ms: Date.now() }));
    }
  }, []);

  const sendMessage = useCallback(
    (type: string, payload: Record<string, unknown>, correlationId?: string) => {
      if (!sessionId) return;
      sendEnvelope({
        type,
        session_id: sessionId,
        payload,
        correlation_id: correlationId ?? `corr_${crypto.randomUUID().replace(/-/g, "")}`,
      });
    },
    [sessionId, sendEnvelope]
  );

  // Connect when sessionId is set
  useEffect(() => {
    if (!sessionId) return;

    const ws = new WebSocket(`${WS_BASE}/ws/session/${sessionId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      // Initial ping
      ws.send(
        JSON.stringify({
          type: "client.ping",
          session_id: sessionId,
          payload: {},
          sent_at_ms: Date.now(),
          correlation_id: `corr_${crypto.randomUUID().replace(/-/g, "")}`,
        })
      );

      // Periodic ping
      pingTimerRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(
            JSON.stringify({
              type: "client.ping",
              session_id: sessionId,
              payload: {},
              sent_at_ms: Date.now(),
              correlation_id: `corr_${crypto.randomUUID().replace(/-/g, "")}`,
            })
          );
        }
      }, PING_INTERVAL_MS);
    };

    ws.onmessage = (event) => {
      let envelope: WsEnvelope;
      try {
        envelope = JSON.parse(event.data as string) as WsEnvelope;
      } catch {
        return;
      }

      switch (envelope.type) {
        case "kg.diff":
          onKgDiffRef.current(envelope.payload as unknown as KgDiffPayload);
          break;
        case "server.error":
          onErrorRef.current(envelope.payload as unknown as ServerErrorPayload);
          break;
        // server.pong and kg.tool_calls_applied are silently ignored
      }
    };

    ws.onerror = () => {
      onErrorRef.current({
        code: "ws_error",
        message: "Backend WebSocket connection error.",
        correlation_id: null,
        retryable: false,
        details: {},
      });
    };

    return () => {
      if (pingTimerRef.current) clearInterval(pingTimerRef.current);
      pingTimerRef.current = null;
      ws.close();
      wsRef.current = null;
    };
  }, [sessionId]);

  const disconnect = useCallback(() => {
    if (pingTimerRef.current) clearInterval(pingTimerRef.current);
    pingTimerRef.current = null;
    wsRef.current?.close();
    wsRef.current = null;
  }, []);

  return { sendMessage, disconnect };
}
