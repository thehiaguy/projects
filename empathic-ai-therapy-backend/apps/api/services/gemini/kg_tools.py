from typing import Any

from vertexai.generative_models import FunctionDeclaration, Tool

from domain.enums import ConceptLabel, GraphRelationshipType
from utils.errors import AppError

_ALLOWED_TOOL_NAMES = {
    "upsert_concept_node",
    "upsert_relation_edge",
    "link_utterance_mentions",
    "set_session_goal",
    "skip_kg_update",
}


def get_allowed_concept_labels() -> list[str]:
    return [e.value for e in ConceptLabel]


def get_allowed_relationship_types() -> list[str]:
    return [e.value for e in GraphRelationshipType]


def tool_decls() -> list[Tool]:
    allowed_labels = get_allowed_concept_labels()
    allowed_rels = get_allowed_relationship_types()

    upsert_concept_node = FunctionDeclaration(
        name="upsert_concept_node",
        description=(
            "Create or update a session-scoped concept node in the knowledge graph. "
            "Only call when there is clear, direct evidence in the utterance text. "
            "Provide an exact quote from the utterance as evidence_quote."
        ),
        parameters={
            "type": "object",
            "properties": {
                "label": {"type": "string", "enum": allowed_labels, "description": "Concept node label type."},
                "canonical": {"type": "string", "description": "Normalized, lowercase, concise concept key (e.g. 'work stress')."},
                "message_id": {"type": "string", "description": "EVI message ID this evidence comes from."},
                "evidence_quote": {"type": "string", "description": "Exact verbatim quote from the utterance supporting this node."},
            },
            "required": ["label", "canonical", "message_id", "evidence_quote"],
        },
    )

    upsert_relation_edge = FunctionDeclaration(
        name="upsert_relation_edge",
        description=(
            "Create or update a typed relationship between two session-scoped concept nodes. "
            "Both nodes must already exist or be created in the same batch."
        ),
        parameters={
            "type": "object",
            "properties": {
                "from_label": {"type": "string", "enum": allowed_labels},
                "from_canonical": {"type": "string"},
                "rel_type": {"type": "string", "enum": allowed_rels, "description": "Typed relationship between the two nodes."},
                "to_label": {"type": "string", "enum": allowed_labels},
                "to_canonical": {"type": "string"},
                "message_id": {"type": "string"},
                "evidence_quote": {"type": "string"},
            },
            "required": ["from_label", "from_canonical", "rel_type", "to_label", "to_canonical", "message_id", "evidence_quote"],
        },
    )

    link_utterance_mentions = FunctionDeclaration(
        name="link_utterance_mentions",
        description="Link the current utterance to concept nodes via MENTIONS relationships.",
        parameters={
            "type": "object",
            "properties": {
                "message_id": {"type": "string"},
                "mentions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string", "enum": allowed_labels},
                            "canonical": {"type": "string"},
                        },
                        "required": ["label", "canonical"],
                    },
                },
                "evidence_quote": {"type": "string"},
            },
            "required": ["message_id", "mentions", "evidence_quote"],
        },
    )

    set_session_goal = FunctionDeclaration(
        name="set_session_goal",
        description="Update the session-level therapeutic goal based on what the user expressed.",
        parameters={
            "type": "object",
            "properties": {
                "canonical": {"type": "string", "description": "Normalized goal description (e.g. 'reduce work anxiety')."},
                "message_id": {"type": "string"},
                "evidence_quote": {"type": "string"},
            },
            "required": ["canonical", "message_id", "evidence_quote"],
        },
    )

    skip_kg_update = FunctionDeclaration(
        name="skip_kg_update",
        description=(
            "Call this when the utterance does not contain enough information to justify "
            "any knowledge graph update. Prefer this over guessing."
        ),
        parameters={
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Brief explanation of why no update is needed."},
            },
            "required": [],
        },
    )

    return [Tool(function_declarations=[
        upsert_concept_node,
        upsert_relation_edge,
        link_utterance_mentions,
        set_session_goal,
        skip_kg_update,
    ])]


def validate_tool_call_shape(tool_call: dict[str, Any]) -> None:
    name = tool_call.get("name")
    if name not in _ALLOWED_TOOL_NAMES:
        raise AppError(
            code="invalid_tool_name",
            message=f"Tool '{name}' is not allowed.",
            http_status=400,
        )

    if name == "skip_kg_update":
        return

    args = tool_call.get("arguments", {})

    # All non-skip tools must have message_id and evidence_quote
    if not args.get("message_id"):
        raise AppError(
            code="missing_message_id",
            message=f"Tool '{name}' requires 'message_id'.",
            http_status=400,
        )
    if not args.get("evidence_quote"):
        raise AppError(
            code="missing_evidence_quote",
            message=f"Tool '{name}' requires 'evidence_quote'.",
            http_status=400,
        )

    allowed_labels = set(get_allowed_concept_labels())
    allowed_rels = set(get_allowed_relationship_types())

    if name == "upsert_concept_node":
        if args.get("label") not in allowed_labels:
            raise AppError(
                code="invalid_concept_label",
                message=f"Label '{args.get('label')}' not allowed.",
                http_status=400,
            )

    if name == "upsert_relation_edge":
        for lbl_key in ("from_label", "to_label"):
            if args.get(lbl_key) not in allowed_labels:
                raise AppError(
                    code="invalid_concept_label",
                    message=f"'{lbl_key}' value '{args.get(lbl_key)}' not allowed.",
                    http_status=400,
                )
        if args.get("rel_type") not in allowed_rels:
            raise AppError(
                code="invalid_relationship_type",
                message=f"rel_type '{args.get('rel_type')}' not allowed.",
                http_status=400,
            )
