from typing import Any

from domain.enums import ConceptLabel, GraphRelationshipType
from services.gemini.schemas import (
    LinkUtteranceMentionsArgs,
    SetSessionGoalArgs,
    SkipKgUpdateArgs,
    UpsertConceptNodeArgs,
    UpsertRelationEdgeArgs,
    get_tool_argument_model,
)


_EDGE_TOOL_RELATIONSHIP_TYPES = [
    GraphRelationshipType.EVOKES.value,
    GraphRelationshipType.DRIVES.value,
    GraphRelationshipType.LEADS_TO.value,
    GraphRelationshipType.AFFECTS.value,
    GraphRelationshipType.SUPPORTS.value,
    GraphRelationshipType.CONFLICTS_WITH.value,
]


def get_allowed_concept_labels() -> list[str]:
    return ConceptLabel.values()


def get_allowed_relationship_types() -> list[str]:
    return list(_EDGE_TOOL_RELATIONSHIP_TYPES)


def tool_decls() -> list[Any]:
    return [
        _build_structured_tool(
            name="upsert_concept_node",
            description="Create or update exactly one session-scoped concept node supported by explicit evidence from the current utterance.",
            args_schema=UpsertConceptNodeArgs,
        ),
        _build_structured_tool(
            name="upsert_relation_edge",
            description="Create or update exactly one concept-to-concept relationship supported by explicit evidence from the current utterance.",
            args_schema=UpsertRelationEdgeArgs,
        ),
        _build_structured_tool(
            name="link_utterance_mentions",
            description="Link the current utterance to one or more mentioned concepts using MENTIONS edges.",
            args_schema=LinkUtteranceMentionsArgs,
        ),
        _build_structured_tool(
            name="set_session_goal",
            description="Set or update the session goal when the user clearly states a goal, objective, or desired outcome.",
            args_schema=SetSessionGoalArgs,
        ),
        _build_structured_tool(
            name="skip_kg_update",
            description="Use this when no safe evidence-backed graph mutation should be applied for the current utterance.",
            args_schema=SkipKgUpdateArgs,
        ),
    ]


def validate_tool_call_shape(tool_call: dict[str, Any]) -> None:
    if not isinstance(tool_call, dict):
        raise ValueError("Tool call must be a dictionary")

    name = tool_call.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("Tool call must include a non-empty name")

    arguments = tool_call.get("arguments")
    if not isinstance(arguments, dict):
        raise ValueError("Tool call must include dictionary arguments")

    args_model = get_tool_argument_model(name)
    args_model.model_validate(arguments)


def _build_structured_tool(*, name: str, description: str, args_schema: Any) -> Any:
    try:
        from langchain_core.tools import StructuredTool
    except ImportError as exc:
        raise RuntimeError(
            "LangChain tool support requires `langchain-core` to be installed."
        ) from exc

    return StructuredTool.from_function(
        func=_tool_execution_stub,
        name=name,
        description=description,
        args_schema=args_schema,
    )


def _tool_execution_stub(**_: Any) -> str:
    raise RuntimeError("Gemini KG tools are declaration-only and must be executed by the orchestration layer.")
