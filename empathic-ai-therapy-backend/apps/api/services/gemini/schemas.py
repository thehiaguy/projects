from typing import Any, Literal

from pydantic import BaseModel

from domain.enums import ConceptLabel, GraphRelationshipType


class UpsertConceptNodeArgs(BaseModel):
    label: str
    canonical: str
    message_id: str
    evidence_quote: str
    confidence: float | None = None
    aliases: list[str] | None = None
    attributes: dict[str, Any] | None = None

    def model_post_init(self, __context: Any) -> None:
        allowed = {e.value for e in ConceptLabel}
        if self.label not in allowed:
            raise ValueError(f"label must be one of {sorted(allowed)}, got '{self.label}'")


class UpsertRelationEdgeArgs(BaseModel):
    from_label: str
    from_canonical: str
    rel_type: str
    to_label: str
    to_canonical: str
    message_id: str
    evidence_quote: str

    def model_post_init(self, __context: Any) -> None:
        allowed_labels = {e.value for e in ConceptLabel}
        allowed_rels = {e.value for e in GraphRelationshipType}
        for lbl in (self.from_label, self.to_label):
            if lbl not in allowed_labels:
                raise ValueError(f"label '{lbl}' not allowed")
        if self.rel_type not in allowed_rels:
            raise ValueError(f"rel_type '{self.rel_type}' not allowed")


class MentionItem(BaseModel):
    label: str
    canonical: str
    start_char: int | None = None
    end_char: int | None = None


class LinkUtteranceMentionsArgs(BaseModel):
    message_id: str
    mentions: list[MentionItem]
    evidence_quote: str


class SetSessionGoalArgs(BaseModel):
    canonical: str
    message_id: str
    evidence_quote: str
    goal_status: str | None = None
    priority: int | None = None


class SkipKgUpdateArgs(BaseModel):
    reason: str = ""


def normalize_tool_calls(raw_model_output: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert Gemini SDK raw output to provider-agnostic tool call list."""
    tool_calls = raw_model_output.get("tool_calls", [])
    normalized: list[dict[str, Any]] = []
    for i, call in enumerate(tool_calls):
        normalized.append({
            "name": call.get("name", ""),
            "arguments": call.get("arguments", {}),
            "provider_index": i,
        })
    return normalized


def validate_tool_call_batch_limits(
    *,
    tool_calls: list[dict[str, Any]],
    max_nodes_per_utterance: int = 4,
    max_edges_per_utterance: int = 6,
) -> None:
    from utils.errors import AppError

    node_count = sum(1 for c in tool_calls if c.get("name") == "upsert_concept_node")
    edge_count = sum(1 for c in tool_calls if c.get("name") == "upsert_relation_edge")

    if node_count > max_nodes_per_utterance:
        raise AppError(
            code="batch_limit_exceeded",
            message=f"Too many node upserts ({node_count} > {max_nodes_per_utterance}) per utterance.",
            http_status=400,
        )
    if edge_count > max_edges_per_utterance:
        raise AppError(
            code="batch_limit_exceeded",
            message=f"Too many edge upserts ({edge_count} > {max_edges_per_utterance}) per utterance.",
            http_status=400,
        )
