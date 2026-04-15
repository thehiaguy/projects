export class ApiClientError extends Error {
  constructor(message, status = null, code = null, details = null) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function trimTrailingSlash(value) {
  return String(value ?? "").replace(/\/+$/, "");
}

function buildUrl(baseUrl, path) {
  const normalizedBaseUrl = trimTrailingSlash(baseUrl);
  const normalizedPath = String(path ?? "").replace(/^\/+/, "");
  return `${normalizedBaseUrl}/${normalizedPath}`;
}

async function parseJsonBody(response) {
  const rawText = await response.text();

  if (!rawText) {
    return null;
  }

  try {
    return JSON.parse(rawText);
  } catch {
    throw new ApiClientError("The backend returned a non-JSON response.", response.status, null, rawText);
  }
}

function toCamelGraphNode(node) {
  return {
    ...node,
    id: node?.id ?? node?.node_id ?? null,
    label: node?.label ?? "",
    canonical: node?.canonical ?? "",
    properties: node?.properties ?? {},
  };
}

function toCamelGraphEdge(edge) {
  return {
    ...edge,
    id: edge?.id ?? edge?.edge_id ?? null,
    type: edge?.type ?? "",
    sourceId: edge?.sourceId ?? edge?.source_id ?? edge?.source ?? null,
    targetId: edge?.targetId ?? edge?.target_id ?? edge?.target ?? null,
    properties: edge?.properties ?? {},
  };
}

function toCamelReceipt(receipt) {
  return {
    ...receipt,
    receiptId: receipt?.receiptId ?? receipt?.receipt_id ?? receipt?.message_id ?? null,
    toolName: receipt?.toolName ?? receipt?.tool_name ?? "graph_update",
    evidence: receipt?.evidence ?? null,
    nodeIds:
      receipt?.nodeIds ??
      receipt?.node_ids ??
      receipt?.applied_node_ids ??
      receipt?.appliedNodeIds ??
      [],
    edgeIds:
      receipt?.edgeIds ??
      receipt?.edge_ids ??
      receipt?.applied_edge_ids ??
      receipt?.appliedEdgeIds ??
      [],
    arguments: receipt?.arguments ?? {},
    appliedAtMs: receipt?.appliedAtMs ?? receipt?.applied_at_ms ?? null,
  };
}

function normalizeSessionResponse(payload) {
  return {
    ...payload,
    sessionId: payload?.sessionId ?? payload?.session_id ?? null,
    sessionToken: payload?.sessionToken ?? payload?.session_token ?? null,
    createdAtMs: payload?.createdAtMs ?? payload?.created_at_ms ?? null,
    endedAtMs: payload?.endedAtMs ?? payload?.ended_at_ms ?? null,
  };
}

function normalizeAccessTokenResponse(payload) {
  const accessToken = payload?.accessToken ?? payload?.access_token ?? null;
  const expiresIn = payload?.expiresIn ?? payload?.expires_in ?? null;

  return {
    ...payload,
    accessToken,
    expiresIn,
    expiresAtMs: typeof expiresIn === "number" ? Date.now() + expiresIn * 1000 : null,
  };
}

function normalizeGraphSnapshot(payload) {
  return {
    nodes: Array.isArray(payload?.nodes) ? payload.nodes.map(toCamelGraphNode).filter((node) => node.id) : [],
    edges: Array.isArray(payload?.edges) ? payload.edges.map(toCamelGraphEdge).filter((edge) => edge.id) : [],
  };
}

function normalizeEndSessionResponse(payload) {
  return {
    ...payload,
    summary: payload?.summary ?? "",
    topConcepts: payload?.topConcepts ?? payload?.top_concepts ?? [],
  };
}

export async function requestJson({ baseUrl, path, method = "GET", body, headers = {} }) {
  const response = await fetch(buildUrl(baseUrl, path), {
    method,
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });

  const payload = await parseJsonBody(response);

  if (!response.ok) {
    throw new ApiClientError(
      payload?.message ?? payload?.detail ?? `Backend request failed with ${response.status}.`,
      response.status,
      payload?.code ?? null,
      payload,
    );
  }

  return payload;
}

export async function createSession({ baseUrl }) {
  const payload = await requestJson({
    baseUrl,
    path: "/v1/sessions",
    method: "POST",
  });

  const normalizedPayload = normalizeSessionResponse(payload);

  if (!normalizedPayload.sessionId || !normalizedPayload.sessionToken) {
    throw new ApiClientError("The backend session response is missing the session identifier or token.", 500, null, payload);
  }

  return normalizedPayload;
}

export async function getHumeAccessToken({ baseUrl }) {
  const payload = await requestJson({
    baseUrl,
    path: "/v1/hume/access-token",
    method: "POST",
  });

  const normalizedPayload = normalizeAccessTokenResponse(payload);

  if (!normalizedPayload.accessToken) {
    throw new ApiClientError("The backend token response did not include a Hume access token.", 500, null, payload);
  }

  return normalizedPayload;
}

export async function getSessionGraphSnapshot({ baseUrl, sessionId, limitNodes, limitEdges }) {
  const searchParams = new URLSearchParams();

  if (typeof limitNodes === "number") {
    searchParams.set("limit_nodes", String(limitNodes));
  }

  if (typeof limitEdges === "number") {
    searchParams.set("limit_edges", String(limitEdges));
  }

  const path = `/v1/sessions/${encodeURIComponent(sessionId)}/graph${
    searchParams.size > 0 ? `?${searchParams.toString()}` : ""
  }`;

  const payload = await requestJson({
    baseUrl,
    path,
    method: "GET",
  });

  return normalizeGraphSnapshot(payload);
}

export async function endSession({ baseUrl, sessionId }) {
  const payload = await requestJson({
    baseUrl,
    path: `/v1/sessions/${encodeURIComponent(sessionId)}/end`,
    method: "POST",
  });

  return normalizeEndSessionResponse(payload);
}

export function normalizeBackendEnvelope(envelope) {
  if (!envelope || typeof envelope !== "object") {
    return envelope;
  }

  return {
    ...envelope,
    payload: {
      ...envelope.payload,
      nodes_upsert: Array.isArray(envelope?.payload?.nodes_upsert)
        ? envelope.payload.nodes_upsert.map(toCamelGraphNode)
        : envelope?.payload?.nodesUpsert?.map?.(toCamelGraphNode) ?? envelope?.payload?.nodes ?? [],
      edges_upsert: Array.isArray(envelope?.payload?.edges_upsert)
        ? envelope.payload.edges_upsert.map(toCamelGraphEdge)
        : envelope?.payload?.edgesUpsert?.map?.(toCamelGraphEdge) ?? envelope?.payload?.edges ?? [],
      receipts: Array.isArray(envelope?.payload?.receipts)
        ? envelope.payload.receipts.map(toCamelReceipt)
        : [],
    },
  };
}
