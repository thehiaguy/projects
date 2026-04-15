"use client";

function InsightCard({ title, body, accent }) {
  return (
    <div className={`rounded-3xl border px-4 py-4 ${accent}`}>
      <p className="text-[0.68rem] uppercase tracking-[0.26em] opacity-70">{title}</p>
      <p className="mt-3 text-sm leading-6">{body}</p>
    </div>
  );
}

export default function ReceiptsPanel({
  receipts = [],
  selectedReceiptId = null,
  onSelectReceipt,
  summaryPartial,
  insightCard,
  safetySignal,
  endSummary,
  topConcepts = [],
}) {
  return (
    <section className="rounded-[2rem] border border-slate-200/80 bg-white/88 p-5 shadow-[0_20px_45px_rgba(15,23,42,0.08)]">
      <div>
        <p className="text-xs uppercase tracking-[0.32em] text-slate-500">Session outputs</p>
        <h3 className="mt-2 text-xl font-semibold text-slate-900">Receipts and guidance</h3>
      </div>

      <div className="mt-5 space-y-3">
        {summaryPartial?.summary ? (
          <InsightCard
            title="Rolling Summary"
            body={summaryPartial.summary}
            accent="border-sky-200 bg-sky-50 text-sky-900"
          />
        ) : null}

        {insightCard?.reflection || insightCard?.question ? (
          <InsightCard
            title="Coach Insight"
            body={[insightCard?.reflection, insightCard?.question].filter(Boolean).join(" ")}
            accent="border-violet-200 bg-violet-50 text-violet-900"
          />
        ) : null}

        {safetySignal?.risk_level ? (
          <InsightCard
            title={`Safety ${safetySignal.risk_level}`}
            body={safetySignal?.rationale ?? "No rationale provided."}
            accent="border-amber-200 bg-amber-50 text-amber-900"
          />
        ) : null}

        {endSummary ? (
          <InsightCard title="Ended Session Summary" body={endSummary} accent="border-emerald-200 bg-emerald-50 text-emerald-900" />
        ) : null}
      </div>

      {topConcepts.length > 0 ? (
        <div className="mt-5 rounded-3xl border border-slate-200 bg-slate-50 px-4 py-4">
          <p className="text-[0.68rem] uppercase tracking-[0.26em] text-slate-500">Top Concepts</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {topConcepts.map((concept) => (
              <span key={`${concept.label}:${concept.canonical}`} className="rounded-full bg-white px-3 py-1 text-sm text-slate-700">
                {concept.label}: {concept.canonical}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      <div className="mt-5">
        <p className="text-xs uppercase tracking-[0.26em] text-slate-500">Receipts</p>
        <div className="mt-3 max-h-[22rem] space-y-2 overflow-y-auto pr-1">
          {receipts.length === 0 ? (
            <div className="rounded-3xl border border-dashed border-slate-200 px-4 py-6 text-sm text-slate-500">
              Backend receipts will appear here as KG updates are applied.
            </div>
          ) : null}

          {receipts.map((receipt) => {
            const isSelected = receipt.receiptId === selectedReceiptId;

            return (
              <button
                key={receipt.receiptId}
                type="button"
                onClick={() => onSelectReceipt?.(isSelected ? null : receipt.receiptId)}
                className={`w-full rounded-3xl border px-4 py-4 text-left transition ${
                  isSelected ? "border-slate-900 bg-slate-900 text-white" : "border-slate-200 bg-slate-50 text-slate-900"
                }`}
              >
                <p className="text-[0.68rem] uppercase tracking-[0.24em] opacity-70">{receipt.toolName}</p>
                <p className="mt-2 text-sm font-semibold">{receipt.receiptId}</p>
                {receipt.evidence?.quote ? (
                  <p className="mt-2 text-sm opacity-80">&quot;{receipt.evidence.quote}&quot;</p>
                ) : null}
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}
