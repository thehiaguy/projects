"use client";

import AudioBubble from "./AudioBubble.jsx";
import SessionDock from "./SessionDock";
import StartStopCallButton from "./StartStopCallButton";

export default function VoicePanel({
  micFft = [],
  assistantFft = [],
  isConnected = false,
  isMuted = false,
  isPlaying = false,
  sessionLabel,
  helperText,
  dockProps,
}) {
  return (
    <section className="space-y-5">
      <div className="rounded-[2.25rem] border border-white/40 bg-[linear-gradient(180deg,rgba(255,249,235,0.95),rgba(255,255,255,0.9))] p-5 shadow-[0_28px_80px_rgba(35,43,56,0.12)]">
        <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.34em] text-slate-500">Session control</p>
            <h1 className="mt-2 text-3xl font-semibold text-slate-950">{sessionLabel}</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">{helperText}</p>
          </div>
          <StartStopCallButton
            isLive={isConnected}
            disabled={!dockProps?.canToggleSession}
            onClick={dockProps?.onToggleSession}
          />
        </div>

        <AudioBubble
          micFft={micFft}
          assistantFft={assistantFft}
          isConnected={isConnected}
          isMuted={isMuted}
          isPlaying={isPlaying}
        />
      </div>

      <SessionDock {...dockProps} />
    </section>
  );
}
