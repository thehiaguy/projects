import json
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from domain.enums import ConceptLabel, GraphRelationshipType

_ALLOWED_CONCEPT_LABELS = set(ConceptLabel.values())
_ALLOWED_EDGE_TOOL_RELATIONSHIPS = {
    GraphRelationshipType.EVOKES.value,
    GraphRelationshipType.DRIVES.value,
    GraphRelationshipType.LEADS_TO.value,
    GraphRelationshipType.AFFECTS.value,
    GraphRelationshipType.SUPPORTS.value,
    GraphRelationshipType.CONFLICTS_WITH.value,
}


class ToolArgsModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class MentionSpan(ToolArgsModel):
    label: str = Field(min_length=1)
    canonical: str = Field(min_length=1)
    start_char: int | None = Field(default=None, ge=0)
    end_char: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_span(self) -> "MentionSpan":
        if self.label not in _ALLOWED_CONCEPT_LABELS:
            raise ValueError(f"Unsupported concept label: {self.label}")
        if (self.start_char is None) != (self.end_char is None):
            raise ValueError("Mention spans must provide both start_char and end_char, or neither")
        if self.start_char is not None and self.end_char is not None and self.end_char < self.start_char:
            raise ValueError("Mention span end_char must be greater than or equal to start_char")
        return self


class UpsertConceptNodeArgs(ToolArgsModel):
    label: str = Field(min_length=1)
    canonical: str = Field(min_length=1)
    message_id: str = Field(min_length=1)
    evidence_quote: str = Field(min_length=1)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    aliases: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_label(self) -> "UpsertConceptNodeArgs":
        if self.label not in _ALLOWED_CONCEPT_LABELS:
            raise ValueError(f"Unsupported concept label: {self.label}")
        return self


class UpsertRelationEdgeArgs(ToolArgsModel):
    from_label: str = Field(min_length=1)
    from_canonical: str = Field(min_length=1)
    rel_type: str = Field(min_length=1)
    to_label: str = Field(min_length=1)
    to_canonical: str = Field(min_length=1)
    message_id: str = Field(min_length=1)
    evidence_quote: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_edge(self) -> "UpsertRelationEdgeArgs":
        if self.from_label not in _ALLOWED_CONCEPT_LABELS:
            raise ValueError(f"Unsupported from_label: {self.from_label}")
        if self.to_label not in _ALLOWED_CONCEPT_LABELS:
            raise ValueError(f"Unsupported to_label: {self.to_label}")
        if self.rel_type not in _ALLOWED_EDGE_TOOL_RELATIONSHIPS:
            raise ValueError(f"Unsupported rel_type for concept edge tool: {self.rel_type}")
        return self


class LinkUtteranceMentionsArgs(ToolArgsModel):
    utterance_id: str | None = None
    message_id: str = Field(min_length=1)
    evidence_quote: str = Field(min_length=1)
    mentions: list[MentionSpan] = Field(min_length=1)


class SetSessionGoalArgs(ToolArgsModel):
    canonical: str = Field(min_length=1)
    message_id: str = Field(min_length=1)
    evidence_quote: str = Field(min_length=1)
    goal_status: str | None = None
    priority: str | None = None


class SkipKgUpdateArgs(ToolArgsModel):
    message_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)


TOOL_ARGUMENT_MODELS: dict[str, type[ToolArgsModel]] = {
    "upsert_concept_node": UpsertConceptNodeArgs,
    "upsert_relation_edge": UpsertRelationEdgeArgs,
    "link_utterance_mentions": LinkUtteranceMentionsArgs,
    "set_session_goal": SetSessionGoalArgs,
    "skip_kg_update": SkipKgUpdateArgs,
}


def normalize_tool_calls(raw_model_output: Any) -> list[dict[str, Any]]:
    if raw_model_output is None:
        return []

    tool_calls = _extract_tool_calls(raw_model_output)
    if tool_calls:
        normalized: list[dict[str, Any]] = []
        for provider_index, tool_call in enumerate(tool_calls):
            if not isinstance(tool_call, Mapping):
                continue
            normalized.append(
                {
                    "name": str(tool_call.get("name") or ""),
                    "arguments": _coerce_arguments(
                        tool_call.get("args", tool_call.get("arguments", {}))
                    ),
                    "call_id": tool_call.get("id") or tool_call.get("tool_call_id"),
                    "provider_index": provider_index,
                }
            )
        return [tool_call for tool_call in normalized if tool_call["name"]]

    function_call = _extract_single_function_call(raw_model_output)
    if not function_call:
        return []

    return [
        {
            "name": str(function_call.get("name") or ""),
            "arguments": _coerce_arguments(function_call.get("arguments", {})),
            "call_id": function_call.get("id"),
            "provider_index": 0,
        }
    ]


def validate_tool_call_batch_limits(
    *,
    tool_calls: list[dict[str, Any]],
    max_nodes_per_utterance: int = 4,
    max_edges_per_utterance: int = 6,
) -> None:
    node_count = 0
    edge_count = 0

    for tool_call in tool_calls:
        name = str(tool_call.get("name") or "")
        arguments = tool_call.get("arguments", {})

        if name == "upsert_concept_node":
            node_count += 1
        elif name == "set_session_goal":
            node_count += 1
        elif name == "upsert_relation_edge":
            edge_count += 1
        elif name == "link_utterance_mentions":
            mentions = arguments.get("mentions", [])
            edge_count += len(mentions) if isinstance(mentions, list) else 1
        elif name == "skip_kg_update":
            continue

        if node_count > max_nodes_per_utterance:
            raise ValueError(
                f"Tool call batch exceeds max_nodes_per_utterance={max_nodes_per_utterance}"
            )
        if edge_count > max_edges_per_utterance:
            raise ValueError(
                f"Tool call batch exceeds max_edges_per_utterance={max_edges_per_utterance}"
            )


def get_tool_argument_model(tool_name: str) -> type[ToolArgsModel]:
    try:
        return TOOL_ARGUMENT_MODELS[tool_name]
    except KeyError as exc:
        raise ValueError(f"Unsupported tool name: {tool_name}") from exc


def _extract_tool_calls(raw_model_output: Any) -> list[Any]:
    if hasattr(raw_model_output, "tool_calls"):
        tool_calls = getattr(raw_model_output, "tool_calls")
        if isinstance(tool_calls, list):
            return tool_calls

    if isinstance(raw_model_output, Mapping):
        tool_calls = raw_model_output.get("tool_calls")
        if isinstance(tool_calls, list):
            return tool_calls

    return []


def _extract_single_function_call(raw_model_output: Any) -> Mapping[str, Any] | None:
    if hasattr(raw_model_output, "additional_kwargs"):
        additional_kwargs = getattr(raw_model_output, "additional_kwargs")
        if isinstance(additional_kwargs, Mapping):
            function_call = additional_kwargs.get("function_call")
            if isinstance(function_call, Mapping):
                return function_call

    if isinstance(raw_model_output, Mapping):
        additional_kwargs = raw_model_output.get("additional_kwargs")
        if isinstance(additional_kwargs, Mapping):
            function_call = additional_kwargs.get("function_call")
            if isinstance(function_call, Mapping):
                return function_call

    return None


def _coerce_arguments(arguments: Any) -> dict[str, Any]:
    if isinstance(arguments, Mapping):
        return dict(arguments)
    if isinstance(arguments, str):
        try:
            loaded = json.loads(arguments)
        except json.JSONDecodeError:
            return {}
        return loaded if isinstance(loaded, dict) else {}
    return {}
