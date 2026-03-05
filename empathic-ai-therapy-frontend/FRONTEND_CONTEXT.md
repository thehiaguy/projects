# Empathic AI Therapy — Backend Context for Frontend Development

This document is a complete reference for building the frontend. It covers every API contract, WebSocket protocol, data shape, and architectural decision made in the backend. Read this in full before writing a single line of frontend code.

---

## 1. Project Overview

An AI-powered therapy companion that:
1. Conducts real-time voice conversations via **Hume EVI** (Empathic Voice Interface)
2. Transcribes and analyzes user speech in real time
3. Extracts a **therapeutic knowledge graph (KG)** from each utterance using **Vertex AI Gemini**
4. Persists the KG in **Neo4j** for the duration of the session
5. Streams KG updates back to the frontend via **WebSocket** so the UI can visualize the user's emotional/conceptual world as it evolves

---

## 2. Running the Backend

```bash
cd apps/api
# Activate venv if needed
set -a && source .env && set +a
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Base URL: `http://localhost:8000`
WebSocket base: `ws://localhost:8000`

---

## 3. Environment Variables (.env)

```env
# Hume EVI (voice AI)
HUME_API_KEY=<from hume.ai dashboard>
HUME_SECRET_KEY=<from hume.ai dashboard>
HUME_CONFIG_ID=<EVI config ID from hume.ai>

# Google Vertex AI (Gemini, via ADC)
GCP_PROJECT=gen-lang-client-0552758370
GCP_LOCATION=us-central1
GEMINI_MODEL_KG=gemini-2.0-flash-001

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<your neo4j password>
NEO4J_DATABASE=neo4j

# Server
CORS_ALLOW_ORIGINS=http://localhost:3000
WS_MAX_SIZE_BYTES=16777216
LOG_LEVEL=INFO
```

**Auth**: Vertex AI uses Google Application Default Credentials (ADC). No API key needed — `gcloud auth application-default login` was run on the host machine.

---

## 4. REST API Reference

### 4.1 Health Check

```
GET /v1/health
```

**Response 200:**
```json
{ "ok": true }
```

---

### 4.2 Create Session

```
POST /v1/sessions
Content-Type: application/json
Body: {}
```

Creates a new therapy session in Neo4j. Call this before opening a WebSocket.

**Response 200:**
```json
{
  "session_id": "sess_a691a305f03c4cf6b4837b1b1eb46fed",
  "created_at_ms": 1772331787307,
  "status": "active"
}
```

- `session_id` — use this for all subsequent calls and the WS URL
- `created_at_ms` — Unix epoch milliseconds
- `status` — always `"active"` on create

---

### 4.3 End Session

```
POST /v1/sessions/{session_id}/end
```

Ends the session and returns a summary with the top therapeutic concepts identified.

**Response 200:**
```json
{
  "session_id": "sess_a691a305f03c4cf6b4837b1b1eb46fed",
  "ended_at_ms": 1772331900000,
  "summary": "Session completed. Key themes discussed: anxiety (Emotion), job interview (Trigger), reduce anxiety (Goal).",
  "top_concepts": [
    {
      "label": "Emotion",
      "canonical": "anxiety",
      "mention_count": 5,
      "score": 0.92
    },
    {
      "label": "Trigger",
      "canonical": "job interview",
      "mention_count": 3,
      "score": 0.75
    }
  ]
}
```

**Response 404** (session not found):
```json
{
  "detail": {
    "code": "session_not_found",
    "message": "Session 'sess_xyz' not found."
  }
}
```

---

### 4.4 Get Session Graph Snapshot

```
GET /v1/sessions/{session_id}/graph
```

Returns the full current state of the knowledge graph for a session.

**Response 200:**
```json
{
  "nodes": [
    {
      "id": "Emotion:sess_abc:anxiety",
      "label": "Emotion",
      "canonical": "anxiety",
      "properties": {}
    },
    {
      "id": "Trigger:sess_abc:job interview",
      "label": "Trigger",
      "canonical": "job interview",
      "properties": {}
    }
  ],
  "edges": [
    {
      "id": "e_xyz",
      "type": "EVOKES",
      "source": "Trigger:sess_abc:job interview",
      "target": "Emotion:sess_abc:anxiety",
      "properties": {}
    }
  ]
}
```

Node `id` format: `"{Label}:{session_id}:{canonical}"`
Edge `source`/`target` reference node `id` values.

---

### 4.5 Get Hume Access Token

```
POST /v1/hume/access-token
```

Exchanges your Hume API credentials (stored in backend `.env`) for a short-lived bearer token that the frontend uses to connect to Hume EVI directly.

**Response 200:**
```json
{
  "access_token": "eyJ...",
  "expires_in": 3600,
  "token_type": "Bearer"
}
```

**Response 401** (bad credentials):
```json
{
  "detail": {
    "code": "hume_auth_failed",
    "message": "Hume OAuth returned status 401.",
    "correlation_id": null
  }
}
```

**Frontend usage**: Fetch this token, then pass it to the Hume EVI SDK when starting a voice session.

---

## 5. WebSocket API Reference

### 5.1 Connection

```
ws://localhost:8000/ws/session/{session_id}
```

Open one WebSocket per session. The session must already exist (call `POST /v1/sessions` first).

### 5.2 Message Envelope Schema

Every message (both client→server and server→client) uses this envelope:

```typescript
interface WsEnvelope {
  type: string;           // message type identifier
  session_id: string;     // must match the URL parameter
  payload: object;        // type-specific content
  sent_at_ms: number;     // Unix epoch milliseconds (integer)
  correlation_id: string; // UUID-like string for request tracing
}
```

### 5.3 Client → Server Messages

#### `client.ping`
Heartbeat to keep the connection alive and verify round-trip.

```json
{
  "type": "client.ping",
  "session_id": "sess_abc",
  "payload": {},
  "correlation_id": "corr_optional"
}
```

#### `evi.user_message.final`
Triggered when Hume EVI finishes transcribing a user utterance. This is the main driver of KG updates.

```json
{
  "type": "evi.user_message.final",
  "session_id": "sess_abc",
  "payload": {
    "message_id": "msg_001",
    "content": "I feel really anxious about my job interview tomorrow",
    "role": "user",
    "interim": false,
    "prosody_scores": {
      "anxiety": 0.91,
      "fear": 0.63,
      "sadness": 0.21
    },
    "timestamp_ms": 1772331800000
  }
}
```

- `interim: true` — message is still being transcribed; server drops it silently
- `interim: false` — final transcript; triggers full KG pipeline
- `prosody_scores` — optional dict of Hume emotion labels → confidence (0–1); used as hints for KG extraction
- `message_id` — stable ID from Hume EVI, used for evidence linking in the KG

#### `evi.assistant_message`
Assistant (AI) message — currently accepted but produces no response. Included for future context tracking.

```json
{
  "type": "evi.assistant_message",
  "session_id": "sess_abc",
  "payload": {
    "message_id": "msg_002",
    "content": "I hear you. Can you tell me more about what makes the interview feel so scary?",
    "role": "assistant"
  }
}
```

#### `evi.chat_metadata`
Hume metadata events — accepted and silently ignored.

---

### 5.4 Server → Client Messages

#### `server.pong`
Response to `client.ping`.

```json
{
  "type": "server.pong",
  "session_id": "sess_abc",
  "payload": {
    "server_ts_ms": 1772331801042
  },
  "sent_at_ms": 1772331801042,
  "correlation_id": "corr_d5564e593c01473e8a7b73f126b944fd"
}
```

#### `kg.diff`
Sent after processing an `evi.user_message.final`. Contains everything that changed in the knowledge graph.

```json
{
  "type": "kg.diff",
  "session_id": "sess_abc",
  "payload": {
    "nodes_upsert": [
      {
        "id": "Emotion:sess_abc:anxiety",
        "label": "Emotion",
        "canonical": "anxiety",
        "properties": {}
      },
      {
        "id": "Trigger:sess_abc:job interview",
        "label": "Trigger",
        "canonical": "job interview",
        "properties": {}
      }
    ],
    "edges_upsert": [
      {
        "id": "e_xyz",
        "type": "EVOKES",
        "source": "Trigger:sess_abc:job interview",
        "target": "Emotion:sess_abc:anxiety",
        "properties": {}
      }
    ],
    "receipts": [
      {
        "receipt_id": "rct_abc123",
        "message_id": "msg_001",
        "tool_name": "upsert_concept_node",
        "evidence_quote": "anxious about my upcoming job interview",
        "applied_node_ids": ["Emotion:sess_abc:anxiety"],
        "applied_edge_ids": [],
        "verified": true,
        "warnings": []
      }
    ],
    "warnings": []
  },
  "sent_at_ms": 1772331802100,
  "correlation_id": "corr_abc"
}
```

**Key design notes:**
- `nodes_upsert` and `edges_upsert` are **upsert** operations — apply them on top of existing state (same `id` = replace/merge)
- `receipts` provide evidence traceability — each links a KG mutation back to an exact quote in the user's speech
- This message arrives before `kg.tool_calls_applied` — render graph updates immediately on receipt

#### `kg.tool_calls_applied`
Sent immediately after `kg.diff`. Provides a structured log of what Gemini called and what was applied/dropped.

```json
{
  "type": "kg.tool_calls_applied",
  "session_id": "sess_abc",
  "payload": {
    "calls": [
      {
        "name": "upsert_concept_node",
        "arguments": {
          "label": "Emotion",
          "canonical": "anxiety",
          "message_id": "msg_001",
          "evidence_quote": "anxious"
        },
        "status": "applied",
        "message_id": "msg_001"
      }
    ],
    "dropped_calls": []
  },
  "sent_at_ms": 1772331802200,
  "correlation_id": "corr_abc"
}
```

#### `server.error`
Sent when any processing error occurs. **The connection is NOT closed** — it remains open for subsequent messages.

```json
{
  "type": "server.error",
  "session_id": "sess_abc",
  "payload": {
    "code": "internal_error",
    "message": "An unexpected error occurred.",
    "correlation_id": "corr_xyz",
    "retryable": false,
    "details": {}
  },
  "sent_at_ms": 1772331803000,
  "correlation_id": "corr_xyz"
}
```

Error codes:
- `unknown_message_type` — sent an unrecognized `type`
- `missing_type` — envelope has no `type` field
- `missing_session_id` — envelope has no `session_id` field
- `invalid_packet` — message is not a JSON object
- `internal_error` — KG pipeline failure (Gemini/Neo4j error)

---

### 5.5 WebSocket Message Sequence

```
Client                          Server
  |                               |
  |-- WS connect ---------------→|
  |                               |  (connection accepted)
  |                               |
  |-- client.ping ---------------→|
  |←-- server.pong --------------|
  |                               |
  |-- evi.user_message.final ----→|
  |                               |  [calls Gemini Vertex AI ~1-3s]
  |                               |  [writes to Neo4j]
  |←-- kg.diff -----------------|
  |←-- kg.tool_calls_applied ----|
  |                               |
  |  (repeat for each utterance)  |
  |                               |
  |-- WS disconnect ------------>|
```

---

## 6. Knowledge Graph Data Model

### 6.1 Node Labels (ConceptLabel enum)

| Label | Description |
|-------|-------------|
| `Person` | People mentioned (therapist, family, colleagues) |
| `Trigger` | Situations or events that cause emotional responses |
| `Emotion` | Emotional states explicitly named by the user |
| `Belief` | Core beliefs or cognitive patterns |
| `Need` | Unmet needs or desires |
| `Goal` | Therapeutic goals or desired outcomes |
| `Action` | Behaviors, coping strategies, or planned actions |
| `Event` | Specific life events referenced |

### 6.2 Relationship Types (GraphRelationshipType enum)

| Type | Meaning |
|------|---------|
| `HAS_UTTERANCE` | Session → Utterance |
| `MENTIONS` | Utterance → Concept (what was said about it) |
| `EVOKES` | Trigger → Emotion (this situation causes this feeling) |
| `DRIVES` | Need/Belief → Action (motivates behavior) |
| `LEADS_TO` | Event → Emotion/Event (causal chain) |
| `AFFECTS` | Concept → Concept (general influence) |
| `SUPPORTS` | Concept → Concept (positive reinforcement) |
| `CONFLICTS_WITH` | Concept → Concept (cognitive dissonance) |

### 6.3 Node ID Format

```
"{Label}:{session_id}:{canonical}"
```

Example: `"Emotion:sess_abc123:anxiety"`

Nodes are **session-scoped** — same concept in different sessions = different nodes.

### 6.4 Canonical Form

The `canonical` field is always:
- Lowercase
- Concise (2–4 words max)
- Stable across utterances (e.g., always `"job interview"`, never `"my job interview tomorrow"`)

---

## 7. Typical Frontend Session Flow

```
1. User opens the app
2. Frontend: POST /v1/sessions → get session_id
3. Frontend: POST /v1/hume/access-token → get hume_token
4. Frontend: Open Hume EVI voice session using hume_token + HUME_CONFIG_ID
5. Frontend: Open WebSocket ws://localhost:8000/ws/session/{session_id}
6. Frontend: Send client.ping every 30s to keep WS alive

7. User speaks → Hume EVI streams audio
8. Hume EVI emits interim transcripts (ignore or show as "typing...")
9. Hume EVI emits final transcript with prosody scores
10. Frontend: Forward to backend as evi.user_message.final
11. Backend responds with kg.diff → Frontend updates graph visualization
12. Backend responds with kg.tool_calls_applied → Optional debug display

13. User ends session
14. Frontend: POST /v1/sessions/{session_id}/end → show summary
15. Frontend: Close WebSocket
```

---

## 8. Hume EVI Integration Notes

The backend provides a token exchange endpoint (`POST /v1/hume/access-token`) but does **not** connect to Hume itself — the frontend connects to Hume EVI directly.

**What the frontend needs to do with Hume:**
- Use the `@humeai/sdk` npm package
- Connect using the access token + `HUME_CONFIG_ID`
- Listen for `user_message` events from Hume
- When `final: true` (or equivalent), forward to the backend WebSocket as `evi.user_message.final`
- Include `prosody_scores` from Hume's emotion detection in the payload

**Prosody score format from Hume:**
```json
{
  "anxiety": 0.91,
  "fear": 0.63,
  "sadness": 0.21,
  "excitement": 0.05,
  ...
}
```
These are float values 0.0–1.0 representing confidence in each emotion label.

---

## 9. Graph Visualization Recommendations

The `kg.diff` messages come in incrementally — the frontend should maintain a **local graph state** and apply diffs on top:

```typescript
// Pseudo-code for managing graph state
type GraphState = {
  nodes: Map<string, KgNode>;  // keyed by node.id
  edges: Map<string, KgEdge>;  // keyed by edge.id
}

function applyKgDiff(state: GraphState, diff: KgDiff): GraphState {
  for (const node of diff.nodes_upsert) {
    state.nodes.set(node.id, node);  // upsert
  }
  for (const edge of diff.edges_upsert) {
    state.edges.set(edge.id, edge);  // upsert
  }
  return state;
}
```

**Visual suggestion per node label:**
| Label | Color suggestion | Icon |
|-------|-----------------|------|
| Emotion | Red/Orange | ❤️ |
| Trigger | Yellow | ⚡ |
| Belief | Purple | 💭 |
| Need | Blue | 💧 |
| Goal | Green | 🎯 |
| Action | Teal | 🔧 |
| Person | Gray | 👤 |
| Event | Brown | 📅 |

---

## 10. Error Handling Patterns

### REST errors
All REST errors follow FastAPI's standard format:
```json
{
  "detail": {
    "code": "error_code",
    "message": "Human readable message",
    "correlation_id": "corr_xyz_or_null"
  }
}
```

### WebSocket errors
`server.error` is sent but the connection stays open. Frontend should:
1. Display a non-blocking notification to the user
2. Continue listening for future messages
3. Only close the connection if the user explicitly ends the session

---

## 11. CORS Configuration

Backend allows: `http://localhost:3000` by default (set via `CORS_ALLOW_ORIGINS` in `.env`).

For production, update `.env`:
```env
CORS_ALLOW_ORIGINS=https://yourapp.com,https://www.yourapp.com
```

---

## 12. Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| API Framework | FastAPI (Python 3.11) |
| WebSocket | FastAPI native WebSocket |
| Voice AI | Hume EVI (frontend connects directly) |
| KG Extraction | Google Vertex AI Gemini 2.0 Flash |
| Graph Database | Neo4j (Bolt protocol) |
| Auth (Vertex AI) | Google ADC (Application Default Credentials) |
| Server | Uvicorn |

---

## 13. ID Formats

All IDs are `{prefix}{uuid4_hex}` (no hyphens):

| Type | Prefix | Example |
|------|--------|---------|
| Session | `sess_` | `sess_a691a305f03c4cf6b4837b1b1eb46fed` |
| Utterance | `utt_` | `utt_3f2a1b...` |
| Prosody Frame | `pf_` | `pf_9c8d7e...` |
| Receipt | `rct_` | `rct_1a2b3c...` |
| Correlation | `corr_` | `corr_d5564e593c01473e8a7b73f126b944fd` |

---

## 14. What the Backend Does NOT Handle

The frontend is responsible for:
- Connecting to Hume EVI (the backend only provides the access token)
- Audio capture and playback
- Displaying the conversation transcript
- Rendering the knowledge graph visually (D3.js, react-force-graph, Cytoscape.js, etc.)
- Session UI (start/stop buttons, timer, etc.)
- Any user authentication (none implemented in backend yet)

---

## 15. File Structure Reference

```
apps/api/
├── app/
│   ├── main.py          # FastAPI app factory + lifespan (Neo4j startup)
│   └── deps.py          # Settings, get_gemini_client(), get_neo4j_driver()
├── api/routes/
│   ├── health.py        # GET /v1/health
│   ├── sessions.py      # POST /v1/sessions, POST /v1/sessions/{id}/end
│   ├── graph.py         # GET /v1/sessions/{id}/graph
│   └── auth_hume.py     # POST /v1/hume/access-token
├── ws/
│   ├── session_ws.py    # WebSocket handler (main loop + message dispatch)
│   └── protocol.py      # WsEnvelope, parse_client_envelope, build_ws_envelope
├── orchestration/
│   ├── kg_updater.py    # 8-stage pipeline: utterance → Gemini → Neo4j
│   └── receipts.py      # Evidence verification + receipt building
├── services/
│   ├── gemini/
│   │   ├── client.py    # vertexai.init() + generate_kg_tool_calls()
│   │   ├── kg_tools.py  # FunctionDeclaration objects for Gemini tool calling
│   │   ├── prompts.py   # System + user prompt builders
│   │   └── schemas.py   # Pydantic validation + normalize_tool_calls()
│   ├── hume/
│   │   └── oauth.py     # fetch_access_token() via Basic auth
│   └── neo4j/
│       ├── driver.py    # Singleton Neo4j driver (execute_read/write)
│       ├── migrate.py   # Run constraints.cypher on startup
│       ├── repo_sessions.py    # create/get/end session records
│       ├── repo_utterances.py  # upsert_utterance, insert_prosody_frame
│       └── repo_graph.py       # upsert_concept_node, upsert_relation_edge,
│                               # get_graph_snapshot, get_graph_context_for_llm
├── domain/
│   ├── models.py        # Pydantic models (SessionRecord, KgNode, KgEdge, etc.)
│   └── enums.py         # ConceptLabel, GraphRelationshipType
└── utils/
    ├── ids.py           # new_session_id(), new_utterance_id(), etc.
    ├── errors.py        # AppError, to_http_exception()
    └── logging.py       # configure_logging(), log_ws_event()
```
