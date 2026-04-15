from pydantic import BaseModel, Field


class SessionRecord(BaseModel):
    session_id: str
    created_at_ms: int
    ended_at_ms: int | None = None
    status: str = "active"
    metadata: dict = Field(default_factory=dict)


class UtteranceRecord(BaseModel):
    utterance_id: str
    session_id: str
    role: str
    text: str
    message_id: str | None = None
    timestamp_ms: int | None = None


class ProsodyFrameRecord(BaseModel):
    frame_id: str
    session_id: str
    message_id: str
    top_scores: dict[str, float] = Field(default_factory=dict)
    created_at_ms: int


class KgNode(BaseModel):
    id: str
    label: str
    canonical: str
    properties: dict = Field(default_factory=dict)


class KgEdge(BaseModel):
    id: str
    type: str
    source: str
    target: str
    properties: dict = Field(default_factory=dict)


class Receipt(BaseModel):
    receipt_id: str
    message_id: str
    tool_name: str
    evidence_quote: str
    applied_node_ids: list[str] = Field(default_factory=list)
    applied_edge_ids: list[str] = Field(default_factory=list)
    verified: bool = True
    warnings: list[str] = Field(default_factory=list)


class KgDiff(BaseModel):
    nodes_upsert: list[KgNode] = Field(default_factory=list)
    edges_upsert: list[KgEdge] = Field(default_factory=list)
    receipts: list[Receipt] = Field(default_factory=list)


class GraphSnapshot(BaseModel):
    nodes: list[KgNode] = Field(default_factory=list)
    edges: list[KgEdge] = Field(default_factory=list)


class TopConceptSummary(BaseModel):
    label: str
    canonical: str
    mention_count: int = 0
    score: float = 0.0


class SessionSummary(BaseModel):
    summary: str
    top_concepts: list[TopConceptSummary] = Field(default_factory=list)
