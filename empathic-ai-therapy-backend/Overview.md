

___________
## Session Start

```mermaid

sequenceDiagram
  participant U as User
  participant FE as Next.js Client
  participant BE as FastAPI
  participant HU as Hume OAuth
  participant EVI as EVI WebSocket
  participant DB as Neo4j

  U->>FE: Click "Start" + consent
  FE->>BE: POST /v1/sessions {consent:true}
  BE->>DB: Create (Session)
  BE-->>FE: {sessionId, sessionToken}
  FE->>BE: POST /v1/hume/access-token
  BE->>HU: POST /oauth2-cc/token (Basic auth)
  HU-->>BE: {access_token, expires_in}
  BE-->>FE: {access_token, expires_in}
  FE->>EVI: Connect wss://.../v0/evi/chat?access_token=...&verbose_transcription=true
  EVI-->>FE: chat_metadata + events
  FE->>BE: WS /ws/session/{sessionId} (Authorization)
  
```


_________

## Voice w/KG listener

```mermaid

sequenceDiagram
  participant FE as Next.js Client
  participant EVI as EVI WebSocket
  participant BE as FastAPI WS
  participant DB as Neo4j
  participant GM as Gemini

  FE->>EVI: audio_input (streamed chunks)
  EVI-->>FE: audio_output (base64 WAV) + assistant_message
  EVI-->>FE: user_message (interim true/false + transcript + prosody)

%%   Note over FE: Ignore interim for KG updates;\nuse interim to stop playback %%
  FE->>BE: WS send evi.user_message.final {messageId,text,prosodyScores,...}
  BE->>DB: Persist Utterance + ProsodyFrame
  BE->>DB: Retrieve graph context (recent + relevant)
  BE->>GM: Forced function calling: graph mutation tools
  GM-->>BE: tool calls (upsert nodes/edges + evidence)
  BE->>DB: MERGE upserts + receipts
  BE-->>FE: WS send kg.diff + receipts + insight card
```

_________
## Proxy through fastapi?

- could work since evi offers audioinput and audio output (but really this is optional)

```mermaid

sequenceDiagram
  participant FE as Browser
  participant BE as FastAPI WS Proxy
  participant EVI as EVI WebSocket

  FE->>BE: WS send audio_chunk (binary/base64)
  BE->>EVI: send audio_input {data: base64}
  EVI-->>BE: audio_output + messages
  BE-->>FE: WS relay audio_output + transcripts
```


________

## Audio window fallback

```mermaid

sequenceDiagram
  participant FE as Browser
  participant BE as FastAPI
  participant EVI as EVI (optional)

  FE->>FE: MediaRecorder windows (e.g., 3-5s)
  FE->>BE: POST /v1/sessions/{id}/audio-window (multipart)
  BE-->>FE: {transcript?, prosody?, kg.diff, insight}
  opt Voice still on
    FE->>EVI: (continue direct voice)
  end
```

_________
## Knowledge Graph Diff Ingestion 

```mermaid

sequenceDiagram
  participant BE as FastAPI
  participant DB as Neo4j

  BE->>DB: MERGE session-scoped nodes (label+canonical+sessionId)
  BE->>DB: MERGE relationships (typed edges)
  BE->>DB: Create Mutation/Receipt nodes linked to Utterance
  DB-->>BE: Upserted IDs + stats
  BE-->>BE: Build kg.diff payload (nodesUpsert + edgesUpsert + receipts)
  
```

___________
## Response generation (not voice)

```mermaid

sequenceDiagram
  participant BE as FastAPI
  participant DB as Neo4j
  participant GM as Gemini
  participant FE as Next.js

  BE->>DB: Retrieve evidence subgraph + last turns
  BE->>GM: Structured output: InsightCard {reflection, question, receipts}
  GM-->>BE: JSON adhering to schema
  BE-->>FE: WS send coach.insight {card, receipts}
  
```


_________
## Safety

```mermaid

sequenceDiagram
  participant BE as FastAPI
  participant GM as Gemini
  participant DB as Neo4j
  participant FE as Next.js

  BE->>GM: Structured classification: risk_level + recommended_actions
  GM-->>BE: {risk_level: none|low|medium|high, actions[]}
  BE->>DB: Persist RiskAssessment
  alt high risk
    BE-->>FE: WS send safety.alert + UI guidance
  else
    BE-->>FE: WS send safety.status
  end
```



