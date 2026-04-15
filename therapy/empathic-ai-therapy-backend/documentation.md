# Backend API Documentation

This document describes the current backend contract implemented in `apps/api`.

It is written for the frontend application and focuses on:

- the expected request and response shapes
- the order the frontend should call the backend
- the websocket message protocol
- what is implemented now versus what is still future work

## Base Runtime

- HTTP base URL: whatever host/port the FastAPI app is running on
  - local example: `http://127.0.0.1:8000`
- WebSocket base URL: same backend host using `ws://` or `wss://`
  - local example: `ws://127.0.0.1:8000/ws/session/{session_id}`

## Recommended Frontend Flow

1. Call `POST /v1/sessions`
2. Save the returned `session_id` and `session_token`
3. Call `POST /v1/hume/access-token`
4. Open the Hume EVI websocket directly from the browser using that token
5. Open `WS /ws/session/{session_id}?session_token=...` to the backend
6. Forward finalized Hume user transcript events as `evi.user_message.final`
7. Optionally forward assistant transcript events as `evi.assistant_message`
8. Listen for `kg.diff`, `kg.tool_calls_applied`, `summary.partial`, `coach.insight`, and `safety.status` / `safety.alert`
9. Use `GET /v1/sessions/{session_id}/graph` for reconnect/recovery
10. Optionally use `POST /v1/sessions/{session_id}/audio-window` for windowed fallback mode
11. Call `POST /v1/sessions/{session_id}/end` when the session ends

## Error Shape

REST errors are typically returned as:

```json
{
  "detail": {
    "code": "session_not_found",
    "message": "Session session-abc was not found.",
    "correlation_id": null
  }
}
```

WebSocket errors are returned inside the websocket envelope as `server.error`.

## REST Routes

### `GET /v1/health`

Purpose:
- minimal liveness/readiness check

Request:
- no body

Response:

```json
{
  "ok": true
}
```

Frontend usage:
- optional startup health check
- not required for session flow

### `POST /v1/sessions`

Purpose:
- create a new session record in Neo4j

Request:
- no body required

Current response:

```json
{
  "session_id": "session-123456abcdef",
  "created_at_ms": 1772326000000,
  "ended_at_ms": null,
  "status": null,
  "metadata": {},
  "session_token": "..."
}
```

Response fields:
- `session_id: string`
- `created_at_ms: number`
- `ended_at_ms: number | null`
- `status: string | null`
- `metadata: object`
- `session_token: string | null`

Frontend usage:
- call once at the beginning of a conversation
- store `session_id`
- store `session_token`
- use `session_id` for:
  - Hume-associated frontend state
  - backend websocket URL
  - graph snapshot route
  - end-session route
- use `session_token` for:
  - backend websocket authentication

### `POST /v1/hume/access-token`

Purpose:
- fetch a short-lived Hume EVI access token using server-side credentials

Request:
- no body required

Current response:

```json
{
  "access_token": "....",
  "expires_in": 1799,
  "token_type": "Bearer"
}
```

Response fields:
- `access_token: string`
- `expires_in: number`
- `token_type: string`

Frontend usage:
- call after creating a session
- use `access_token` when opening the direct browser-to-Hume EVI websocket
- do not cache long-term; it is temporary

Failure example:

```json
{
  "detail": {
    "code": "hume_access_token_failed",
    "message": "Failed to fetch a Hume access token.",
    "correlation_id": null
  }
}
```

### `GET /v1/sessions/{session_id}/graph`

Purpose:
- retrieve the current graph snapshot for one session
- use this for initial graph load or reconnect recovery

Path params:
- `session_id: string`

Query params:
- `limit_nodes: integer`
  - default: `200`
  - min: `1`
  - max: `1000`
- `limit_edges: integer`
  - default: `400`
  - min: `1`
  - max: `2000`

Current response:

```json
{
  "nodes": [
    {
      "id": "session-123:Trigger:work stress",
      "label": "Trigger",
      "canonical": "work stress",
      "properties": {
        "session_id": "session-123",
        "canonical": "work stress",
        "created_at_ms": 1772326000000,
        "last_seen_at_ms": 1772326200000,
        "latest_goal_canonical": null
      }
    }
  ],
  "edges": [
    {
      "id": "session-123:Trigger:work stress:EVOKES:session-123:Emotion:anxious",
      "type": "EVOKES",
      "source": "session-123:Trigger:work stress",
      "target": "session-123:Emotion:anxious",
      "properties": {
        "created_at_ms": 1772326200000,
        "last_seen_at_ms": 1772326200000,
        "start_char": null,
        "end_char": null
      }
    }
  ]
}
```

Node shape:
- `id: string`
- `label: string`
- `canonical: string`
- `properties: object`

Edge shape:
- `id: string`
- `type: string`
- `source: string`
- `target: string`
- `properties: object`

Important note:
- the snapshot may include `Utterance` nodes plus `MENTIONS` edges
- it excludes `Session` and `ProsodyFrame` nodes from the graph response

404 example:

```json
{
  "detail": {
    "code": "session_not_found",
    "message": "Session session-abc was not found."
  }
}
```

### `POST /v1/sessions/{session_id}/end`

Purpose:
- mark a session as ended
- return a lightweight summary and top concepts

Path params:
- `session_id: string`

Request:
- no body required

Current response:

```json
{
  "summary": "Session ended. Top concepts captured: work stress, anxious, sleep better.",
  "top_concepts": [
    {
      "label": "Trigger",
      "canonical": "work stress",
      "mention_count": 1,
      "score": 2.77
    },
    {
      "label": "Emotion",
      "canonical": "anxious",
      "mention_count": 1,
      "score": 2.77
    }
  ]
}
```

Response fields:
- `summary: string`
- `top_concepts: TopConceptSummary[]`

`TopConceptSummary` shape:
- `label: string`
- `canonical: string`
- `mention_count: number | null`
- `score: number | null`

404 example:

```json
{
  "detail": {
    "code": "session_not_found",
    "message": "Session session-abc was not found."
  }
}
```

### `POST /v1/sessions/{session_id}/audio-window`

Purpose:
- fallback route for windowed audio mode
- reuses the same KG pipeline used by the websocket flow

Path params:
- `session_id: string`

Request:
- multipart form data

Current fields:
- `file?: UploadFile`
- `transcript_text: string`
- `message_id?: string`
- `timestamp_ms?: number`
- `prosody_scores_json?: string`

Important:
- `transcript_text` is currently required
- the backend accepts `file`, but does not yet perform server-side transcription from that upload

Current response:

```json
{
  "transcript": "Work stress keeps me up at night and I want better sleep.",
  "prosody_scores": {
    "Stress": 0.87,
    "Fatigue": 0.63
  },
  "kg_diff": {},
  "tool_calls_applied": {},
  "summary_partial": {},
  "coach_insight": {},
  "safety_event": {
    "type": "safety.status",
    "payload": {}
  },
  "warnings": [
    "audio_file_received_without_server_side_transcription"
  ]
}
```

## WebSocket Route

### `WS /ws/session/{session_id}`

Purpose:
- realtime channel between frontend and backend
- frontend forwards Hume transcript/prosody events
- backend sends graph diffs and execution receipts

Path params:
- `session_id: string`

Current requirements:
- session must already exist
- create it first with `POST /v1/sessions`
- provide a valid session token

Browser-safe auth:
- `?session_token=...` on the websocket URL

Non-browser auth option:
- `Authorization: Bearer ...`

If the session does not exist:
- backend sends `server.error`
- backend closes the socket with code `4404`

## WebSocket Envelope

Every client and server websocket message uses this wrapper:

```json
{
  "type": "evi.user_message.final",
  "session_id": "session-123456abcdef",
  "payload": {},
  "sent_at_ms": 1772326200000,
  "correlation_id": "corr-123456abcdef"
}
```

Envelope fields:
- `type: string`
- `session_id: string`
- `payload: object`
- `sent_at_ms: number`
- `correlation_id: string | null`

Client notes:
- `sent_at_ms` is optional for client packets; server will fill it if omitted
- `correlation_id` is optional for client packets; server will fill it if omitted
- `session_id` in the envelope must match the websocket path `session_id`

## Inbound WebSocket Messages

### `client.ping`

Purpose:
- simple keepalive / connectivity check

Client packet:

```json
{
  "type": "client.ping",
  "session_id": "session-123456abcdef",
  "payload": {},
  "correlation_id": "corr-ping-1"
}
```

Server response:

```json
{
  "type": "server.pong",
  "session_id": "session-123456abcdef",
  "payload": {
    "ok": true
  },
  "sent_at_ms": 1772326200000,
  "correlation_id": "corr-ping-1"
}
```

### `evi.assistant_message`

Purpose:
- store assistant transcript text for session history
- this currently does not trigger KG updates

Payload shape:

```json
{
  "message_id": "assistant-msg-1",
  "role": "assistant",
  "content": "I hear that work stress is really affecting you.",
  "timestamp_ms": 1772326200000
}
```

Server response:

```json
{
  "type": "server.ack",
  "session_id": "session-123456abcdef",
  "payload": {
    "accepted_type": "evi.assistant_message",
    "message_id": "assistant-msg-1"
  },
  "sent_at_ms": 1772326200100,
  "correlation_id": "corr-..."
}
```

### `evi.chat_metadata`

Purpose:
- optional metadata packet from the frontend
- currently acknowledged but not persisted

Client packet:

```json
{
  "type": "evi.chat_metadata",
  "session_id": "session-123456abcdef",
  "payload": {
    "provider": "hume"
  }
}
```

Server response:

```json
{
  "type": "server.ack",
  "session_id": "session-123456abcdef",
  "payload": {
    "accepted_type": "evi.chat_metadata"
  },
  "sent_at_ms": 1772326200200,
  "correlation_id": "corr-..."
}
```

### `evi.user_message.final`

Purpose:
- the main event used for graph updates
- send only finalized user transcript events here

Payload shape:

```json
{
  "message_id": "user-msg-1",
  "role": "user",
  "content": "Work stress makes me anxious and I want to sleep better.",
  "interim": false,
  "prosody_scores": {
    "Anxiety": 0.91,
    "Stress": 0.88,
    "Tiredness": 0.52
  },
  "timestamp_ms": 1772326201000,
  "raw_event": {
    "optional": "debug copy of original Hume event"
  }
}
```

Field notes:
- `message_id` is required
- `role` should be `"user"`
- `content` is the finalized transcript text
- `interim` should be `false`
- `prosody_scores` is optional but recommended
- `timestamp_ms` is optional
- `raw_event` is optional

Important behavior:
- if `interim` is `true`, the backend drops it from the KG mutation pipeline

## Outbound WebSocket Messages

### `kg.diff`

Purpose:
- tells the frontend which nodes and edges to upsert into the live graph
- includes evidence receipts for UI transparency

Payload shape:

```json
{
  "nodes_upsert": [
    {
      "id": "session-123:Trigger:work stress",
      "label": "Trigger",
      "canonical": "work stress",
      "properties": {
        "session_id": "session-123",
        "canonical": "work stress",
        "created_at_ms": 1772326201000,
        "last_seen_at_ms": 1772326201000,
        "latest_goal_canonical": null
      }
    }
  ],
  "edges_upsert": [
    {
      "id": "session-123:Trigger:work stress:EVOKES:session-123:Emotion:anxious",
      "type": "EVOKES",
      "source": "session-123:Trigger:work stress",
      "target": "session-123:Emotion:anxious",
      "properties": {
        "created_at_ms": 1772326201000,
        "last_seen_at_ms": 1772326201000,
        "start_char": null,
        "end_char": null
      }
    }
  ],
  "receipts": [
    {
      "receipt_id": "receipt-123456abcdef",
      "message_id": "user-msg-1",
      "tool_name": "upsert_relation_edge",
      "evidence_quote": "Work stress makes me anxious",
      "applied_node_ids": [
        "session-123:Trigger:work stress",
        "session-123:Emotion:anxious"
      ],
      "applied_edge_ids": [
        "session-123:Trigger:work stress:EVOKES:session-123:Emotion:anxious"
      ],
      "verified": true,
      "warnings": []
    }
  ],
  "warnings": []
}
```

Frontend usage:
- upsert `nodes_upsert` into local graph state keyed by `id`
- upsert `edges_upsert` into local graph state keyed by `id`
- render `receipts` in a side panel or evidence UI

### `kg.tool_calls_applied`

Purpose:
- debugging and transparency for tool execution
- includes applied calls and dropped calls

Payload shape:

```json
{
  "calls": [
    {
      "name": "upsert_concept_node",
      "arguments": {
        "label": "Trigger",
        "canonical": "work stress",
        "message_id": "user-msg-1",
        "evidence_quote": "Work stress"
      },
      "status": "applied",
      "message_id": "user-msg-1",
      "session_id": "session-123456abcdef",
      "receipt_id": null,
      "applied_nodes": [],
      "applied_edges": []
    }
  ],
  "dropped_calls": [
    {
      "name": "upsert_relation_edge",
      "arguments": {},
      "status": "dropped",
      "reason": "Tool call evidence quote was not found in the utterance text"
    }
  ]
}
```

Frontend usage:
- optional developer/debug panel
- not required for basic graph rendering

### `summary.partial`

Purpose:
- rolling compact summary after a finalized user message

Payload shape:

```json
{
  "summary": "Current session themes: work stress, anxious, sleep better.",
  "based_on_message_id": "user-msg-1",
  "top_concepts": [],
  "updated_at_ms": 1772326202000
}
```

### `coach.insight`

Purpose:
- one supportive frontend card grounded in the latest message and current graph

Payload shape:

```json
{
  "card": {
    "reflection": "Work stress seems tightly linked to anxiety for you right now.",
    "question": "What part of the stress feels most active at night?",
    "focus": "Sleep and stress"
  },
  "receipt_ids": [],
  "message_id": "user-msg-1"
}
```

### `safety.status` / `safety.alert`

Purpose:
- structured safety classification after a finalized user message

Payload shape:

```json
{
  "risk_level": "low",
  "recommended_actions": [],
  "message_id": "user-msg-1",
  "rationale": "No direct acute safety indicators were identified."
}
```

### `server.pong`

Purpose:
- response to `client.ping`

Payload:

```json
{
  "ok": true
}
```

### `server.ack`

Purpose:
- acknowledgement for non-KG websocket packets

Payload examples:

```json
{
  "accepted_type": "evi.assistant_message",
  "message_id": "assistant-msg-1"
}
```

```json
{
  "accepted_type": "evi.chat_metadata"
}
```

### `server.error`

Purpose:
- structured websocket error response

Payload shape:

```json
{
  "code": "unsupported_ws_message_type",
  "message": "Unsupported websocket packet type: unknown.type",
  "correlation_id": "corr-123456abcdef",
  "retryable": false,
  "details": null
}
```

Common codes:
- `session_not_found`
- `invalid_ws_packet`
- `session_id_mismatch`
- `unsupported_ws_message_type`
- `ws_processing_error`

Frontend usage:
- show a safe error message
- optionally log `correlation_id`
- retry only if `retryable` is `true`

## Current Backend Behavior Notes

These are important for frontend expectations:

- voice audio does not flow through FastAPI
  - browser talks directly to Hume EVI
  - browser forwards selected transcript/prosody events to FastAPI
- the backend websocket currently expects JSON only
- `evi.user_message.final` is the main event for KG updates
- `evi.assistant_message` is stored, but does not currently update the graph
- graph updates are session-scoped
- graph snapshots exclude `Session` and `ProsodyFrame` nodes
- graph snapshots may include `Utterance` nodes and `MENTIONS` edges

## What Is Not Implemented Yet

These items appear in planning docs but are not currently part of the live backend contract:

- persisted safety assessments
- persisted receipt nodes in Neo4j

Frontend should not depend on those yet.

## Minimal Frontend Example

### Create session

```ts
const sessionRes = await fetch("/v1/sessions", { method: "POST" });
const session = await sessionRes.json();
const sessionId = session.session_id;
const sessionToken = session.session_token;
```

### Get Hume token

```ts
const tokenRes = await fetch("/v1/hume/access-token", { method: "POST" });
const token = await tokenRes.json();
```

### Open backend websocket

```ts
const ws = new WebSocket(
  `ws://127.0.0.1:8000/ws/session/${sessionId}?session_token=${sessionToken}`
);

ws.onmessage = (event) => {
  const packet = JSON.parse(event.data);
  if (packet.type === "kg.diff") {
    // update graph
  }
  if (packet.type === "kg.tool_calls_applied") {
    // optional debug UI
  }
  if (packet.type === "summary.partial") {
    // update rolling summary UI
  }
  if (packet.type === "coach.insight") {
    // render insight card
  }
  if (packet.type === "safety.status" || packet.type === "safety.alert") {
    // update safety UI
  }
  if (packet.type === "server.error") {
    // show/log error
  }
};
```

### Forward a finalized Hume user message

```ts
ws.send(
  JSON.stringify({
    type: "evi.user_message.final",
    session_id: sessionId,
    payload: {
      message_id: "user-msg-1",
      role: "user",
      content: "Work stress makes me anxious and I want to sleep better.",
      interim: false,
      prosody_scores: {
        Anxiety: 0.91,
        Stress: 0.88,
      },
      timestamp_ms: Date.now(),
    },
  })
);
```

### Recover graph state

```ts
const graphRes = await fetch(`/v1/sessions/${sessionId}/graph`);
const graph = await graphRes.json();
```

### End session

```ts
const endRes = await fetch(`/v1/sessions/${sessionId}/end`, { method: "POST" });
const summary = await endRes.json();
```
