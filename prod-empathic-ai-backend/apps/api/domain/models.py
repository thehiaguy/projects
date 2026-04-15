from pydantic import BaseModel, ConfigDict, Field


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SessionRecord(DomainModel):
    session_id: str = Field(min_length=1)
    created_at_ms: int = Field(ge=0)
    ended_at_ms: int | None = Field(default=None, ge=0)
    status: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    session_token: str | None = None


class UtteranceRecord(DomainModel):
    utterance_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    role: str = Field(min_length=1)
    text: str = Field(min_length=1)
    message_id: str | None = None
    timestamp_ms: int | None = Field(default=None, ge=0)


class ProsodyFrameRecord(DomainModel):
    frame_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    message_id: str = Field(min_length=1)
    top_scores: dict[str, float] = Field(default_factory=dict)
    created_at_ms: int = Field(ge=0)


class KgNode(DomainModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    canonical: str = Field(min_length=1)
    properties: dict[str, object] = Field(default_factory=dict)


class KgEdge(DomainModel):
    id: str = Field(min_length=1)
    type: str = Field(min_length=1)
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    properties: dict[str, object] = Field(default_factory=dict)


class Receipt(DomainModel):
    receipt_id: str = Field(min_length=1)
    message_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    evidence_quote: str = Field(min_length=1)
    applied_node_ids: list[str] = Field(default_factory=list)
    applied_edge_ids: list[str] = Field(default_factory=list)
    verified: bool = False
    warnings: list[str] = Field(default_factory=list)


class KgDiff(DomainModel):
    nodes_upsert: list[KgNode] = Field(default_factory=list)
    edges_upsert: list[KgEdge] = Field(default_factory=list)
    receipts: list[Receipt] = Field(default_factory=list)


class TopConceptSummary(DomainModel):
    label: str = Field(min_length=1)
    canonical: str = Field(min_length=1)
    mention_count: int | None = Field(default=None, ge=0)
    score: float | None = None


class GraphSnapshot(DomainModel):
    nodes: list[KgNode] = Field(default_factory=list)
    edges: list[KgEdge] = Field(default_factory=list)


class SessionSummary(DomainModel):
    summary: str = Field(min_length=1)
    top_concepts: list[TopConceptSummary] = Field(default_factory=list)


class SummaryPartial(DomainModel):
    summary: str = Field(min_length=1)
    based_on_message_id: str = Field(min_length=1)
    top_concepts: list[TopConceptSummary] = Field(default_factory=list)
    updated_at_ms: int = Field(ge=0)


class CoachInsightCard(DomainModel):
    reflection: str = Field(min_length=1)
    question: str = Field(min_length=1)
    focus: str = Field(min_length=1)


class CoachInsightPayload(DomainModel):
    card: CoachInsightCard
    receipt_ids: list[str] = Field(default_factory=list)
    message_id: str = Field(min_length=1)


class SafetyPayload(DomainModel):
    risk_level: str = Field(min_length=1)
    recommended_actions: list[str] = Field(default_factory=list)
    message_id: str = Field(min_length=1)
    rationale: str | None = None


class AudioWindowResponse(DomainModel):
    transcript: str = Field(min_length=1)
    prosody_scores: dict[str, float] = Field(default_factory=dict)
    kg_diff: dict[str, object] = Field(default_factory=dict)
    tool_calls_applied: dict[str, object] = Field(default_factory=dict)
    summary_partial: SummaryPartial | None = None
    coach_insight: CoachInsightPayload | None = None
    safety_event: dict[str, object] | None = None
    warnings: list[str] = Field(default_factory=list)
