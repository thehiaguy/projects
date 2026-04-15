"use client";

import { useCallback, useMemo, useRef, useState } from "react";

function valueToText(value) {
  if (typeof value === "string") {
    return value;
  }

  if (Array.isArray(value)) {
    return value
      .map((part) => {
        if (typeof part === "string") {
          return part;
        }

        return (
          part?.text ??
          part?.content ??
          part?.message ??
          part?.value ??
          ""
        );
      })
      .join("")
      .trim();
  }

  if (value && typeof value === "object") {
    return value.text ?? value.content ?? value.message ?? "";
  }

  return "";
}

function normalizeEventType(rawEvent) {
  return rawEvent?.type ?? rawEvent?.message_type ?? rawEvent?.messageType ?? null;
}

function normalizeProsodyScores(rawEvent) {
  const scores =
    rawEvent?.prosody_scores ??
    rawEvent?.prosodyScores ??
    rawEvent?.models?.prosody?.scores ??
    rawEvent?.models?.prosody?.top ??
    null;

  if (!scores || typeof scores !== "object" || Array.isArray(scores)) {
    return null;
  }

  return scores;
}

function normalizeTimestamp(rawEvent) {
  return (
    rawEvent?.timestamp_ms ??
    rawEvent?.timestampMs ??
    rawEvent?.time?.end ??
    rawEvent?.time?.begin ??
    rawEvent?.timestamp ??
    Date.now()
  );
}

function upsertTranscriptEntry(entries, nextEntry, maxTranscriptEntries) {
  const nextEntries = [...entries];
  const existingIndex = nextEntries.findIndex((entry) => entry.messageId === nextEntry.messageId);

  if (existingIndex >= 0) {
    nextEntries[existingIndex] = {
      ...nextEntries[existingIndex],
      ...nextEntry,
    };
    return nextEntries;
  }

  nextEntries.push(nextEntry);

  if (nextEntries.length > maxTranscriptEntries) {
    return nextEntries.slice(nextEntries.length - maxTranscriptEntries);
  }

  return nextEntries;
}

/**
 * Normalizes raw Hume EVI events for the frontend and forwards the backend-relevant
 * envelopes to the FastAPI WebSocket. Interim user transcripts are intentionally not
 * forwarded to the backend KG pipeline.
 */
export function useEviEventForwarder(options = {}) {
  const {
    sessionId = null,
    sendEnvelope,
    dedupeWindowMs = 750,
    maxTranscriptEntries = 100,
    forwardAssistantMessages = true,
    forwardChatMetadata = true,
  } = options;

  const recentlyForwardedRef = useRef(new Map());

  const [transcript, setTranscript] = useState([]);
  const [latestProsodyFrame, setLatestProsodyFrame] = useState(null);
  const [lastForwardedEvent, setLastForwardedEvent] = useState(null);

  const normalizeMessageEvent = useCallback((rawEvent, fallbackRole) => {
    const type = normalizeEventType(rawEvent);
    const content = valueToText(
      rawEvent?.content ??
        rawEvent?.message ??
        rawEvent?.text ??
        rawEvent?.transcript ??
        rawEvent?.message_text,
    );

    return {
      type,
      messageId:
        rawEvent?.message_id ??
        rawEvent?.messageId ??
        rawEvent?.id ??
        rawEvent?.chatId ??
        `${fallbackRole}-${Date.now()}`,
      role: rawEvent?.role ?? fallbackRole,
      content,
      interim: Boolean(rawEvent?.interim ?? rawEvent?.is_interim),
      prosodyScores: normalizeProsodyScores(rawEvent),
      timestampMs: normalizeTimestamp(rawEvent),
      rawEvent,
    };
  }, []);

  const shouldForward = useCallback(
    (signature) => {
      const now = Date.now();
      const lastSentAt = recentlyForwardedRef.current.get(signature);

      if (typeof lastSentAt === "number" && now - lastSentAt < dedupeWindowMs) {
        return false;
      }

      recentlyForwardedRef.current.set(signature, now);

      if (recentlyForwardedRef.current.size > 200) {
        const cutoff = now - dedupeWindowMs;

        recentlyForwardedRef.current.forEach((sentAt, key) => {
          if (sentAt < cutoff) {
            recentlyForwardedRef.current.delete(key);
          }
        });
      }

      return true;
    },
    [dedupeWindowMs],
  );

  const forwardEvent = useCallback(
    (rawEvent) => {
      const type = normalizeEventType(rawEvent);

      if (!type) {
        return null;
      }

      if (type === "user_message") {
        const normalizedMessage = normalizeMessageEvent(rawEvent, "user");

        setTranscript((currentTranscript) =>
          upsertTranscriptEntry(currentTranscript, normalizedMessage, maxTranscriptEntries),
        );

        if (normalizedMessage.prosodyScores) {
          setLatestProsodyFrame({
            messageId: normalizedMessage.messageId,
            role: normalizedMessage.role,
            prosodyScores: normalizedMessage.prosodyScores,
            timestampMs: normalizedMessage.timestampMs,
            rawEvent,
          });
        }

        if (normalizedMessage.interim) {
          return {
            forwarded: false,
            type: "evi.user_message.interim",
            payload: normalizedMessage,
          };
        }

        const payload = {
          message_id: normalizedMessage.messageId,
          role: normalizedMessage.role,
          content: normalizedMessage.content,
          interim: false,
          prosody_scores: normalizedMessage.prosodyScores,
          timestamp_ms: normalizedMessage.timestampMs,
          raw_event: normalizedMessage.rawEvent,
        };

        const signature = [
          sessionId ?? "no-session",
          "evi.user_message.final",
          payload.message_id,
          payload.content,
        ].join(":");

        if (!shouldForward(signature)) {
          return {
            forwarded: false,
            type: "evi.user_message.final",
            payload,
          };
        }

        sendEnvelope?.("evi.user_message.final", payload);
        setLastForwardedEvent({
          type: "evi.user_message.final",
          payload,
          sentAtMs: Date.now(),
        });

        return {
          forwarded: true,
          type: "evi.user_message.final",
          payload,
        };
      }

      if (type === "assistant_message") {
        const normalizedMessage = normalizeMessageEvent(rawEvent, "assistant");

        setTranscript((currentTranscript) =>
          upsertTranscriptEntry(currentTranscript, normalizedMessage, maxTranscriptEntries),
        );

        if (!forwardAssistantMessages) {
          return {
            forwarded: false,
            type: "evi.assistant_message",
            payload: normalizedMessage,
          };
        }

        const payload = {
          message_id: normalizedMessage.messageId,
          role: normalizedMessage.role,
          content: normalizedMessage.content,
          timestamp_ms: normalizedMessage.timestampMs,
          raw_event: normalizedMessage.rawEvent,
        };

        const signature = [
          sessionId ?? "no-session",
          "evi.assistant_message",
          payload.message_id,
          payload.content,
        ].join(":");

        if (!shouldForward(signature)) {
          return {
            forwarded: false,
            type: "evi.assistant_message",
            payload,
          };
        }

        sendEnvelope?.("evi.assistant_message", payload);
        setLastForwardedEvent({
          type: "evi.assistant_message",
          payload,
          sentAtMs: Date.now(),
        });

        return {
          forwarded: true,
          type: "evi.assistant_message",
          payload,
        };
      }

      if (type === "chat_metadata") {
        const payload = {
          provider: "hume",
          chat_id: rawEvent?.chatId ?? rawEvent?.chat_id ?? null,
          chat_group_id: rawEvent?.chatGroupId ?? rawEvent?.chat_group_id ?? null,
          timestamp_ms: normalizeTimestamp(rawEvent),
          raw_event: rawEvent,
        };

        if (!forwardChatMetadata) {
          return {
            forwarded: false,
            type: "evi.chat_metadata",
            payload,
          };
        }

        const signature = [
          sessionId ?? "no-session",
          "evi.chat_metadata",
          JSON.stringify(payload),
        ].join(":");

        if (!shouldForward(signature)) {
          return {
            forwarded: false,
            type: "evi.chat_metadata",
            payload,
          };
        }

        sendEnvelope?.("evi.chat_metadata", payload);
        setLastForwardedEvent({
          type: "evi.chat_metadata",
          payload,
          sentAtMs: Date.now(),
        });

        return {
          forwarded: true,
          type: "evi.chat_metadata",
          payload,
        };
      }

      return {
        forwarded: false,
        type,
        payload: rawEvent,
      };
    },
    [
      forwardAssistantMessages,
      forwardChatMetadata,
      maxTranscriptEntries,
      normalizeMessageEvent,
      sendEnvelope,
      sessionId,
      shouldForward,
    ],
  );

  const resetForwarder = useCallback(() => {
    recentlyForwardedRef.current.clear();
    setTranscript([]);
    setLatestProsodyFrame(null);
    setLastForwardedEvent(null);
  }, []);

  return useMemo(
    () => ({
      transcript,
      finalTranscript: transcript.filter((entry) => !entry.interim),
      latestProsodyFrame,
      lastForwardedEvent,
      forwardEvent,
      resetForwarder,
    }),
    [forwardEvent, lastForwardedEvent, latestProsodyFrame, resetForwarder, transcript],
  );
}

export default useEviEventForwarder;
