"use client";

function toneClasses(tone) {
  switch (tone) {
    case "live":
      return "border-emerald-200 bg-emerald-50 text-emerald-700";
    case "warning":
      return "border-amber-200 bg-amber-50 text-amber-700";
    case "danger":
      return "border-rose-200 bg-rose-50 text-rose-700";
    default:
      return "border-slate-200 bg-slate-50 text-slate-700";
  }
}

function getStatusTone(value) {
  if (value === "open" || value === "connected") {
    return "live";
  }

  if (value === "error" || value === "closed") {
    return "danger";
  }

  if (value === "offline" || value === "reconnecting" || value === "connecting") {
    return "warning";
  }

  return "idle";
}

function StatusPill({ label, value }) {
  const tone = getStatusTone(value);

  return (
    <div className={`rounded-full border px-4 py-2 ${toneClasses(tone)}`}>
      <p className="text-[0.68rem] uppercase tracking-[0.26em]">{label}</p>
      <p className="mt-1 text-sm font-semibold capitalize">{value ?? "idle"}</p>
    </div>
  );
}

export default function ConnectionStatus({ backendStatus, voiceStatus, lastError, sessionId }) {
  return (
    <section className="rounded-[2rem] border border-slate-200/80 bg-white/88 p-5 shadow-[0_20px_45px_rgba(15,23,42,0.08)]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.32em] text-slate-500">Connection status</p>
          <h3 className="mt-2 text-xl font-semibold text-slate-900">Session {sessionId}</h3>
        </div>
        <div className="flex flex-wrap gap-3">
          <StatusPill label="Backend WS" value={backendStatus} />
          <StatusPill label="Hume EVI" value={voiceStatus} />
        </div>
      </div>

      {lastError ? (
        <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {lastError}
        </div>
      ) : null}
    </section>
  );
}
