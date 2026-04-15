/**
 * Frontend DTOs and type contracts (JSDoc module).
 *
 * This file intentionally centralizes data-shape definitions for:
 * - REST responses from FastAPI
 * - WebSocket packet envelopes (browser <-> backend)
 * - Normalized Hume EVI events used by the frontend
 * - View models consumed by UI components
 *
 * Implementers should keep this file synchronized with backend Pydantic models and shared schemas.
 */

/**
 * @typedef {'idle'|'connecting'|'connected'|'reconnecting'|'disconnected'|'error'} SocketStatus
 */

/**
 * @typedef {'idle'|'connecting'|'connected'|'disconnecting'|'error'} VoiceConnectionState
 */

/**
 * @typedef {'neutral'|'success'|'warning'|'danger'} BadgeTone
 */

/**
 * @typedef {Object} CreateSessionResponse
 * @property {string} sessionId
 */

/**
 * @typedef {Object} HumeAccessTokenResponse
 * @property {string} accessToken
 * @property {number} expiresIn
 * @property {number=} expiresAtMs
 */

/**
 * @typedef {Object} EndSessionResponse
 * @property {string} summary
 * @property {Array<{label: string, canonical: string, count?: number}>} topConcepts
 */

/**
 * @typedef {Record<string, number>} ProsodyScores
 */

/**
 * @typedef {Object} ProsodySignal
 * @property {string} label
 * @property {number} score
 * @property {string=} source
 */

/**
 * @typedef {Object} TranscriptEntry
 * @property {string} messageId
 * @property {'user'|'assistant'} role
 * @property {string} text
 * @property {boolean} interim
 * @property {number | null} timestampMs
 * @property {ProsodyScores | null=} prosodyScores
 */

/**
 * @typedef {Object} EviNormalizedEvent
 * @property {'user_message'|'assistant_message'|'chat_metadata'|'audio_output'|'unknown'} kind
 * @property {string | null} messageId
 * @property {'user'|'assistant'|null} role
 * @property {string | null} content
 * @property {boolean} interim
 * @property {ProsodyScores | null} prosodyScores
 * @property {number | null} timestampMs
 * @property {unknown=} raw
 */

/**
 * @typedef {Object} BuildEviConnectionConfigParams
 * @property {string} accessToken
 * @property {string=} humeConfigId
 * @property {boolean} verboseTranscription
 * @property {string} sessionId
 */

/**
 * @typedef {Object} WsEnvelope
 * @property {string} type
 * @property {string} session_id
 * @property {number} sent_at_ms
 * @property {Record<string, unknown>} payload
 */

/**
 * @typedef {Object} KgNode
 * @property {string} id
 * @property {string} label
 * @property {string} canonical
 * @property {string} sessionId
 * @property {Record<string, unknown>=} properties
 * @property {number | null=} lastSeenAt
 */

/**
 * @typedef {Object} KgEdge
 * @property {string} id
 * @property {string} type
 * @property {string} sourceId
 * @property {string} targetId
 * @property {string} sessionId
 * @property {Record<string, unknown>=} properties
 * @property {number | null=} lastSeenAt
 */

/**
 * @typedef {Object} ReceiptEvidence
 * @property {string} messageId
 * @property {string} quote
 * @property {boolean=} verified
 */

/**
 * @typedef {Object} Receipt
 * @property {string} receiptId
 * @property {string} toolName
 * @property {ReceiptEvidence | null} evidence
 * @property {Array<string>=} nodeIds
 * @property {Array<string>=} edgeIds
 * @property {Record<string, unknown>=} arguments
 * @property {number | null=} appliedAtMs
 */

/**
 * @typedef {Object} KgDiffPayload
 * @property {KgNode[]} nodes_upsert
 * @property {KgEdge[]} edges_upsert
 * @property {Receipt[]} receipts
 */

/**
 * @typedef {Object} GraphSnapshotResponse
 * @property {KgNode[]} nodes
 * @property {KgEdge[]} edges
 */

/**
 * @typedef {WsEnvelope} BackendClientPacket
 */

/**
 * @typedef {WsEnvelope} BackendServerPacket
 */

/**
 * @typedef {Object} GraphViewModel
 * @property {KgNode[]} nodes
 * @property {KgEdge[]} edges
 * @property {{updatedAtMs: number | null}} metadata
 */

/**
 * @typedef {Object} GraphRenderModel
 * @property {Array<Record<string, unknown>>} nodes
 * @property {Array<Record<string, unknown>>} edges
 * @property {{highlightNodeIds: string[], highlightEdgeIds: string[]}} highlights
 * @property {Array<{id: string, label: string, canonical: string}>} fallbackRows
 */

/**
 * @typedef {Object} ReceiptListItemViewModel
 * @property {string} receiptId
 * @property {string} summary
 * @property {string | null} evidenceQuote
 * @property {boolean} isVerified
 * @property {string[]} highlightNodeIds
 * @property {string[]} highlightEdgeIds
 */

/**
 * @typedef {Object} ConnectionStatusViewModel
 * @property {SocketStatus} backend
 * @property {VoiceConnectionState | SocketStatus} evi
 * @property {string | null} lastError
 */

/**
 * @typedef {Object} ConnectionStatusBadgeModel
 * @property {string} label
 * @property {BadgeTone} tone
 */

/**
 * @typedef {Object} SocketStatusTransition
 * @property {SocketStatus} nextStatus
 * @property {number=} reasonCode
 * @property {string=} userMessage
 */

/**
 * @typedef {Object} FrontendRuntimeConfig
 * @property {string} apiBaseUrl
 * @property {string} wsBaseUrl
 * @property {string} appName
 * @property {boolean} verboseTranscriptionEnabled
 */

/**
 * @typedef {Object} UseBackendSocketParams
 * @property {string | null} sessionId
 * @property {string} wsBaseUrl
 * @property {boolean} enabled
 * @property {(packet: BackendServerPacket) => void=} onPacket
 * @property {(status: SocketStatus) => void=} onStatusChange
 */

/**
 * @typedef {Object} UseBackendSocketResult
 * @property {SocketStatus} status
 * @property {string | null} lastError
 * @property {React.MutableRefObject<WebSocket | null>=} socketRef
 * @property {(packet: BackendClientPacket) => void} sendPacket
 * @property {() => void} reconnect
 * @property {() => void} disconnect
 */

/**
 * @typedef {Object} UseEviEventForwarderParams
 * @property {string | null} sessionId
 * @property {unknown} eviEventStream
 * @property {(packet: BackendClientPacket) => void} sendBackendPacket
 * @property {boolean} enabled
 * @property {number=} debounceMs
 */

/**
 * @typedef {Object} UseEviEventForwarderResult
 * @property {number} forwardedCount
 * @property {number} droppedCount
 * @property {string | null} lastForwardedMessageId
 * @property {string | null} lastError
 */

/**
 * @typedef {Object} GraphSessionState
 * @property {GraphViewModel} graph
 * @property {Receipt[]} receipts
 * @property {string | null} selectedReceiptId
 * @property {string | null} lastError
 */

/**
 * @typedef {Object} GraphStateAction
 * @property {string} type
 * @property {BackendServerPacket=} packet
 * @property {string | null=} receiptId
 */

/**
 * @typedef {Object} UseGraphStateParams
 * @property {string} sessionId
 * @property {GraphSnapshotResponse=} initialSnapshot
 * @property {(error: string) => void=} onGraphError
 */

/**
 * @typedef {Object} UseGraphStateResult
 * @property {GraphViewModel} graph
 * @property {Receipt[]} receipts
 * @property {string | null} selectedReceiptId
 * @property {(packet: BackendServerPacket) => void} dispatchPacket
 * @property {(receiptId: string | null) => void} selectReceipt
 * @property {() => void} reset
 */

/**
 * @typedef {Object} UseSessionParams
 * @property {string} sessionId
 * @property {string} apiBaseUrl
 * @property {string} wsBaseUrl
 * @property {boolean} enableVerboseTranscription
 */

/**
 * @typedef {Object} UseSessionInternalState
 * @property {ConnectionStatusViewModel} connection
 * @property {TranscriptEntry[]} transcriptEntries
 * @property {ProsodySignal[]} prosodySignals
 * @property {GraphViewModel} graph
 * @property {Receipt[]} receipts
 * @property {string | null} selectedReceiptId
 */

/**
 * @typedef {Object} SessionPageViewModel
 * @property {string} sessionId
 * @property {ConnectionStatusViewModel} connection
 * @property {TranscriptEntry[]} transcriptEntries
 * @property {ProsodySignal[]} prosodySignals
 * @property {GraphViewModel} graph
 * @property {Receipt[]} receipts
 * @property {string | null} selectedReceiptId
 */

/**
 * Validate that a value conforms to the websocket envelope shape.
 *
 * Expected input:
 * - `value` (`unknown`)
 *
 * Expected output:
 * - `WsEnvelope`
 *
 * Purpose:
 * - Runtime contract guard for frontend/backend websocket packets.
 */
export function assertWsEnvelope(value) {
    if (!value || typeof value !== "object") {
        throw new Error("Invalid WsEnvelope: payload is not an object");
    }

    // check what required fields for WsEnvelope format are missing
    const missingFields = [];
    if (typeof value.type !== "string") missingFields.push("type");
    if (typeof value.session_id !== "string") missingFields.push("session_id");
    if (typeof value.sent_at_ms !== "number") missingFields.push("sent_at_ms");
    if (!value.payload || typeof value.payload !== "object") missingFields.push("payload");

    if (missingFields.length > 0) {
        throw new Error(`Invalid WsEnvelope. Missing or invalid fields: ${missingFields.join(", ")}`);
    }
    return value;
}

/**
 * Normalize a REST graph snapshot response into the frontend graph view model.
 *
 * Expected input:
 * - `snapshot` (`GraphSnapshotResponse`)
 *
 * Expected output:
 * - `GraphViewModel`
 *
 * Purpose:
 * - Provide a single normalization path for initial graph state hydration.
 */
export function normalizeGraphSnapshot(snapshot) {
  const safeSnapshot = snapshot || {};

  // guarentee arrays and inject frontend metadata
  return {
    nodes: Array.isArray(safeSnapshot.nodes) ? safeSnapshot.nodes : [],
    edges: Array.isArray(safeSnapshot.edges) ? safeSnapshot.edges : [],
    
    metadata: {
      updatedAtMs: Date.now(),
    },
  };
}