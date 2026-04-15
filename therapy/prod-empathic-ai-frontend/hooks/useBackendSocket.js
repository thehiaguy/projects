"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

function normalizeBaseUrl(baseUrl) {
  if (baseUrl) {
    return baseUrl.replace(/\/+$/, "");
  }

  if (typeof window === "undefined") {
    return "";
  }

  return `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}`;
}

function normalizeWsBaseUrl(baseUrl) {
  return normalizeBaseUrl(baseUrl)
    .replace(/^http:/i, "ws:")
    .replace(/^https:/i, "wss:");
}

function buildSessionSocketUrl(baseUrl, sessionId, sessionToken) {
  const normalizedBaseUrl = normalizeWsBaseUrl(baseUrl);
  const encodedSessionId = encodeURIComponent(sessionId);
  const searchParams = new URLSearchParams();

  if (sessionToken) {
    searchParams.set("session_token", sessionToken);
  }

  return `${normalizedBaseUrl}/ws/session/${encodedSessionId}${
    searchParams.size > 0 ? `?${searchParams.toString()}` : ""
  }`;
}

function createSocketError(message, details) {
  const error = new Error(message);
  error.details = details ?? null;
  return error;
}

function safeParseEnvelope(rawValue) {
  if (typeof rawValue !== "string") {
    return null;
  }

  return JSON.parse(rawValue);
}

/**
 * Maintains the frontend FastAPI knowledge-stream WebSocket connection.
 *
 * Behavior derived from the context docs:
 * - connect to /ws/session/{sessionId}
 * - exchange JSON envelopes
 * - automatically reconnect with backoff
 * - surface offline state without breaking the rest of the UI
 */
export function useBackendSocket(options = {}) {
  const {
    sessionId = null,
    sessionToken = null,
    enabled = true,
    wsBaseUrl = process.env.NEXT_PUBLIC_WS_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "",
    reconnect = true,
    initialReconnectDelayMs = 500,
    maxReconnectDelayMs = 10_000,
    queueWhileDisconnected = true,
    onEnvelope,
    onOpen,
    onClose,
    onError,
  } = options;

  const socketRef = useRef(null);
  const connectRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const manualDisconnectRef = useRef(false);
  const queueRef = useRef([]);
  const onEnvelopeRef = useRef(onEnvelope);
  const onOpenRef = useRef(onOpen);
  const onCloseRef = useRef(onClose);
  const onErrorRef = useRef(onError);

  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);
  const [lastEnvelope, setLastEnvelope] = useState(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  useEffect(() => {
    onEnvelopeRef.current = onEnvelope;
  }, [onEnvelope]);

  useEffect(() => {
    onOpenRef.current = onOpen;
  }, [onOpen]);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const teardownSocket = useCallback(
    (code = 1000, reason = "Manual disconnect", { manual = true } = {}) => {
      manualDisconnectRef.current = manual;
      clearReconnectTimer();

      const socket = socketRef.current;
      socketRef.current = null;

      if (socket && socket.readyState < WebSocket.CLOSING) {
        socket.close(code, reason);
      }
    },
    [clearReconnectTimer],
  );

  const flushQueue = useCallback(() => {
    const socket = socketRef.current;

    if (!socket || socket.readyState !== WebSocket.OPEN || queueRef.current.length === 0) {
      return;
    }

    const queuedMessages = queueRef.current.splice(0, queueRef.current.length);

    queuedMessages.forEach((message) => {
      socket.send(message);
    });
  }, []);

  const disconnect = useCallback(
    (code = 1000, reason = "Manual disconnect") => {
      teardownSocket(code, reason, { manual: true });
      setStatus((currentStatus) => (currentStatus === "offline" ? "offline" : "closed"));
    },
    [teardownSocket],
  );

  const connect = useCallback(() => {
    if (!enabled || !sessionId || !sessionToken) {
      return null;
    }

    if (typeof WebSocket === "undefined") {
      const nextError = createSocketError("WebSocket is not available in the current runtime.");
      setError(nextError);
      setStatus("error");
      onErrorRef.current?.(nextError);
      return null;
    }

    const existingSocket = socketRef.current;

    if (existingSocket && existingSocket.readyState <= WebSocket.OPEN) {
      return existingSocket;
    }

    manualDisconnectRef.current = false;
    clearReconnectTimer();
    setError(null);
    setStatus(reconnectAttemptsRef.current > 0 ? "reconnecting" : "connecting");

    const socket = new WebSocket(buildSessionSocketUrl(wsBaseUrl, sessionId, sessionToken));
    socketRef.current = socket;

    const handleEnvelope = (rawValue) => {
      try {
        const envelope = safeParseEnvelope(rawValue);

        if (!envelope) {
          return;
        }

        setLastEnvelope(envelope);
        onEnvelopeRef.current?.(envelope);
      } catch (parseError) {
        const nextError = createSocketError("Received an invalid JSON envelope from the backend.", {
          cause: parseError,
          rawValue,
        });
        setError(nextError);
        onErrorRef.current?.(nextError);
      }
    };

    socket.addEventListener("open", (event) => {
      reconnectAttemptsRef.current = 0;
      setReconnectAttempts(0);
      setStatus("open");
      flushQueue();
      onOpenRef.current?.(event);
    });

    socket.addEventListener("message", (event) => {
      if (typeof event.data === "string") {
        handleEnvelope(event.data);
        return;
      }

      if (typeof Blob !== "undefined" && event.data instanceof Blob) {
        event.data.text().then(handleEnvelope).catch((blobError) => {
          const nextError = createSocketError("Unable to read a backend WebSocket message.", {
            cause: blobError,
          });
          setError(nextError);
          onErrorRef.current?.(nextError);
        });
      }
    });

    socket.addEventListener("error", (event) => {
      const nextError = createSocketError("The backend WebSocket connection failed.", { event });
      setError(nextError);
      setStatus("error");
      onErrorRef.current?.(nextError);
    });

    socket.addEventListener("close", (event) => {
      onCloseRef.current?.(event);

      if (socketRef.current === socket) {
        socketRef.current = null;
      }

      if (manualDisconnectRef.current || !enabled || !sessionId) {
        setStatus((currentStatus) => (currentStatus === "offline" ? "offline" : "closed"));
        return;
      }

      const isOffline = typeof navigator !== "undefined" && navigator.onLine === false;

      if (isOffline) {
        setStatus("offline");
        return;
      }

      if (!reconnect) {
        setStatus("closed");
        return;
      }

      reconnectAttemptsRef.current += 1;
      setReconnectAttempts(reconnectAttemptsRef.current);

      const delay = Math.min(
        initialReconnectDelayMs * 2 ** (reconnectAttemptsRef.current - 1),
        maxReconnectDelayMs,
      );

      setStatus("reconnecting");
      clearReconnectTimer();
      reconnectTimerRef.current = setTimeout(() => {
        connectRef.current?.();
      }, delay);
    });

    return socket;
  }, [
    clearReconnectTimer,
    enabled,
    flushQueue,
    initialReconnectDelayMs,
    maxReconnectDelayMs,
    reconnect,
    sessionId,
    sessionToken,
    wsBaseUrl,
  ]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  const sendJson = useCallback(
    (value) => {
      const serialized = JSON.stringify(value);
      const socket = socketRef.current;

      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(serialized);
        return true;
      }

      if (queueWhileDisconnected) {
        queueRef.current.push(serialized);
      }

      return false;
    },
    [queueWhileDisconnected],
  );

  const sendEnvelope = useCallback(
    (type, payload = {}, overrides = {}) =>
      sendJson({
        type,
        session_id: overrides.session_id ?? overrides.sessionId ?? sessionId,
        payload,
        sent_at_ms: overrides.sent_at_ms ?? overrides.sentAtMs ?? Date.now(),
        correlation_id: overrides.correlation_id ?? overrides.correlationId,
      }),
    [sendJson, sessionId],
  );

  const getSocket = useCallback(() => socketRef.current, []);

  useEffect(() => {
    if (!enabled || !sessionId || !sessionToken) {
      teardownSocket(1000, "Session unavailable", { manual: true });
      return undefined;
    }

    const connectTimer = setTimeout(() => {
      connect();
    }, 0);

    return () => {
      clearTimeout(connectTimer);
      teardownSocket(1000, "Session cleanup", { manual: true });
    };
  }, [connect, enabled, sessionId, sessionToken, teardownSocket]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return undefined;
    }

    const handleOffline = () => {
      setStatus("offline");
    };

    const handleOnline = () => {
      if (!enabled || !sessionId || !sessionToken) {
        return;
      }

      if (!socketRef.current || socketRef.current.readyState >= WebSocket.CLOSING) {
        connect();
      }
    };

    window.addEventListener("offline", handleOffline);
    window.addEventListener("online", handleOnline);

    return () => {
      window.removeEventListener("offline", handleOffline);
      window.removeEventListener("online", handleOnline);
    };
  }, [connect, enabled, sessionId, sessionToken]);

  useEffect(() => () => clearReconnectTimer(), [clearReconnectTimer]);

  return useMemo(
    () => ({
      status,
      error,
      lastEnvelope,
      reconnectAttempts,
      isOpen: status === "open",
      isOffline: status === "offline",
      getSocket,
      connect,
      disconnect,
      sendJson,
      sendEnvelope,
    }),
    [connect, disconnect, error, getSocket, lastEnvelope, reconnectAttempts, sendEnvelope, sendJson, status],
  );
}

export default useBackendSocket;
