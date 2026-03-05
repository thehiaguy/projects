"use client";

import { useCallback, useRef, useState } from "react";
import type { KgNode, KgEdge, KgDiffPayload, GraphData, ForceNode, ForceLink } from "@/lib/types";

export function useGraphState() {
  const nodesMap = useRef<Map<string, KgNode>>(new Map());
  const edgesMap = useRef<Map<string, KgEdge>>(new Map());
  // Track newly upserted node IDs for flash animation
  const newNodeIds = useRef<Set<string>>(new Set());

  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });

  const buildGraphData = useCallback((): GraphData => {
    const nodes: ForceNode[] = Array.from(nodesMap.current.values()).map((n) => ({
      ...n,
      isNew: newNodeIds.current.has(n.id),
    }));
    const links: ForceLink[] = Array.from(edgesMap.current.values()).map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      type: e.type,
    }));
    return { nodes, links };
  }, []);

  const applyDiff = useCallback((diff: KgDiffPayload) => {
    newNodeIds.current.clear();

    for (const node of diff.nodes_upsert) {
      const isNew = !nodesMap.current.has(node.id);
      nodesMap.current.set(node.id, node);
      if (isNew) newNodeIds.current.add(node.id);
    }
    for (const edge of diff.edges_upsert) {
      edgesMap.current.set(edge.id, edge);
    }

    setGraphData(buildGraphData());

    // Clear the "new" flags after 2s so flash animation ends
    if (newNodeIds.current.size > 0) {
      const ids = new Set(newNodeIds.current);
      setTimeout(() => {
        ids.forEach((id) => newNodeIds.current.delete(id));
        // No need to re-render here; next diff will rebuild
      }, 2000);
    }
  }, [buildGraphData]);

  const resetGraph = useCallback(() => {
    nodesMap.current.clear();
    edgesMap.current.clear();
    newNodeIds.current.clear();
    setGraphData({ nodes: [], links: [] });
  }, []);

  return { graphData, applyDiff, resetGraph };
}
