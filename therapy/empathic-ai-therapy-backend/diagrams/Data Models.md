
```mermaid
flowchart LR
    U[User]
    S[Session]
    M[Message]
    ES[EmotionSignal]
    SUM[SessionSummary]
    G[Goal]
    C[Concern]
    T[Trigger]
    CS[CopingStrategy]
    P[Pattern]
    R[Relationship]
    B[Belief]
    H[Habit]
    RF[RiskFlag]
    AP[ActionPlan]

    U -->|HAS_SESSION| S
    S -->|HAS_MESSAGE| M
    M -->|HAS_EMOTION_SIGNAL| ES
    S -->|GENERATED_SUMMARY| SUM

    U -->|HAS_GOAL| G
    U -->|HAS_CONCERN| C
    U -->|HAS_TRIGGER| T
    U -->|USES_STRATEGY| CS
    U -->|SHOWS_PATTERN| P
    U -->|HAS_RELATIONSHIP| R
    U -->|HOLDS_BELIEF| B
    U -->|HAS_HABIT| H
    U -->|HAS_RISK_FLAG| RF
    U -->|HAS_ACTION_PLAN| AP

    T -->|AMPLIFIES| C
    CS -->|HELPS_WITH| C
    CS -->|REGULATES| T
    P -->|RELATES_TO| C
    B -->|INFLUENCES| P
    R -->|ASSOCIATED_WITH| T
    SUM -->|UPDATES| G
    SUM -->|UPDATES| C
    SUM -->|UPDATES| P
    RF -->|INFORMS| AP

```



## Identity / structure

- `User`
    
- `Session`
    
- `Message`
    
- `SessionSummary`
    

## Emotional / therapeutic memory

- `EmotionSignal`
    
- `Concern`
    
- `Goal`
    
- `Trigger`
    
- `CopingStrategy`
    
- `Pattern`
    
- `Belief`
    
- `Habit`
    
- `Relationship`
    
- `Topic`
    

## Safety / guidance

- `RiskFlag`
    
- `ActionPlan`
    
- `Resource`
    
- `MoodTrend`
    

---

## Backend Contracts

```mermaid

classDiagram  
    class SessionRecord {  
        +string session_id  
        +int created_at_ms  
        +int ended_at_ms  
        +string status  
        +dict metadata  
    }  
  
    class UtteranceRecord {  
        +string utterance_id  
        +string session_id  
        +string role  
        +string text  
        +string message_id  
        +int timestamp_ms  
    }  
  
    class ProsodyFrameRecord {  
        +string frame_id  
        +string session_id  
        +string message_id  
        +dict top_scores  
        +int created_at_ms  
    }  
  
    class KgNode {  
        +string id  
        +string label  
        +string canonical  
        +dict properties  
    }  
  
    class KgEdge {  
        +string id  
        +string type  
        +string source  
        +string target  
        +dict properties  
    }  
  
    class Receipt {  
        +string receipt_id  
        +string message_id  
        +string tool_name  
        +string evidence_quote  
        +list applied_node_ids  
        +list applied_edge_ids  
        +bool verified  
        +list warnings  
    }  
  
    class KgDiff {  
        +list nodes_upsert  
        +list edges_upsert  
        +list receipts  
    }  
  
    class GraphSnapshot {  
        +list nodes  
        +list edges  
    }  
  
    class TopConceptSummary {  
        +string label  
        +string canonical  
        +int mention_count  
        +float score  
    }  
  
    class SessionSummary {  
        +string summary  
        +list top_concepts  
    }  
  
    class WsEnvelope {  
        +string type  
        +string session_id  
        +dict payload  
        +int sent_at_ms  
        +string correlation_id  
    }  
  
    class EviUserMessagePayload {  
        +string message_id  
        +string role  
        +string content  
        +bool interim  
        +dict prosody_scores  
        +int timestamp_ms  
        +dict raw_event  
    }  
  
    class EviAssistantMessagePayload {  
        +string message_id  
        +string role  
        +string content  
        +int timestamp_ms  
    }  
  
    class KgDiffPayload {  
        +list nodes_upsert  
        +list edges_upsert  
        +list receipts  
        +list warnings  
    }  
  
    class ToolCallsAppliedPayload {  
        +list calls  
        +list dropped_calls  
    }  
  
    class ServerErrorPayload {  
        +string code  
        +string message  
        +string correlation_id  
        +bool retryable  
        +dict details  
    }  
  
    SessionSummary --> TopConceptSummary : contains  
    GraphSnapshot --> KgNode : contains  
    GraphSnapshot --> KgEdge : contains  
    KgDiff --> KgNode : nodes_upsert  
    KgDiff --> KgEdge : edges_upsert  
    KgDiff --> Receipt : receipts  
    KgDiffPayload --> KgNode : nodes_upsert  
    KgDiffPayload --> KgEdge : edges_upsert  
    KgDiffPayload --> Receipt : receipts  
    WsEnvelope --> EviUserMessagePayload : payload for evi.user_message.final  
    WsEnvelope --> EviAssistantMessagePayload : payload for evi.assistant_message  
    WsEnvelope --> KgDiffPayload : payload for kg.diff  
    WsEnvelope --> ToolCallsAppliedPayload : payload for kg.tool_calls_applied  
    WsEnvelope --> ServerErrorPayload : payload for server.error  
  
%% This diagram reflects the data contracts described in implementation-plan.md  
%% and the backend domain/ws scaffolding under apps/api/.
```



_________

## Neo4j Session Graph

```mermaid

erDiagram  
    Session {  
        string sessionId PK  
        int createdAt  
        int endedAt  
        string latestGoalCanonical  
        int goalUpdatedAt  
    }  
  
    Utterance {  
        string utteranceId PK  
        string sessionId FK  
        string role  
        string text  
        string messageId  
        int timestampMs  
        int createdAt  
    }  
  
    ProsodyFrame {  
        string frameId PK  
        string sessionId FK  
        string messageId  
        string topJson  
        int createdAt  
    }  
  
    Person {  
        string sessionId PK  
        string canonical PK  
        int createdAt  
        int lastSeenAt  
    }  
  
    Trigger {  
        string sessionId PK  
        string canonical PK  
        int createdAt  
        int lastSeenAt  
    }  
  
    Emotion {  
        string sessionId PK  
        string canonical PK  
        int createdAt  
        int lastSeenAt  
    }  
  
    Belief {  
        string sessionId PK  
        string canonical PK  
        int createdAt  
        int lastSeenAt  
    }  
  
    Need {  
        string sessionId PK  
        string canonical PK  
        int createdAt  
        int lastSeenAt  
    }  
  
    Goal {  
        string sessionId PK  
        string canonical PK  
        int createdAt  
        int lastSeenAt  
    }  
  
    Action {  
        string sessionId PK  
        string canonical PK  
        int createdAt  
        int lastSeenAt  
    }  
  
    Event {  
        string sessionId PK  
        string canonical PK  
        int createdAt  
        int lastSeenAt  
    }  
  
    Session ||--o{ Utterance : HAS_UTTERANCE  
    Session ||..o{ ProsodyFrame : scopes_by_sessionId  
  
    Utterance ||--o{ Person : MENTIONS  
    Utterance ||--o{ Trigger : MENTIONS  
    Utterance ||--o{ Emotion : MENTIONS  
    Utterance ||--o{ Belief : MENTIONS  
    Utterance ||--o{ Need : MENTIONS  
    Utterance ||--o{ Goal : MENTIONS  
    Utterance ||--o{ Action : MENTIONS  
    Utterance ||--o{ Event : MENTIONS  
  
    Trigger ||--o{ Emotion : EVOKES  
    Belief ||--o{ Emotion : DRIVES  
    Emotion ||--o{ Action : LEADS_TO  
    Action ||--o{ Goal : AFFECTS  
    Need ||--o{ Goal : SUPPORTS  
    Need ||--o{ Goal : CONFLICTS_WITH  
  
%% Notes from implementation-plan.md:  
%% - Session and Utterance use unique single-property constraints.  
%% - Each concept label uses composite uniqueness on (sessionId, canonical).  
%% - ProsodyFrame is stored by session/message metadata; the plan does not require a first-class graph edge for it.
```




___________

## End to End runtime flow


```mermaid

sequenceDiagram  
    participant User  
    participant Web as Next.js Frontend  
    participant Hume as Hume EVI  
    participant API as FastAPI Backend  
    participant Gemini as Gemini KG Extractor  
    participant Neo4j as Neo4j Graph  
  
    User->>Web: Start session  
    Web->>API: POST /v1/sessions  
    API->>Neo4j: Create Session node  
    API-->>Web: Return session_id  
  
    Web->>API: POST /v1/hume/access-token  
    API->>Hume: POST /oauth2-cc/token  
    Hume-->>API: access_token, expires_in  
    API-->>Web: access_token, expires_in  
  
    Web->>Hume: Connect direct EVI websocket  
    User->>Hume: Send live voice audio  
    Hume-->>Web: user_message and prosody events  
    Hume-->>Web: assistant_message and audio_output  
  
    Web->>API: Connect WS /ws/session/{session_id}  
    Web->>API: Send evi.user_message.final  
    API->>Neo4j: Upsert Utterance  
    API->>Neo4j: Insert ProsodyFrame  
    API->>Neo4j: Fetch graph context  
    API->>Gemini: Prompt with forced KG tools  
    Gemini-->>API: Return tool calls or skip_kg_update  
    API->>Neo4j: Apply concept, relation, mention, and goal upserts  
    API-->>Web: Send kg.diff  
    API-->>Web: Send kg.tool_calls_applied  
  
    Web->>API: GET /v1/sessions/{session_id}/graph  
    API->>Neo4j: Fetch graph snapshot  
    API-->>Web: Return nodes and edges  
  
    User->>Web: End session  
    Web->>API: POST /v1/sessions/{session_id}/end  
    API->>Neo4j: Set Session.endedAt and compute top concepts  
    API-->>Web: Return summary and top_concepts  
  
%% Voice stays direct browser <-> Hume.  
%% FastAPI handles the knowledge stream and graph updates.

```
