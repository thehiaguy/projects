"use client";

function highlightClass(isHighlighted) {
  return isHighlighted ? "border-[#f4c95d] bg-[#fff6db]" : "border-slate-200 bg-slate-50";
}

export default function GraphPanel({
  graph = { nodes: [], edges: [] },
  highlightedNodeIds = [],
  highlightedEdgeIds = [],
  graphUnavailable = false,
}) {
  const nodeIdSet = new Set(highlightedNodeIds);
  const edgeIdSet = new Set(highlightedEdgeIds);

  return (
    <section className="rounded-[2rem] border border-slate-200/80 bg-white/88 p-5 shadow-[0_20px_45px_rgba(15,23,42,0.08)]">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.32em] text-slate-500">Knowledge graph</p>
          <h3 className="mt-2 text-xl font-semibold text-slate-900">Live concepts</h3>
        </div>
        <p className="text-sm text-slate-500">
          {graph.nodes.length} nodes / {graph.edges.length} edges
        </p>
      </div>

      {graphUnavailable ? (
        <div className="mt-5 rounded-3xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
          The backend reported that the graph subsystem is unavailable. Transcript and prosody can still run.
        </div>
      ) : null}

      <div className="mt-5 grid gap-4 xl:grid-cols-2">
        <div>
          <p className="text-xs uppercase tracking-[0.26em] text-slate-500">Nodes</p>
          <div className="mt-3 max-h-[18rem] space-y-2 overflow-y-auto pr-1">
            {graph.nodes.length === 0 ? (
              <div className="rounded-3xl border border-dashed border-slate-200 px-4 py-6 text-sm text-slate-500">
                No graph nodes yet.
              </div>
            ) : null}
            {graph.nodes.map((node) => (
              <div
                key={node.id}
                className={`rounded-3xl border px-4 py-3 ${highlightClass(nodeIdSet.has(node.id))}`}
              >
                <p className="text-[0.68rem] uppercase tracking-[0.24em] text-slate-500">{node.label}</p>
                <p className="mt-2 text-sm font-semibold text-slate-900">{node.canonical}</p>
              </div>
            ))}
          </div>
        </div>

        <div>
          <p className="text-xs uppercase tracking-[0.26em] text-slate-500">Edges</p>
          <div className="mt-3 max-h-[18rem] space-y-2 overflow-y-auto pr-1">
            {graph.edges.length === 0 ? (
              <div className="rounded-3xl border border-dashed border-slate-200 px-4 py-6 text-sm text-slate-500">
                No graph edges yet.
              </div>
            ) : null}
            {graph.edges.map((edge) => (
              <div
                key={edge.id}
                className={`rounded-3xl border px-4 py-3 ${highlightClass(edgeIdSet.has(edge.id))}`}
              >
                <p className="text-[0.68rem] uppercase tracking-[0.24em] text-slate-500">{edge.type}</p>
                <p className="mt-2 text-sm text-slate-700">
                  {edge.sourceId} → {edge.targetId}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
