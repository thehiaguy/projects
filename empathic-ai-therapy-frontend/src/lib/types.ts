// ─── Knowledge Graph ────────────────────────────────────────────────────────

export type KgNodeLabel =
  | "Emotion"
  | "Trigger"
  | "Belief"
  | "Need"
  | "Goal"
  | "Action"
  | "Person"
  | "Event";

export interface KgNode {
  id: string;
  label: KgNodeLabel;
  canonical: string;
  properties: Record<string, unknown>;
}

export interface KgEdge {
  id: string;
  type: string;
  source: string;
  target: string;
  properties: Record<string, unknown>;
}

export interface KgReceipt {
  receipt_id: string;
  message_id: string;
  tool_name: string;
  evidence_quote: string;
  applied_node_ids: string[];
  applied_edge_ids: string[];
  verified: boolean;
  warnings: string[];
}

export interface KgDiffPayload {
  nodes_upsert: KgNode[];
  edges_upsert: KgEdge[];
  receipts: KgReceipt[];
  warnings: string[];
}

// ─── react-force-graph-2d ───────────────────────────────────────────────────

export interface ForceNode extends KgNode {
  // react-force-graph mutates these during simulation
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number;
  fy?: number;
  isNew?: boolean;
}

export interface ForceLink {
  id: string;
  source: string | ForceNode;
  target: string | ForceNode;
  type: string;
}

export interface GraphData {
  nodes: ForceNode[];
  links: ForceLink[];
}

// ─── WebSocket Envelopes ─────────────────────────────────────────────────────

export interface WsEnvelope {
  type: string;
  session_id: string;
  payload: Record<string, unknown>;
  sent_at_ms?: number;
  correlation_id?: string;
}

// Client → Server

export interface ClientPingEnvelope extends WsEnvelope {
  type: "client.ping";
  payload: Record<string, never>;
}

export interface EviUserMessageFinalPayload {
  message_id: string;
  content: string;
  role: "user";
  interim: boolean;
  prosody_scores: Record<string, number>;
  timestamp_ms: number;
}

export interface EviUserMessageFinalEnvelope extends WsEnvelope {
  type: "evi.user_message.final";
  payload: EviUserMessageFinalPayload;
}

export interface EviAssistantMessagePayload {
  message_id: string;
  content: string;
  role: "assistant";
}

export interface EviAssistantMessageEnvelope extends WsEnvelope {
  type: "evi.assistant_message";
  payload: EviAssistantMessagePayload;
}

// Server → Client

export interface ServerPongPayload {
  server_ts_ms: number;
}

export interface ServerErrorPayload {
  code: string;
  message: string;
  correlation_id: string | null;
  retryable: boolean;
  details: Record<string, unknown>;
}

export interface KgDiffEnvelope extends WsEnvelope {
  type: "kg.diff";
  payload: KgDiffPayload;
}

// ─── REST API Types ──────────────────────────────────────────────────────────

export interface CreateSessionResponse {
  session_id: string;
  created_at_ms: number;
  status: string;
}

export interface TopConcept {
  label: string;
  canonical: string;
  mention_count: number;
  score: number;
}

export interface EndSessionResponse {
  session_id: string;
  ended_at_ms: number;
  summary: string;
  top_concepts: TopConcept[];
}

export interface HumeTokenResponse {
  access_token: string;
  expires_in: number;
  token_type: string;
}

export interface GraphSnapshotResponse {
  nodes: KgNode[];
  edges: KgEdge[];
}

// ─── Transcript ──────────────────────────────────────────────────────────────

export type TranscriptRole = "user" | "assistant";

export interface TranscriptEntry {
  id: string;
  role: TranscriptRole;
  content: string;
  prosody_scores?: Record<string, number>;
  timestamp_ms: number;
  interim?: boolean;
}
