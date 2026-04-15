"use client";

import { useCallback, useMemo, useState } from "react";

function createHttpError(message, status, details) {
  const error = new Error(message);
  error.status = status ?? null;
  error.details = details ?? null;
  return error;
}

function joinUrl(baseUrl, path) {
  const normalizedBase = (baseUrl || "").replace(/\/+$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  if (normalizedBase) {
    return `${normalizedBase}${normalizedPath}`;
  }

  if (typeof window !== "undefined") {
    return normalizedPath;
  }

  return normalizedPath;
}

async function parseJsonResponse(response) {
  const text = await response.text();

  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text);
  } catch {
    throw createHttpError("Received a non-JSON response from the backend.", response.status, {
      body: text,
    });
  }
}

function readSessionId(payload) {
  return payload?.sessionId ?? payload?.session_id ?? null;
}

function readAccessToken(payload) {
  return payload?.accessToken ?? payload?.access_token ?? null;
}

function readExpiresIn(payload) {
  return payload?.expiresIn ?? payload?.expires_in ?? null;
}

function readTopConcepts(payload) {
  return payload?.topConcepts ?? payload?.top_concepts ?? [];
}

/**
 * Manages frontend session lifecycle against the FastAPI backend.
 *
 * Behavior derived from the context docs:
 * - create a session via POST /v1/sessions
 * - fetch a temporary Hume access token via POST /v1/hume/access-token
 * - end a session via POST /v1/sessions/{id}/end and retain summary data
 */
export function useSession(options = {}) {
  const {
    apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "",
    fetchImpl = typeof fetch === "function" ? fetch.bind(globalThis) : null,
    defaultCreateBody = { consent: true },
  } = options;

  const [sessionId, setSessionId] = useState(null);
  const [sessionRecord, setSessionRecord] = useState(null);
  const [accessToken, setAccessToken] = useState(null);
  const [accessTokenExpiresIn, setAccessTokenExpiresIn] = useState(null);
  const [accessTokenExpiresAt, setAccessTokenExpiresAt] = useState(null);
  const [summary, setSummary] = useState(null);
  const [topConcepts, setTopConcepts] = useState([]);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);
  const [isCreating, setIsCreating] = useState(false);
  const [isFetchingToken, setIsFetchingToken] = useState(false);
  const [isEnding, setIsEnding] = useState(false);

  const assertFetch = useCallback(() => {
    if (!fetchImpl) {
      throw createHttpError("Fetch is not available in the current runtime.");
    }

    return fetchImpl;
  }, [fetchImpl]);

  const createSession = useCallback(
    async (createBody = defaultCreateBody) => {
      const doFetch = assertFetch();

      setIsCreating(true);
      setError(null);
      setStatus("creating");

      try {
        const response = await doFetch(joinUrl(apiBaseUrl, "/v1/sessions"), {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(createBody ?? defaultCreateBody),
        });

        const payload = await parseJsonResponse(response);

        if (!response.ok) {
          throw createHttpError(
            payload?.message ?? "Unable to create a session.",
            response.status,
            payload,
          );
        }

        const nextSessionId = readSessionId(payload);

        if (!nextSessionId) {
          throw createHttpError("The backend did not return a session identifier.", response.status, payload);
        }

        setSessionId(nextSessionId);
        setSessionRecord(payload);
        setSummary(null);
        setTopConcepts([]);
        setAccessToken(null);
        setAccessTokenExpiresIn(null);
        setAccessTokenExpiresAt(null);
        setStatus("created");

        return payload;
      } catch (nextError) {
        setError(nextError);
        setStatus("error");
        throw nextError;
      } finally {
        setIsCreating(false);
      }
    },
    [apiBaseUrl, assertFetch, defaultCreateBody],
  );

  const fetchAccessToken = useCallback(
    async (body = undefined) => {
      const doFetch = assertFetch();

      setIsFetchingToken(true);
      setError(null);
      setStatus((currentStatus) => (currentStatus === "ended" ? "ended" : "tokenizing"));

      try {
        const response = await doFetch(joinUrl(apiBaseUrl, "/v1/hume/access-token"), {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(body ?? {}),
        });

        const payload = await parseJsonResponse(response);

        if (!response.ok) {
          throw createHttpError(
            payload?.message ?? "Unable to fetch a Hume access token.",
            response.status,
            payload,
          );
        }

        const nextAccessToken = readAccessToken(payload);
        const nextExpiresIn = readExpiresIn(payload);

        if (!nextAccessToken) {
          throw createHttpError("The backend did not return a Hume access token.", response.status, payload);
        }

        setAccessToken(nextAccessToken);
        setAccessTokenExpiresIn(nextExpiresIn);
        setAccessTokenExpiresAt(
          typeof nextExpiresIn === "number" ? Date.now() + nextExpiresIn * 1000 : null,
        );
        setStatus((currentStatus) => (currentStatus === "ended" ? "ended" : "ready"));

        return payload;
      } catch (nextError) {
        setError(nextError);
        setStatus("error");
        throw nextError;
      } finally {
        setIsFetchingToken(false);
      }
    },
    [apiBaseUrl, assertFetch],
  );

  const startSession = useCallback(
    async ({
      createBody = defaultCreateBody,
      accessTokenBody = undefined,
    } = {}) => {
      const nextSession = await createSession(createBody);
      const nextToken = await fetchAccessToken(accessTokenBody);

      return {
        session: nextSession,
        token: nextToken,
      };
    },
    [createSession, defaultCreateBody, fetchAccessToken],
  );

  const endSession = useCallback(
    async (targetSessionId = sessionId) => {
      if (!targetSessionId) {
        throw createHttpError("A session must exist before it can be ended.");
      }

      const doFetch = assertFetch();

      setIsEnding(true);
      setError(null);
      setStatus("ending");

      try {
        const response = await doFetch(
          joinUrl(apiBaseUrl, `/v1/sessions/${encodeURIComponent(targetSessionId)}/end`),
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
          },
        );

        const payload = await parseJsonResponse(response);

        if (!response.ok) {
          throw createHttpError(
            payload?.message ?? "Unable to end the current session.",
            response.status,
            payload,
          );
        }

        setSummary(payload?.summary ?? null);
        setTopConcepts(readTopConcepts(payload));
        setSessionRecord((currentRecord) => ({
          ...(currentRecord ?? {}),
          ...(payload ?? {}),
          sessionId: targetSessionId,
          status: "ended",
        }));
        setStatus("ended");

        return payload;
      } catch (nextError) {
        setError(nextError);
        setStatus("error");
        throw nextError;
      } finally {
        setIsEnding(false);
      }
    },
    [apiBaseUrl, assertFetch, sessionId],
  );

  const resetSession = useCallback(() => {
    setSessionId(null);
    setSessionRecord(null);
    setAccessToken(null);
    setAccessTokenExpiresIn(null);
    setAccessTokenExpiresAt(null);
    setSummary(null);
    setTopConcepts([]);
    setError(null);
    setIsCreating(false);
    setIsFetchingToken(false);
    setIsEnding(false);
    setStatus("idle");
  }, []);

  const value = useMemo(
    () => ({
      sessionId,
      sessionRecord,
      accessToken,
      accessTokenExpiresIn,
      accessTokenExpiresAt,
      summary,
      topConcepts,
      status,
      error,
      isCreating,
      isFetchingToken,
      isEnding,
      hasSession: Boolean(sessionId),
      hasActiveSession: Boolean(sessionId) && status !== "ended",
      createSession,
      fetchAccessToken,
      startSession,
      endSession,
      resetSession,
    }),
    [
      accessToken,
      accessTokenExpiresAt,
      accessTokenExpiresIn,
      createSession,
      endSession,
      error,
      fetchAccessToken,
      isCreating,
      isEnding,
      isFetchingToken,
      resetSession,
      sessionId,
      sessionRecord,
      startSession,
      status,
      summary,
      topConcepts,
    ],
  );

  return value;
}

export default useSession;
