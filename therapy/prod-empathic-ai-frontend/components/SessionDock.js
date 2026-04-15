"use client";

function ControlButton({ label, hint, active = false, disabled = false, onClick, icon }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`flex min-w-[7rem] items-center gap-3 rounded-full border px-4 py-3 text-left transition ${
        disabled
          ? "cursor-not-allowed border-slate-200/70 bg-slate-100/70 text-slate-400"
          : active
            ? "border-slate-900 bg-slate-900 text-white shadow-[0_20px_35px_rgba(15,23,42,0.22)]"
            : "border-slate-200 bg-white/92 text-slate-900 hover:-translate-y-0.5 hover:border-slate-300"
      }`}
    >
      <span
        className={`flex h-10 w-10 items-center justify-center rounded-full ${
          active ? "bg-white/14 text-white" : "bg-slate-100 text-slate-700"
        }`}
      >
        {icon}
      </span>
      <span className="flex flex-col">
        <span className="text-sm font-semibold">{label}</span>
        <span className={`text-[0.68rem] uppercase tracking-[0.24em] ${active ? "text-white/60" : "text-slate-500"}`}>
          {hint}
        </span>
      </span>
    </button>
  );
}

function PlusIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-[2]">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 5v14M5 12h14" />
    </svg>
  );
}

function PowerIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-[2]">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v8" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M7.05 6.34a8 8 0 1 0 9.9 0" />
    </svg>
  );
}

function MicIcon({ muted = false }) {
  return muted ? (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-[2]">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9V7a3 3 0 0 0-5.88-1.12" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M17 12a5 5 0 0 1-8.47 3.53M5 12a5 5 0 0 0 8 4" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 17v4M8 21h8M4 4l16 16" />
    </svg>
  ) : (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-[2]">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 15a3 3 0 0 0 3-3V7a3 3 0 1 0-6 0v5a3 3 0 0 0 3 3Z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 11a7 7 0 0 1-14 0M12 18v3M8 21h8" />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5 fill-current">
      <rect x="6" y="6" width="12" height="12" rx="2.5" />
    </svg>
  );
}

export default function SessionDock({
  canCreateNewSession,
  canToggleSession,
  canToggleMute,
  canEndSession,
  isLive,
  isMuted,
  isEnding,
  onCreateNewSession,
  onToggleSession,
  onToggleMute,
  onEndSession,
}) {
  return (
    <div className="rounded-[2rem] border border-slate-200/80 bg-white/88 p-3 shadow-[0_28px_60px_rgba(15,23,42,0.12)] backdrop-blur">
      <div className="flex flex-wrap items-center gap-3">
        <ControlButton
          label="New"
          hint="Create"
          onClick={onCreateNewSession}
          disabled={!canCreateNewSession}
          icon={<PlusIcon />}
        />
        <ControlButton
          label={isLive ? "Stop" : "Start"}
          hint={isLive ? "Disconnect" : "Connect"}
          onClick={onToggleSession}
          active={isLive}
          disabled={!canToggleSession}
          icon={isLive ? <StopIcon /> : <PowerIcon />}
        />
        <ControlButton
          label={isMuted ? "Unmute" : "Mute"}
          hint="Mic"
          onClick={onToggleMute}
          active={isLive && !isMuted}
          disabled={!canToggleMute}
          icon={<MicIcon muted={isMuted} />}
        />
        <ControlButton
          label={isEnding ? "Ending" : "End"}
          hint="Finalize"
          onClick={onEndSession}
          disabled={!canEndSession}
          icon={<PowerIcon />}
        />
      </div>
    </div>
  );
}
