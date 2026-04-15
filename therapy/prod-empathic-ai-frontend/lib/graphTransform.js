/**
 * Upsert incoming KG diff nodes/edges into the current frontend graph view model.
 *
 * Expected input:
 * - `graph` (`import('./dtos').GraphViewModel`)
 * - `kgDiff` (`import('./dtos').KgDiffPayload`)
 *
 * Expected output:
 * - `import('./dtos').GraphViewModel` with merged nodes/edges and updated metadata timestamp.
 *
 * Data contract notes:
 * - Node/edge identity should be stable by `id`.
 * - Must preserve existing UI metadata when a diff omits properties.
 *
 * Purpose:
 * - Apply incremental backend graph updates on the client.
 */
export function mergeKgDiffIntoGraph(graph, kgDiff) {
    if (!kgDiff) return graph;

    // convert existing arrays to Maps w/ id for O(1) lookups
    const nodeMap = new Map((graph.nodes || []).map((n) => [n.id, n]));
    const edgeMap = new Map((graph.edges || []).map((e) => [e.id, e]));

    // update/insert incoming nodes
    if (Array.isArray(kgDiff.nodes_upsert)) {
        for (const incomingNode of kgDiff.nodes_upsert) {
            const existingNode = nodeMap.get(incomingNode.id) || {};
            // incomingNode overwrites existingNode fields; missing fields preserved
            nodeMap.set(incomingNode.id, { ...existingNode, ...incomingNode });
        }
    }

    // update/insert incoming edges
    if (Array.isArray(kgDiff.edges_upsert)) {
        for (const incomingEdge of kgDiff.edges_upsert) {
            const existingEdge = edgeMap.get(incomingEdge.id) || {};
            edgeMap.set(incomingEdge.id, { ...existingEdge, ...incomingEdge });
        }
    }

    // new object (immutability) so React re-renders
    return {
        nodes: Array.from(nodeMap.values()),
        edges: Array.from(edgeMap.values()),
        metadata: {
            updatedAtMs: Date.now(),
        },
    };
}

/**
 * Convert raw prosody score maps into sorted display rows.
 *
 * Expected input:
 * - `prosodyScores` (`Record<string, number> | null`)
 * - `limit` (`number`, optional)
 *
 * Expected output:
 * - `import('./dtos').ProsodySignal[]`
 *
 * Purpose:
 * - Transform EVI score dictionaries into panel-friendly arrays.
 */
export function prosodyScoresToSignals(prosodyScores, limit) {
    if (!prosodyScores || typeof prosodyScores !== "object") {
        return [];
    }

    // convert prosodyScores into array of emotions
    const signals = Object.entries(prosodyScores).map(([label, score]) => ({
        label,
        score,
    }));

    // sort strongest emotions at top
    signals.sort((a, b) => b.score - a.score);

    // limit to "top X" emotions
    if (typeof limit === "number" && limit > 0) {
        return signals.slice(0, limit);
    }

    return signals;
}

/**
 * Build graph highlight IDs from a selected receipt.
 *
 * Expected input:
 * - `receipts` (`import('./dtos').Receipt[]`)
 * - `selectedReceiptId` (`string | null`)
 *
 * Expected output:
 * - `{ highlightNodeIds: string[], highlightEdgeIds: string[] }`
 *
 * Purpose:
 * - Support cross-panel linking between receipts and graph visualization.
 */
export function buildReceiptGraphHighlights(receipts, selectedReceiptId) {
    const defaultHighlights = { highlightNodeIds: [], highlightEdgeIds: [] };

    if (!selectedReceiptId || !Array.isArray(receipts)) {
        return defaultHighlights;
    }

    const activeReceipt = receipts.find((r) => r.receiptId === selectedReceiptId);

    if (!activeReceipt) {
        return defaultHighlights;
    }

    // return arrays of user-highlighted nodes/edges
    return {
        highlightNodeIds: Array.isArray(activeReceipt.nodeIds) ? activeReceipt.nodeIds : [],
        highlightEdgeIds: Array.isArray(activeReceipt.edgeIds) ? activeReceipt.edgeIds : [],
    };
}