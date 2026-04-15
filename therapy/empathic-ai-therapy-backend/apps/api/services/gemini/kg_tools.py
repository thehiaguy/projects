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
    """
    Purpose:
        Return the allowed session-scoped concept node labels for KG mutations.

    Inputs:
        None.

    Returns:
        Ordered list of allowed labels, expected to include:
        `Person`, `Trigger`, `Emotion`, `Belief`, `Need`, `Goal`, `Action`, `Event`.

    Data structures / implementation notes:
        - Single source of truth used by prompt construction and tool schema generation
        - Keep in sync with Neo4j validation in `repo_graph.py`
    """
    return ConceptLabel.values()


def get_allowed_relationship_types() -> list[str]:
    """
    Purpose:
        Return the allowed KG relationship types used for graph edge upserts.

    Inputs:
        None.

    Returns:
        List of relationship type strings, including plan-defined types such as:
        `EVOKES`, `DRIVES`, `LEADS_TO`, `AFFECTS`, `SUPPORTS`, `CONFLICTS_WITH`.

    Data structures / implementation notes:
        - This list is intentionally limited to concept-to-concept relationships.
        - `MENTIONS` is handled separately by the dedicated `link_utterance_mentions` tool.
    """
    return list(_EDGE_TOOL_RELATIONSHIP_TYPES)


def tool_decls() -> list[Any]:
    """
    Purpose:
        Build the Gemini function declaration schemas for KG updates (node/edge/mention/goal tools).

    Inputs:
        None. Uses allowed labels/relations from helper functions/constants.

    Returns:
        List of JSON-schema-like function declarations, each with:
        - `name`
        - `description`
        - `parameters` (`type: object`, `properties`, `required`)

    Data structures / implementation notes:
        Required tool set from plan:
        - `upsert_concept_node`
        - `upsert_relation_edge`
        - `link_utterance_mentions`
        - `set_session_goal`
        Include evidence fields: `message_id`, `evidence_quote`.
    """
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
    """
    Purpose:
        Perform backend-side validation on a normalized Gemini tool call before execution.

    Inputs:
        - `tool_call`: dict containing at minimum `name` and `arguments`.

    Returns:
        None. Raises validation error if invalid.

    Data structures / implementation notes:
        - Check tool name is allowed
        - Enforce required evidence fields
        - Enforce allowed labels/relationship enums
        - Additional limits (max calls per utterance) belong in orchestration-level validation
    """
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
