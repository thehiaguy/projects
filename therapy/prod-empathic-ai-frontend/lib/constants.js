/**
 * Canonical frontend packet types accepted/sent by the browser over the backend websocket.
 *
 * Purpose:
 * - Shared enum-like registry for runtime guards, reducers, and telemetry.
 */
export const WS_PACKET_TYPES = Object.freeze({
  EVI_USER_MESSAGE_FINAL: "evi.user_message.final",
  EVI_ASSISTANT_MESSAGE: "evi.assistant_message",
  EVI_CHAT_METADATA: "evi.chat_metadata",
  CLIENT_PING: "client.ping",
  KG_DIFF: "kg.diff",
  KG_TOOL_CALLS_APPLIED: "kg.tool_calls_applied",
  SUMMARY_PARTIAL: "summary.partial",
  SAFETY_SIGNAL: "safety.signal",
  SERVER_ERROR: "server.error",
});

/**
 * Allowed session-scoped concept labels expected in KG diffs and receipts.
 *
 * Purpose:
 * - Keep frontend graph styling/validation aligned with backend label contracts.
 */
export const KG_CONCEPT_LABELS = Object.freeze([
  "Person",
  "Trigger",
  "Emotion",
  "Belief",
  "Need",
  "Goal",
  "Action",
  "Event",
]);

/**
 * Resolve and validate frontend runtime configuration from public environment variables.
 *
 * Expected input:
 * - No direct arguments; reads `process.env.NEXT_PUBLIC_*`.
 *
 * Expected output:
 * - `import('./dtos').FrontendRuntimeConfig`
 *   `{ apiBaseUrl, wsBaseUrl, appName, verboseTranscriptionEnabled }`
 *
 * Data contract notes:
 * - Must throw a clear configuration error if required URLs are missing.
 * - Should parse boolean flags from strings safely (`"true"`, `"false"`).
 *
 * Purpose:
 * - Provide a single source of truth for browser runtime config.
 */
export function getFrontendRuntimeConfig() {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL;
  const wsBaseUrl = process.env.NEXT_PUBLIC_WS_URL;

  if (!apiBaseUrl) {
    throw new Error("Missing required environment variable: NEXT_PUBLIC_API_URL");
  }
  if (!wsBaseUrl) {
    throw new Error("Missing required environment variable: NEXT_PUBLIC_WS_URL");
  }

  return {
    apiBaseUrl,
    wsBaseUrl,
    appName: process.env.NEXT_PUBLIC_APP_NAME || "Empathic AI Therapy",
    verboseTranscriptionEnabled: process.env.NEXT_PUBLIC_VERBOSE_TRANSCRIPTION === "true",
  };
}

/**
 * Check whether a packet type should affect graph topology/receipts state.
 *
 * Expected input:
 * - `packetType` (`string`)
 *
 * Expected output:
 * - `boolean`
 *
 * Purpose:
 * - Let reducers/hooks ignore non-graph websocket packets efficiently.
 */
export function isGraphAffectingPacketType(packetType) {
  // these ws packets force Graph/Receipts UI to re-render:
  const graphAffectingTypes = [
    WS_PACKET_TYPES.KG_DIFF,
    WS_PACKET_TYPES.KG_TOOL_CALLS_APPLIED,
  ];

  return graphAffectingTypes.includes(packetType);
}