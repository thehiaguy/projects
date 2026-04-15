"use client";

function StatusRow({ label, value }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-2xl bg-slate-50 px-4 py-3">
      <p className="text-xs uppercase tracking-[0.24em] text-slate-500">{label}</p>
      <p className="max-w-[65%] truncate text-right text-sm font-medium text-slate-900">{value || "n/a"}</p>
    </div>
  );
}

export default function HumeDebugPanel({
  voiceStatus,
  readyState,
  tokenState,
  humeConfigId,
  chatId,
  chatGroupId,
  lastError,
  lastErrorPayload,
  recentEventTypes,
}) {
  return (
    <section className="rounded-[2rem] border border-slate-200/80 bg-white/88 p-5 shadow-[0_20px_45px_rgba(15,23,42,0.08)]">
      <div>
        <p className="text-xs uppercase tracking-[0.32em] text-slate-500">Hume debug</p>
        <h3 className="mt-2 text-xl font-semibold text-slate-900">Realtime connection diagnostics</h3>
      </div>

      <div className="mt-5 space-y-3">
        <StatusRow label="Voice status" value={voiceStatus} />
        <StatusRow label="Ready state" value={readyState} />
        <StatusRow
          label="Token"
          value={tokenState.loading ? "loading" : tokenState.token ? "prefetched" : "missing"}
        />
        <StatusRow label="Config id" value={humeConfigId || "not set"} />
        <StatusRow label="Chat id" value={chatId || "not received"} />
        <StatusRow label="Chat group id" value={chatGroupId || "not received"} />
      </div>

      <div className="mt-5 rounded-3xl border border-slate-200 bg-slate-50 px-4 py-4">
        <p className="text-[0.68rem] uppercase tracking-[0.26em] text-slate-500">Last error</p>
        <p className="mt-2 text-sm leading-6 text-slate-700">{lastError || "No Hume error reported."}</p>
        {lastErrorPayload ? (
          <pre className="mt-3 overflow-x-auto rounded-2xl bg-slate-900 px-4 py-3 text-xs leading-5 text-slate-100">
            {lastErrorPayload}
          </pre>
        ) : null}
      </div>

      <div className="mt-5 rounded-3xl border border-slate-200 bg-slate-50 px-4 py-4">
        <p className="text-[0.68rem] uppercase tracking-[0.26em] text-slate-500">Recent event types</p>
        {recentEventTypes.length === 0 ? (
          <p className="mt-2 text-sm text-slate-700">No Hume websocket messages received yet.</p>
        ) : (
          <div className="mt-3 flex flex-wrap gap-2">
            {recentEventTypes.map((eventType, index) => (
              <span key={`${eventType}-${index}`} className="rounded-full bg-white px-3 py-1 text-sm text-slate-700">
                {eventType}
              </span>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
