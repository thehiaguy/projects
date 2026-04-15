"use client";

function formatTimestamp(timestampMs) {
  if (!timestampMs) {
    return "Live";
  }

  return new Date(timestampMs).toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function TranscriptPanel({ entries = [] }) {
  return (
    <section className="rounded-[2rem] border border-slate-200/80 bg-white/88 p-5 shadow-[0_20px_45px_rgba(15,23,42,0.08)]">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.32em] text-slate-500">Transcript</p>
          <h3 className="mt-2 text-xl font-semibold text-slate-900">Conversation feed</h3>
        </div>
        <p className="text-sm text-slate-500">{entries.length} messages</p>
      </div>

      <div className="mt-5 max-h-[28rem] space-y-3 overflow-y-auto pr-1">
        {entries.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-slate-200 px-4 py-8 text-center text-sm text-slate-500">
            Once you start the session, finalized Hume user and assistant messages will appear here.
          </div>
        ) : null}

        {entries.map((entry) => (
          <article
            key={entry.messageId}
            className={`rounded-3xl px-4 py-4 ${
              entry.role === "user" ? "bg-[#f4c95d]/25 text-slate-900" : "bg-slate-900 text-white"
            }`}
          >
            <div className="flex items-center justify-between gap-4">
              <p className="text-[0.7rem] uppercase tracking-[0.28em] opacity-70">
                {entry.role === "user" ? "You" : "EVI"}
              </p>
              <p className="text-xs opacity-70">
                {entry.interim ? "Interim" : formatTimestamp(entry.timestampMs)}
              </p>
            </div>
            <p className="mt-3 text-sm leading-6 opacity-95">{entry.content || entry.text || "..."}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
