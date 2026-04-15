"use client";

import { VoiceProvider, useVoice } from "@humeai/voice-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ConnectionStatus from "./ConnectionStatus";
import GraphPanel from "./GraphPanel";
import HumeDebugPanel from "./HumeDebugPanel";
import ProsodyPanel from "./ProsodyPanel";
import ReceiptsPanel from "./ReceiptsPanel";
import TranscriptPanel from "./TranscriptPanel";
import VoicePanel from "./VoicePanel";
import { createSession, endSession, getHumeAccessToken, getSessionGraphSnapshot, normalizeBackendEnvelope } from "../lib/api";
import { deriveBackendWsBaseUrl } from "../lib/runtime";
import { clearSessionRecord, persistSessionRecord, readSessionRecord, updateSessionRecord } from "../lib/sessionStore";
import { prosodyScoresToSignals } from "../lib/graphTransform";
import useBackendSocket from "../hooks/useBackendSocket";
import useEviEventForwarder from "../hooks/useEviEventForwarder";
import useGraphState from "../hooks/useGraphState";

function serializeDebugValue(value) {
  return JSON.stringify(
    value,
    (key, nestedValue) => {
      if (nestedValue instanceof Date) {
        return nestedValue.toISOString();
      }

      if (nestedValue instanceof Error) {
        return {
          name: nestedValue.name,
          message: nestedValue.message,
          stack: nestedValue.stack,
        };
      }

      return nestedValue;
    },
    2,
  );
}

function SessionExperienceInner({ sessionId, apiBaseUrl, wsBaseUrl, humeConfigId }) {
  const router = useRouter();
  const voice = useVoice();
  const graphState = useGraphState();
  const {
    graph,
    receipts,
    insightCard,
    safetySignal,
    summaryPartial,
    graphUnavailable,
    lastServerError,
    applyEnvelope,
    applyGraphSnapshot,
  } = graphState;

  const [selectedReceiptId, setSelectedReceiptId] = useState(null);
  const [sessionToken, setSessionToken] = useState(null);
  const [resumedChatGroupId, setResumedChatGroupId] = useState(null);
  const [sessionError, setSessionError] = useState(null);
  const [accessTokenState, setAccessTokenState] = useState({
    token: null,
    expiresAtMs: null,
    loading: false,
  });
  const [isGraphLoading, setIsGraphLoading] = useState(false);
  const [isEnding, setIsEnding] = useState(false);
  const [endResult, setEndResult] = useState(null);
  const [recentHumeEventTypes, setRecentHumeEventTypes] = useState([]);
  const [lastHumeErrorPayload, setLastHumeErrorPayload] = useState(null);

  const processedMessageCountRef = useRef(0);
  const recoveryFetchedRef = useRef(false);
  const initialSnapshotFetchedRef = useRef(false);
  const lastGraphFetchAtRef = useRef(0);
  const lastLoggedVoiceStatusRef = useRef(null);
  const lastLoggedVoiceErrorRef = useRef(null);

  useEffect(() => {
    const sessionRecord = readSessionRecord(sessionId);

    if (!sessionRecord?.sessionToken) {
      setSessionError("Missing session token for this session. Start a new session from the landing page.");
      setSessionToken(null);
      return;
    }

    setSessionError(null);
    setSessionToken(sessionRecord.sessionToken);
    setResumedChatGroupId(sessionRecord.chatGroupId ?? null);
  }, [sessionId]);

  const backendSocket = useBackendSocket({
    sessionId,
    sessionToken,
    enabled: Boolean(sessionId && sessionToken && !endResult),
    wsBaseUrl: wsBaseUrl || deriveBackendWsBaseUrl(apiBaseUrl),
    onEnvelope: (envelope) => {
      applyEnvelope(normalizeBackendEnvelope(envelope));
    },
    onOpen: () => {
      recoveryFetchedRef.current = false;
    },
    onError: (error) => {
      setSessionError(error?.message ?? "The backend websocket failed.");
    },
  });

  const eventForwarder = useEviEventForwarder({
    sessionId,
    sendEnvelope: backendSocket.sendEnvelope,
  });
  const backendSocketStatus = backendSocket.status;
  const sendBackendEnvelope = backendSocket.sendEnvelope;
  const disconnectBackendSocket = backendSocket.disconnect;

  const transcriptEntries = useMemo(
    () => eventForwarder.transcript.filter((entry) => entry.content || entry.text),
    [eventForwarder.transcript],
  );

  useEffect(() => {
    if (voice.messages.length < processedMessageCountRef.current) {
      processedMessageCountRef.current = 0;
    }

    const nextMessages = voice.messages.slice(processedMessageCountRef.current);
    nextMessages.forEach((message) => {
      if (message?.type) {
        console.info("[Hume] message", {
          type: message.type,
          chatId: voice.chatMetadata?.chatId ?? null,
          chatGroupId: voice.chatMetadata?.chatGroupId ?? null,
        });
        console.info("[Hume] message_json", serializeDebugValue(message));
        if (message.type === "error") {
          try {
            setLastHumeErrorPayload(JSON.stringify(message, null, 2));
          } catch {
            setLastHumeErrorPayload(String(message));
          }
        }
        setRecentHumeEventTypes((current) => [...current, message.type].slice(-12));
        eventForwarder.forwardEvent(message);
      }
    });
    processedMessageCountRef.current = voice.messages.length;
  }, [eventForwarder, voice.chatMetadata, voice.messages]);

  useEffect(() => {
    if (lastLoggedVoiceStatusRef.current === voice.status.value) {
      return;
    }

    lastLoggedVoiceStatusRef.current = voice.status.value;
    console.info("[Hume] status", {
      status: voice.status.value,
      readyState: voice.readyState,
      isMuted: voice.isMuted,
      isPlaying: voice.isPlaying,
      chatMetadata: voice.chatMetadata,
    });
  }, [voice.chatMetadata, voice.isMuted, voice.isPlaying, voice.readyState, voice.status.value]);

  useEffect(() => {
    if (!voice.error) {
      return;
    }

    const signature = `${voice.error.type}:${voice.error.reason}:${voice.error.message}`;

    if (lastLoggedVoiceErrorRef.current === signature) {
      return;
    }

    lastLoggedVoiceErrorRef.current = signature;
    console.error("[Hume] error", voice.error);
    console.error("[Hume] error_json", serializeDebugValue(voice.error));
    try {
      setLastHumeErrorPayload(JSON.stringify(voice.error, null, 2));
    } catch {
      setLastHumeErrorPayload(String(voice.error));
    }
  }, [voice.error]);

  const fetchGraphSnapshot = useCallback(async () => {
    if (!sessionId || endResult) {
      return;
    }

    setIsGraphLoading(true);

    try {
      const snapshot = await getSessionGraphSnapshot({
        baseUrl: apiBaseUrl,
        sessionId,
      });
      applyGraphSnapshot(snapshot);
      lastGraphFetchAtRef.current = Date.now();
      setSessionError(null);
    } catch (error) {
      setSessionError(error?.message ?? "Unable to load the graph snapshot.");
    } finally {
      setIsGraphLoading(false);
    }
  }, [apiBaseUrl, applyGraphSnapshot, endResult, sessionId]);

  useEffect(() => {
    if (initialSnapshotFetchedRef.current) {
      return;
    }

    initialSnapshotFetchedRef.current = true;
    void fetchGraphSnapshot();
  }, [fetchGraphSnapshot]);

  useEffect(() => {
    if (backendSocketStatus !== "open" || recoveryFetchedRef.current) {
      return;
    }

    recoveryFetchedRef.current = true;
    sendBackendEnvelope("client.ping", {});

    if (Date.now() - lastGraphFetchAtRef.current > 2_000) {
      void fetchGraphSnapshot();
    }
  }, [backendSocketStatus, fetchGraphSnapshot, sendBackendEnvelope]);

  useEffect(() => {
    const chatGroupId = voice.chatMetadata?.chatGroupId ?? null;

    if (!chatGroupId || chatGroupId === resumedChatGroupId) {
      return;
    }

    updateSessionRecord(sessionId, {
      chatGroupId,
      chatId: voice.chatMetadata?.chatId ?? null,
    });
    setResumedChatGroupId(chatGroupId);
  }, [resumedChatGroupId, sessionId, voice.chatMetadata]);

  const ensureAccessToken = useCallback(async () => {
    const expiresSoon =
      typeof accessTokenState.expiresAtMs === "number" && accessTokenState.expiresAtMs - Date.now() < 60_000;

    if (accessTokenState.token && !expiresSoon) {
      return accessTokenState.token;
    }

    setAccessTokenState((currentState) => ({ ...currentState, loading: true }));

    try {
      const response = await getHumeAccessToken({ baseUrl: apiBaseUrl });
      setAccessTokenState({
        token: response.accessToken,
        expiresAtMs: response.expiresAtMs,
        loading: false,
      });
      return response.accessToken;
    } catch (error) {
      setSessionError(error?.message ?? "Unable to fetch a Hume access token.");
      setAccessTokenState((currentState) => ({ ...currentState, loading: false }));
      throw error;
    }
  }, [accessTokenState.expiresAtMs, accessTokenState.token, apiBaseUrl]);

  useEffect(() => {
    if (!sessionId || !sessionToken || endResult || accessTokenState.loading || accessTokenState.token) {
      return;
    }

    void ensureAccessToken().catch(() => {
      // The start button should remain usable even if eager token fetch fails.
    });
  }, [
    accessTokenState.loading,
    accessTokenState.token,
    endResult,
    ensureAccessToken,
    sessionId,
    sessionToken,
  ]);

  const handleToggleSession = useCallback(async () => {
    if (voice.status.value === "connected" || voice.status.value === "connecting") {
      await voice.disconnect();
      return;
    }

    if (!sessionToken) {
      setSessionError("This session does not have a backend session token.");
      return;
    }

    if (!accessTokenState.token) {
      if (!accessTokenState.loading) {
        void ensureAccessToken().catch(() => {
          // Surface of failure is handled inside ensureAccessToken.
        });
      }

      setSessionError("Preparing the Hume access token. Press Start again once it is ready.");
      return;
    }

    try {
      console.info("[Hume] connect_attempt", {
        sessionId,
        hasToken: Boolean(accessTokenState.token),
        humeConfigId: humeConfigId || null,
        resumedChatGroupId: resumedChatGroupId || null,
      });
      await voice.connect({
        auth: { type: "accessToken", value: accessTokenState.token },
        configId: humeConfigId || undefined,
        resumedChatGroupId: resumedChatGroupId || undefined,
        verboseTranscription: true,
        sessionSettings: {
          customSessionId: sessionId,
        },
      });
      setSessionError(null);
    } catch (error) {
      setSessionError(error?.message ?? "Unable to start the Hume voice session.");
    }
  }, [
    accessTokenState.loading,
    accessTokenState.token,
    ensureAccessToken,
    humeConfigId,
    resumedChatGroupId,
    sessionId,
    sessionToken,
    voice,
  ]);

  const handleToggleMute = useCallback(() => {
    if (voice.isMuted) {
      voice.unmute();
      return;
    }

    voice.mute();
  }, [voice]);

  const handleEndSession = useCallback(async () => {
    if (isEnding || endResult) {
      return;
    }

    setIsEnding(true);

    try {
      if (voice.status.value === "connected" || voice.status.value === "connecting") {
        await voice.disconnect();
      }

      const result = await endSession({
        baseUrl: apiBaseUrl,
        sessionId,
      });

      clearSessionRecord(sessionId);
      setEndResult(result);
      setSessionError(null);
      disconnectBackendSocket(1000, "Session ended");
    } catch (error) {
      setSessionError(error?.message ?? "Unable to end the current session.");
    } finally {
      setIsEnding(false);
    }
  }, [apiBaseUrl, disconnectBackendSocket, endResult, isEnding, sessionId, voice]);

  const handleCreateNewSession = useCallback(async () => {
    try {
      if (voice.status.value === "connected" || voice.status.value === "connecting") {
        await voice.disconnect();
      }

      if (!endResult) {
        try {
          await endSession({ baseUrl: apiBaseUrl, sessionId });
        } catch {
          // Best-effort finalization before creating a new session.
        }
      }

      clearSessionRecord(sessionId);
      const nextSession = await createSession({ baseUrl: apiBaseUrl });
      persistSessionRecord(nextSession);
      router.replace(`/session?sessionId=${encodeURIComponent(nextSession.sessionId)}`);
    } catch (error) {
      setSessionError(error?.message ?? "Unable to create a new session.");
    }
  }, [apiBaseUrl, endResult, router, sessionId, voice]);

  const latestSignals = useMemo(
    () => prosodyScoresToSignals(eventForwarder.latestProsodyFrame?.prosodyScores, 8),
    [eventForwarder.latestProsodyFrame?.prosodyScores],
  );

  const highlightedReceipt = useMemo(
    () => receipts.find((receipt) => receipt.receiptId === selectedReceiptId) ?? null,
    [receipts, selectedReceiptId],
  );

  const lastError =
    sessionError ??
    voice.error?.message ??
    lastServerError?.message ??
    null;

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(244,201,93,0.24),_transparent_24%),linear-gradient(180deg,#f9faf6,#eef4ff)] px-4 py-4 text-slate-950 md:px-6 md:py-6">
      <div className="mx-auto grid max-w-7xl gap-4 lg:grid-cols-[1.4fr_0.95fr]">
        <section className="space-y-4">
          <VoicePanel
            micFft={voice.micFft}
            assistantFft={voice.fft}
            isConnected={voice.status.value === "connected"}
            isMuted={voice.isMuted}
            isPlaying={voice.isPlaying}
            sessionLabel={endResult ? "Session ended" : `Session ${sessionId}`}
            helperText={
              endResult
                ? "This backend session has been finalized. Create a new session to continue testing."
                : "The dock below now controls Hume EVI directly. Finalized user and assistant events are forwarded into your FastAPI websocket contract."
            }
            dockProps={{
              canCreateNewSession: !isEnding,
              canToggleSession:
                !isEnding &&
                !endResult &&
                Boolean(sessionToken) &&
                (Boolean(accessTokenState.token) || !accessTokenState.loading),
              canToggleMute: !isEnding && !endResult && voice.status.value === "connected",
              canEndSession: !isEnding && !endResult && Boolean(sessionId),
              isLive: voice.status.value === "connected" || voice.status.value === "connecting",
              isMuted: voice.isMuted,
              isEnding,
              onCreateNewSession: handleCreateNewSession,
              onToggleSession: handleToggleSession,
              onToggleMute: handleToggleMute,
              onEndSession: handleEndSession,
            }}
          />

          <ConnectionStatus
            backendStatus={backendSocketStatus}
            voiceStatus={voice.status.value}
            lastError={lastError}
            sessionId={sessionId}
          />
          <HumeDebugPanel
            voiceStatus={voice.status.value}
            readyState={voice.readyState}
            tokenState={accessTokenState}
            humeConfigId={humeConfigId}
            chatId={voice.chatMetadata?.chatId ?? null}
            chatGroupId={voice.chatMetadata?.chatGroupId ?? null}
            lastError={voice.error?.message ?? null}
            lastErrorPayload={lastHumeErrorPayload}
            recentEventTypes={recentHumeEventTypes}
          />
          <TranscriptPanel entries={transcriptEntries} />
          <ProsodyPanel signals={latestSignals} />
        </section>

        <section className="space-y-4">
          <GraphPanel
            graph={graph}
            highlightedNodeIds={highlightedReceipt?.nodeIds ?? []}
            highlightedEdgeIds={highlightedReceipt?.edgeIds ?? []}
            graphUnavailable={graphUnavailable}
          />
          <ReceiptsPanel
            receipts={receipts}
            selectedReceiptId={selectedReceiptId}
            onSelectReceipt={setSelectedReceiptId}
            summaryPartial={summaryPartial}
            insightCard={insightCard}
            safetySignal={safetySignal}
            endSummary={endResult?.summary}
            topConcepts={endResult?.topConcepts ?? []}
          />
          {isGraphLoading ? (
            <div className="rounded-[2rem] border border-slate-200/80 bg-white/88 px-5 py-4 text-sm text-slate-500 shadow-[0_20px_45px_rgba(15,23,42,0.08)]">
              Refreshing graph snapshot...
            </div>
          ) : null}
        </section>
      </div>
    </main>
  );
}

export default function SessionExperience(props) {
  return (
    <VoiceProvider key={props.sessionId} clearMessagesOnDisconnect={false}>
      <SessionExperienceInner key={props.sessionId} {...props} />
    </VoiceProvider>
  );
}
