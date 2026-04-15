"use client";

function formatPercent(score) {
  return `${Math.round(Number(score || 0) * 100)}%`;
}

export default function ProsodyPanel({ signals = [] }) {
  return (
    <section className="rounded-[2rem] border border-slate-200/80 bg-white/88 p-5 shadow-[0_20px_45px_rgba(15,23,42,0.08)]">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.32em] text-slate-500">Prosody</p>
          <h3 className="mt-2 text-xl font-semibold text-slate-900">Audio emotion scores</h3>
        </div>
      </div>

      <div className="mt-5 space-y-3">
        {signals.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-slate-200 px-4 py-8 text-center text-sm text-slate-500">
            Hume user-message prosody scores will surface here once audio starts flowing.
          </div>
        ) : null}

        {signals.map((signal) => (
          <div key={signal.label} className="rounded-3xl bg-slate-50 px-4 py-3">
            <div className="flex items-center justify-between gap-4">
              <p className="text-sm font-semibold text-slate-900">{signal.label}</p>
              <p className="text-sm text-slate-500">{formatPercent(signal.score)}</p>
            </div>
            <div className="mt-3 h-2 rounded-full bg-white">
              <div
                className="h-2 rounded-full bg-[linear-gradient(90deg,#f4c95d,#ff8f70,#5bc0eb)]"
                style={{ width: `${Math.min(Number(signal.score || 0) * 100, 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
