"use client";

import { useCallback, useMemo, useReducer } from "react";

function getNodeKey(node) {
  return (
    node?.id ??
    node?.node_id ??
    [node?.label, node?.canonical, node?.sessionId ?? node?.session_id]
      .filter(Boolean)
      .join(":")
  );
}

function getEdgeKey(edge) {
  return (
    edge?.id ??
    edge?.edge_id ??
    [
      edge?.type,
      edge?.source ?? edge?.source_id ?? edge?.from,
      edge?.target ?? edge?.target_id ?? edge?.to,
    ]
      .filter(Boolean)
      .join(":")
  );
}

function getReceiptKey(receipt) {
  return receipt?.receipt_id ?? receipt?.receiptId ?? receipt?.message_id ?? receipt?.messageId ?? null;
}

function upsertItems(items, keySelector) {
  const orderedKeys = [];
  const itemMap = new Map();

  items.forEach((item) => {
    const key = keySelector(item);

    if (!key) {
      return;
    }

    if (!itemMap.has(key)) {
      orderedKeys.push(key);
    }

    itemMap.set(key, {
      ...(itemMap.get(key) ?? {}),
      ...item,
    });
  });

  return orderedKeys.map((key) => itemMap.get(key));
}

function mergeItems(currentItems, nextItems, keySelector) {
  return upsertItems([...currentItems, ...nextItems], keySelector);
}

function mergeWarnings(currentWarnings, nextWarnings) {
  return Array.from(new Set([...(currentWarnings ?? []), ...(nextWarnings ?? [])].filter(Boolean)));
}

function readPayloadWarnings(payload) {
  return payload?.warnings ?? [];
}

function readPayloadReceipts(payload) {
  return payload?.receipts ?? [];
}

function readPayloadNodes(payload) {
  return payload?.nodes_upsert ?? payload?.nodesUpsert ?? payload?.nodes ?? [];
}

function readPayloadEdges(payload) {
  return payload?.edges_upsert ?? payload?.edgesUpsert ?? payload?.edges ?? [];
}

function inferGraphUnavailable(payload) {
  const code = String(payload?.code ?? "").toLowerCase();
  const message = String(payload?.message ?? "").toLowerCase();
  const subsystem = String(payload?.details?.subsystem ?? "").toLowerCase();

  return (
    code.includes("graph") ||
    code.includes("neo4j") ||
    message.includes("graph") ||
    message.includes("neo4j") ||
    subsystem === "graph" ||
    subsystem === "neo4j"
  );
}

function createInitialState() {
  return {
    nodes: [],
    edges: [],
    receipts: [],
    warnings: [],
    highlightedNodeIds: [],
    toolCalls: [],
    droppedToolCalls: [],
    insightCard: null,
    safetySignal: null,
    summaryPartial: null,
    lastEnvelope: null,
    lastServerError: null,
    graphUnavailable: false,
    updatedAt: null,
  };
}

function graphStateReducer(state, action) {
  switch (action.type) {
    case "RESET":
      return createInitialState();

    case "APPLY_SNAPSHOT":
      return {
        ...state,
        nodes: upsertItems(readPayloadNodes(action.payload), getNodeKey),
        edges: upsertItems(readPayloadEdges(action.payload), getEdgeKey),
        warnings: mergeWarnings(state.warnings, readPayloadWarnings(action.payload)),
        graphUnavailable: false,
        updatedAt: Date.now(),
      };

    case "APPLY_KG_DIFF": {
      const receipts = readPayloadReceipts(action.payload);
      const highlightedNodeIds = Array.from(
        new Set(
          receipts.flatMap((receipt) => receipt?.applied_node_ids ?? receipt?.appliedNodeIds ?? []),
        ),
      );

      return {
        ...state,
        nodes: mergeItems(state.nodes, readPayloadNodes(action.payload), getNodeKey),
        edges: mergeItems(state.edges, readPayloadEdges(action.payload), getEdgeKey),
        receipts: mergeItems(state.receipts, receipts, getReceiptKey).slice(-action.maxReceipts),
        warnings: mergeWarnings(state.warnings, readPayloadWarnings(action.payload)),
        highlightedNodeIds,
        graphUnavailable: false,
        updatedAt: Date.now(),
      };
    }

    case "APPLY_TOOL_CALLS":
      return {
        ...state,
        toolCalls: action.payload?.calls ?? [],
        droppedToolCalls: action.payload?.dropped_calls ?? action.payload?.droppedCalls ?? [],
        updatedAt: Date.now(),
      };

    case "APPLY_INSIGHT":
      return {
        ...state,
        insightCard: action.payload?.card ?? action.payload ?? null,
        receipts: mergeItems(state.receipts, readPayloadReceipts(action.payload), getReceiptKey).slice(
          -action.maxReceipts,
        ),
        updatedAt: Date.now(),
      };

    case "APPLY_SAFETY":
      return {
        ...state,
        safetySignal: action.payload,
        updatedAt: Date.now(),
      };

    case "APPLY_SUMMARY":
      return {
        ...state,
        summaryPartial: action.payload,
        updatedAt: Date.now(),
      };

    case "APPLY_ERROR":
      return {
        ...state,
        lastServerError: action.payload,
        graphUnavailable: inferGraphUnavailable(action.payload) || state.graphUnavailable,
        updatedAt: Date.now(),
      };

    case "SET_LAST_ENVELOPE":
      return {
        ...state,
        lastEnvelope: action.payload,
      };

    default:
      return state;
  }
}

/**
 * Holds the frontend graph projection and applies backend envelopes incrementally.
 *
 * Behavior derived from the context docs:
 * - apply graph snapshots fetched from REST
 * - apply incremental kg.diff payloads from the backend WebSocket
 * - retain receipts, tool-call metadata, insight cards, and safety signals
 */
export function useGraphState(options = {}) {
  const { maxReceipts = 100 } = options;
  const [state, dispatch] = useReducer(graphStateReducer, undefined, createInitialState);

  const resetGraphState = useCallback(() => {
    dispatch({ type: "RESET" });
  }, []);

  const applyGraphSnapshot = useCallback((payload) => {
    dispatch({ type: "APPLY_SNAPSHOT", payload });
  }, []);

  const applyKgDiff = useCallback(
    (payload) => {
      dispatch({ type: "APPLY_KG_DIFF", payload, maxReceipts });
    },
    [maxReceipts],
  );

  const applyEnvelope = useCallback(
    (envelope) => {
      if (!envelope?.type) {
        return false;
      }

      dispatch({ type: "SET_LAST_ENVELOPE", payload: envelope });

      switch (envelope.type) {
        case "kg.diff":
          dispatch({ type: "APPLY_KG_DIFF", payload: envelope.payload, maxReceipts });
          return true;

        case "kg.tool_calls_applied":
          dispatch({ type: "APPLY_TOOL_CALLS", payload: envelope.payload });
          return true;

        case "coach.insight":
          dispatch({ type: "APPLY_INSIGHT", payload: envelope.payload, maxReceipts });
          return true;

        case "summary.partial":
          dispatch({ type: "APPLY_SUMMARY", payload: envelope.payload });
          return true;

        case "safety.alert":
        case "safety.status":
          dispatch({ type: "APPLY_SAFETY", payload: envelope.payload });
          return true;

        case "server.error":
          dispatch({ type: "APPLY_ERROR", payload: envelope.payload });
          return true;

        default:
          return false;
      }
    },
    [maxReceipts],
  );

  return useMemo(
    () => ({
      ...state,
      graph: {
        nodes: state.nodes,
        edges: state.edges,
      },
      resetGraphState,
      applyGraphSnapshot,
      applyKgDiff,
      applyEnvelope,
    }),
    [applyEnvelope, applyGraphSnapshot, applyKgDiff, resetGraphState, state],
  );
}

export default useGraphState;
