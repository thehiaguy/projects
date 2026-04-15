# Frontend Integration Guide

This is the frontend-only version of the backend contract.

Use this when wiring the Next.js client to:
- create sessions
- fetch a Hume token
- connect to the backend websocket
- send finalized Hume transcript events
- receive graph updates

## Base URLs

- Local HTTP: `http://127.0.0.1:8000`
- Local WS: `ws://127.0.0.1:8000/ws/session/{session_id}`

## Integration Order

1. `POST /v1/sessions`
2. Save the returned `session_token`
3. `POST /v1/hume/access-token`
4. Open Hume EVI directly from the browser
5. Open backend websocket: `WS /ws/session/{session_id}?session_token=...`
6. Forward finalized Hume user transcript events to backend
7. Listen for `kg.diff`, `summary.partial`, `coach.insight`, and `safety.status` / `safety.alert`
8. Use `GET /v1/sessions/{session_id}/graph` for reconnect/recovery
9. `POST /v1/sessions/{session_id}/end`

## REST Routes

### `GET /v1/health`

Response:

```json
{
  "ok": true
}
```

### `POST /v1/sessions`

Request:
- no body

Response:

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

Frontend requirement:
- save `session_id`
- save `session_token`

### `POST /v1/hume/access-token`

Request:
- no body

Response:

```json
{
  "access_token": "....",
  "expires_in": 1799,
  "token_type": "Bearer"
}
```

Frontend requirement:
- use `access_token` to connect to Hume EVI

### `GET /v1/sessions/{session_id}/graph`

Optional query params:
- `limit_nodes`
- `limit_edges`

Response:

```json
{
  "nodes": [
    {
      "id": "session-123:Trigger:work stress",
      "label": "Trigger",
      "canonical": "work stress",
      "properties": {}
    }
  ],
  "edges": [
    {
      "id": "edge-1",
      "type": "EVOKES",
      "source": "node-a",
      "target": "node-b",
      "properties": {}
    }
  ]
}
```

Use this for:
- initial graph load
- reconnect recovery
- full graph refresh

### `POST /v1/sessions/{session_id}/audio-window`

Fallback multipart route for windowed audio mode.

Current request fields:
- `file?: UploadFile`
- `transcript_text: string`
- `message_id?: string`
- `timestamp_ms?: number`
- `prosody_scores_json?: string`

Important:
- the current backend requires `transcript_text`
- if you upload an audio file, the backend accepts it but does not yet transcribe it server-side

Example response:

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

### `POST /v1/sessions/{session_id}/end`

Request:
- no body

Response:

```json
{
  "summary": "Session ended. Top concepts captured: work stress, anxious, sleep better.",
  "top_concepts": [
    {
      "label": "Trigger",
      "canonical": "work stress",
      "mention_count": 1,
      "score": 2.77
    }
  ]
}
```

## WebSocket Route

### `WS /ws/session/{session_id}`

Open after creating the session.

If the session does not exist, the server sends `server.error` and closes the socket.

Auth:
- include `session_token` as a query param
- browser example:
  - `ws://127.0.0.1:8000/ws/session/${sessionId}?session_token=${sessionToken}`

## WebSocket Envelope

All websocket messages use this wrapper:

```json
{
  "type": "evi.user_message.final",
  "session_id": "session-123456abcdef",
  "payload": {},
  "sent_at_ms": 1772326200000,
  "correlation_id": "corr-123456abcdef"
}
```

Fields:
- `type: string`
- `session_id: string`
- `payload: object`
- `sent_at_ms: number`
- `correlation_id: string | null`

Client notes:
- you may omit `sent_at_ms`
- you may omit `correlation_id`
- `session_id` must match the websocket path

## Inbound WebSocket Messages From Frontend

### `client.ping`

Send:

```json
{
  "type": "client.ping",
  "session_id": "session-123456abcdef",
  "payload": {}
}
```

Receive:

```json
{
  "type": "server.pong",
  "session_id": "session-123456abcdef",
  "payload": {
    "ok": true
  }
}
```

### `evi.assistant_message`

Use this to store assistant transcript text.

Send:

```json
{
  "type": "evi.assistant_message",
  "session_id": "session-123456abcdef",
  "payload": {
    "message_id": "assistant-msg-1",
    "role": "assistant",
    "content": "I hear that work stress is really affecting you.",
    "timestamp_ms": 1772326200000
  }
}
```

Receive:

```json
{
  "type": "server.ack",
  "session_id": "session-123456abcdef",
  "payload": {
    "accepted_type": "evi.assistant_message",
    "message_id": "assistant-msg-1"
  }
}
```

### `evi.chat_metadata`

Optional metadata packet.

Send:

```json
{
  "type": "evi.chat_metadata",
  "session_id": "session-123456abcdef",
  "payload": {
    "provider": "hume"
  }
}
```

Receive:

```json
{
  "type": "server.ack",
  "session_id": "session-123456abcdef",
  "payload": {
    "accepted_type": "evi.chat_metadata"
  }
}
```

### `evi.user_message.final`

This is the main packet for graph updates.

Send only finalized user transcript events here.

Send:

```json
{
  "type": "evi.user_message.final",
  "session_id": "session-123456abcdef",
  "payload": {
    "message_id": "user-msg-1",
    "role": "user",
    "content": "Work stress makes me anxious and I want to sleep better.",
    "interim": false,
    "prosody_scores": {
      "Anxiety": 0.91,
      "Stress": 0.88
    },
    "timestamp_ms": 1772326201000
  }
}
```

Payload fields:
- `message_id: string`
- `role: "user"`
- `content: string`
- `interim: boolean`
- `prosody_scores?: Record<string, number>`
- `timestamp_ms?: number`
- `raw_event?: object`

Important:
- if `interim` is `true`, the backend ignores it for KG updates

## Outbound WebSocket Messages To Frontend

### `kg.diff`

Primary live graph update message.

Receive:

```json
{
  "type": "kg.diff",
  "session_id": "session-123456abcdef",
  "payload": {
    "nodes_upsert": [],
    "edges_upsert": [],
    "receipts": [],
    "warnings": []
  }
}
```

Payload fields:
- `nodes_upsert: KgNode[]`
- `edges_upsert: KgEdge[]`
- `receipts: Receipt[]`
- `warnings: string[]`

Frontend behavior:
- upsert nodes by `id`
- upsert edges by `id`
- render receipts if needed

### `kg.tool_calls_applied`

Tool execution/debug packet.

Receive:

```json
{
  "type": "kg.tool_calls_applied",
  "session_id": "session-123456abcdef",
  "payload": {
    "calls": [],
    "dropped_calls": []
  }
}
```

Payload fields:
- `calls: object[]`
- `dropped_calls: object[]`

Frontend behavior:
- optional debug panel
- not required for base graph UI

### `summary.partial`

Rolling summary event.

Receive:

```json
{
  "type": "summary.partial",
  "session_id": "session-123456abcdef",
  "payload": {
    "summary": "Current session themes: work stress, anxious, sleep better.",
    "based_on_message_id": "user-msg-1",
    "top_concepts": [],
    "updated_at_ms": 1772326202000
  }
}
```

### `coach.insight`

Supportive UI card.

Receive:

```json
{
  "type": "coach.insight",
  "session_id": "session-123456abcdef",
  "payload": {
    "card": {
      "reflection": "Work stress seems tightly linked to anxiety for you right now.",
      "question": "What part of the stress feels most active at night?",
      "focus": "Sleep and stress"
    },
    "receipt_ids": [],
    "message_id": "user-msg-1"
  }
}
```

### `safety.status`

Low/no-risk safety signal.

### `safety.alert`

Medium/high-risk safety signal.

Example safety payload:

```json
{
  "type": "safety.status",
  "session_id": "session-123456abcdef",
  "payload": {
    "risk_level": "low",
    "recommended_actions": [],
    "message_id": "user-msg-1",
    "rationale": "No direct acute safety indicators were identified."
  }
}
```

### `server.pong`

Receive after `client.ping`.

```json
{
  "type": "server.pong",
  "session_id": "session-123456abcdef",
  "payload": {
    "ok": true
  }
}
```

### `server.ack`

Receive after `evi.assistant_message` or `evi.chat_metadata`.

### `server.error`

Receive on websocket errors.

```json
{
  "type": "server.error",
  "session_id": "session-123456abcdef",
  "payload": {
    "code": "unsupported_ws_message_type",
    "message": "Unsupported websocket packet type: unknown.type",
    "correlation_id": "corr-123456abcdef",
    "retryable": false,
    "details": null
  }
}
```

Frontend behavior:
- show/log `payload.message`
- keep `payload.correlation_id` for debugging
- only retry automatically if `payload.retryable === true`

## Suggested TypeScript Interfaces

```ts
export type WsEnvelope<T = Record<string, unknown>> = {
  type: string;
  session_id: string;
  payload: T;
  sent_at_ms?: number;
  correlation_id?: string | null;
};

export type KgNode = {
  id: string;
  label: string;
  canonical: string;
  properties: Record<string, unknown>;
};

export type KgEdge = {
  id: string;
  type: string;
  source: string;
  target: string;
  properties: Record<string, unknown>;
};

export type Receipt = {
  receipt_id: string;
  message_id: string;
  tool_name: string;
  evidence_quote: string;
  applied_node_ids: string[];
  applied_edge_ids: string[];
  verified: boolean;
  warnings: string[];
};

export type KgDiffPayload = {
  nodes_upsert: KgNode[];
  edges_upsert: KgEdge[];
  receipts: Receipt[];
  warnings: string[];
};
```

## Minimal Frontend Example

```ts
const sessionRes = await fetch("/v1/sessions", { method: "POST" });
const session = await sessionRes.json();
const sessionId = session.session_id;
const sessionToken = session.session_token;

const tokenRes = await fetch("/v1/hume/access-token", { method: "POST" });
const token = await tokenRes.json();

const ws = new WebSocket(
  `ws://127.0.0.1:8000/ws/session/${sessionId}?session_token=${sessionToken}`
);

ws.onmessage = (event) => {
  const packet = JSON.parse(event.data);

  if (packet.type === "kg.diff") {
    const diff = packet.payload;
    // merge diff.nodes_upsert and diff.edges_upsert into graph state
  }

  if (packet.type === "summary.partial") {
    // update rolling summary UI
  }

  if (packet.type === "coach.insight") {
    // render coach card
  }

  if (packet.type === "safety.status" || packet.type === "safety.alert") {
    // update safety UI state
  }

  if (packet.type === "server.error") {
    console.error(packet.payload);
  }
};

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

## Not Available Yet

Do not depend on these yet:

- backend-issued `sessionToken`
- websocket auth headers
