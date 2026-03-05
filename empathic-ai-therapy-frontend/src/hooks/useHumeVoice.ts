"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { HumeClient } from "hume";
import type { TranscriptEntry } from "@/lib/types";

const SAMPLE_RATE = 16_000;

export type HumeStatus = "idle" | "connecting" | "active" | "error";

interface UseHumeVoiceOptions {
  accessToken: string | null;
  configId: string;
  sessionId: string | null;
  onFinalUserMessage: (params: {
    messageId: string;
    content: string;
    prosodyScores: Record<string, number>;
    timestampMs: number;
  }) => void;
  onTranscriptEntry: (entry: TranscriptEntry) => void;
}

export function useHumeVoice({
  accessToken,
  configId,
  sessionId,
  onFinalUserMessage,
  onTranscriptEntry,
}: UseHumeVoiceOptions) {
  const [status, setStatus] = useState<HumeStatus>("idle");

  // Refs to avoid stale closures
  const socketRef = useRef<ReturnType<InstanceType<typeof HumeClient>["empathicVoice"]["chat"]["connect"]> extends Promise<infer S> ? S : never>(null as never);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioQueueRef = useRef<AudioBuffer[]>([]);
  const isPlayingRef = useRef(false);
  const playbackCtxRef = useRef<AudioContext | null>(null);

  const onFinalRef = useRef(onFinalUserMessage);
  const onEntryRef = useRef(onTranscriptEntry);
  useEffect(() => { onFinalRef.current = onFinalUserMessage; }, [onFinalUserMessage]);
  useEffect(() => { onEntryRef.current = onTranscriptEntry; }, [onTranscriptEntry]);

  // ─── Audio Playback ───────────────────────────────────────────────────────

  const playNextInQueue = useCallback(() => {
    if (audioQueueRef.current.length === 0) {
      isPlayingRef.current = false;
      return;
    }
    isPlayingRef.current = true;
    const ctx = playbackCtxRef.current!;
    const buffer = audioQueueRef.current.shift()!;
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);
    source.onended = playNextInQueue;
    source.start();
  }, []);

  const enqueueAudio = useCallback(
    async (base64Data: string) => {
      if (!playbackCtxRef.current) {
        playbackCtxRef.current = new AudioContext();
      }
      const ctx = playbackCtxRef.current;
      const binary = atob(base64Data);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      try {
        const decoded = await ctx.decodeAudioData(bytes.buffer);
        audioQueueRef.current.push(decoded);
        if (!isPlayingRef.current) playNextInQueue();
      } catch {
        // Ignore decode errors for partial chunks
      }
    },
    [playNextInQueue]
  );

  const stopPlayback = useCallback(() => {
    audioQueueRef.current = [];
    isPlayingRef.current = false;
    if (playbackCtxRef.current) {
      playbackCtxRef.current.close().catch(() => {});
      playbackCtxRef.current = null;
    }
  }, []);

  // ─── Mic Capture ─────────────────────────────────────────────────────────

  const startMicCapture = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    streamRef.current = stream;

    const ctx = new AudioContext({ sampleRate: SAMPLE_RATE });
    audioCtxRef.current = ctx;

    await ctx.audioWorklet.addModule("/audio-processor.js");

    const source = ctx.createMediaStreamSource(stream);
    const worklet = new AudioWorkletNode(ctx, "audio-processor");
    workletNodeRef.current = worklet;

    worklet.port.onmessage = (e: MessageEvent<Float32Array>) => {
      const float32 = e.data;
      // Convert Float32 PCM → Int16 PCM
      const int16 = new Int16Array(float32.length);
      for (let i = 0; i < float32.length; i++) {
        const s = Math.max(-1, Math.min(1, float32[i]));
        int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
      }
      // Base64 encode
      const bytes = new Uint8Array(int16.buffer);
      let binary = "";
      for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
      const b64 = btoa(binary);

      // Send to Hume EVI
      if (socketRef.current) {
        socketRef.current.sendAudioInput({ data: b64 });
      }
    };

    source.connect(worklet);
    worklet.connect(ctx.destination);
  }, []);

  const stopMicCapture = useCallback(() => {
    workletNodeRef.current?.disconnect();
    workletNodeRef.current = null;
    audioCtxRef.current?.close().catch(() => {});
    audioCtxRef.current = null;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  // ─── Connect / Disconnect ─────────────────────────────────────────────────

  const connect = useCallback(async () => {
    if (!accessToken || !sessionId) return;
    setStatus("connecting");

    try {
      const client = new HumeClient({ accessToken });
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const socket = await (client.empathicVoice.chat as any).connect({
        configId,
      });
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      socketRef.current = socket as any;

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      socket.on("open", async () => {
        setStatus("active");
        await startMicCapture();
      });

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      socket.on("message", (message: any) => {
        const type: string = message?.type;

        if (type === "user_message") {
          const content: string = message?.message?.content ?? "";
          const scores: Record<string, number> =
            message?.models?.prosody?.scores ?? {};
          const messageId: string =
            message?.id ?? `msg_${Date.now()}`;
          const interim: boolean = message?.interim ?? false;

          onEntryRef.current({
            id: messageId,
            role: "user",
            content,
            prosody_scores: scores,
            timestamp_ms: Date.now(),
            interim,
          });

          if (!interim) {
            onFinalRef.current({
              messageId,
              content,
              prosodyScores: scores,
              timestampMs: Date.now(),
            });
          }
        }

        if (type === "assistant_message") {
          const content: string = message?.message?.content ?? "";
          const messageId: string = message?.id ?? `msg_${Date.now()}`;
          onEntryRef.current({
            id: messageId,
            role: "assistant",
            content,
            timestamp_ms: Date.now(),
          });
        }

        if (type === "audio_output") {
          const data: string = message?.data ?? "";
          if (data) enqueueAudio(data);
        }
      });

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      socket.on("error", (err: any) => {
        console.error("Hume EVI error:", err);
        setStatus("error");
      });

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      socket.on("close", () => {
        setStatus("idle");
      });
    } catch (err) {
      console.error("Failed to connect to Hume EVI:", err);
      setStatus("error");
    }
  }, [accessToken, configId, sessionId, startMicCapture, enqueueAudio]);

  const disconnect = useCallback(() => {
    stopMicCapture();
    stopPlayback();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (socketRef.current as any)?.close?.();
    socketRef.current = null as never;
    setStatus("idle");
  }, [stopMicCapture, stopPlayback]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopMicCapture();
      stopPlayback();
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (socketRef.current as any)?.close?.();
    };
  }, [stopMicCapture, stopPlayback]);

  return { status, connect, disconnect };
}
