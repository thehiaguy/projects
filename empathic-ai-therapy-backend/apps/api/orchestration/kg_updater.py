import time
from typing import Any

from app.deps import get_gemini_client, get_settings
from orchestration.receipts import attach_receipts
from services.gemini import client as gemini_client_module
from services.gemini.kg_tools import tool_decls, validate_tool_call_shape
from services.gemini.prompts import build_kg_system_prompt, build_kg_user_prompt
from services.gemini.schemas import normalize_tool_calls, validate_tool_call_batch_limits
from services.neo4j import repo_graph, repo_utterances
from utils.ids import new_prosody_frame_id, new_utterance_id
from utils.logging import get_logger

logger = get_logger(__name__)


async def process_utterance_event(
    *,
    session_id: str,
    evi_user_message: dict[str, Any],
) -> dict[str, Any]:
    # 1. Drop interim messages
    if evi_user_message.get("interim", False):
        return {
            "kg_diff": {"nodes_upsert": [], "edges_upsert": [], "receipts": []},
            "tool_calls_applied": {"calls": [], "dropped_calls": []},
            "warnings": ["skipped: interim message"],
        }

    message_id: str = evi_user_message.get("message_id", "")
    text: str = evi_user_message.get("content", "")
    role: str = evi_user_message.get("role", "user")
    timestamp_ms: int | None = evi_user_message.get("timestamp_ms")
    prosody_scores: dict[str, float] | None = evi_user_message.get("prosody_scores")

    now_ms = int(time.time() * 1000)

    # 2. Persist Utterance
    utterance_id = new_utterance_id()
    utterance_record = repo_utterances.upsert_utterance(
        utterance_id=utterance_id,
        session_id=session_id,
        role=role,
        text=text,
        message_id=message_id,
        timestamp_ms=timestamp_ms,
    )

    # 3. Persist ProsodyFrame if available
    if prosody_scores:
        frame_id = new_prosody_frame_id()
        repo_utterances.insert_prosody_frame(
            frame_id=frame_id,
            session_id=session_id,
            message_id=message_id,
            top_json=prosody_scores,
            created_at_ms=now_ms,
        )

    # 4. Build graph context
    graph_context = build_graph_context_for_event(
        session_id=session_id,
        utterance_text=text,
    )

    # 5. Build prompts + tool declarations
    settings = get_settings()
    system_prompt = build_kg_system_prompt()
    user_prompt = build_kg_user_prompt(
        session_id=session_id,
        utterance_text=text,
        message_id=message_id,
        prosody_scores=prosody_scores,
        graph_context=graph_context,
    )
    declarations = tool_decls()

    # 6. Call Gemini
    client = get_gemini_client()
    raw_output = await gemini_client_module.generate_kg_tool_calls(
        client=client,
        model_name=settings.gemini_model_kg,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        tool_declarations=declarations,
    )

    # 7. Normalize + validate tool calls
    normalized_calls = normalize_tool_calls(raw_output)

    # Filter out skip_kg_update
    active_calls = [c for c in normalized_calls if c.get("name") != "skip_kg_update"]
    dropped_calls: list[dict[str, Any]] = []

    valid_calls: list[dict[str, Any]] = []
    for call in active_calls:
        try:
            validate_tool_call_shape(call)
            valid_calls.append(call)
        except Exception as exc:
            dropped_calls.append({"call": call, "reason": str(exc)})

    try:
        validate_tool_call_batch_limits(tool_calls=valid_calls)
    except Exception as exc:
        logger.warning("Batch limit exceeded for session %s: %s", session_id, exc)
        valid_calls = valid_calls[:4]

    # 8. Execute Neo4j mutations
    mutation_result = apply_tool_calls_to_graph(
        session_id=session_id,
        tool_calls=valid_calls,
        utterance_record=utterance_record,
    )

    # 9. Build receipts
    receipts = attach_receipts(
        tool_call_results=mutation_result["tool_call_results"],
        utterance_text=text,
    )

    return {
        "kg_diff": {
            "nodes_upsert": mutation_result["nodes_upsert"],
            "edges_upsert": mutation_result["edges_upsert"],
            "receipts": receipts,
        },
        "tool_calls_applied": {
            "calls": [
                {
                    "name": r["tool_name"],
                    "arguments": r["tool_arguments"],
                    "status": "applied",
                    "message_id": r["message_id"],
                }
                for r in mutation_result["tool_call_results"]
            ],
            "dropped_calls": dropped_calls,
        },
        "warnings": [],
    }


def build_graph_context_for_event(
    *,
    session_id: str,
    utterance_text: str,
) -> dict[str, Any]:
    try:
        return repo_graph.get_graph_context_for_llm(
            session_id=session_id,
            query_text=utterance_text,
        )
    except Exception as exc:
        logger.warning("Could not fetch graph context: %s", exc)
        return {"top_concepts": [], "recent_edges": []}


def apply_tool_calls_to_graph(
    *,
    session_id: str,
    tool_calls: list[dict[str, Any]],
    utterance_record: dict[str, Any],
) -> dict[str, Any]:
    nodes_upsert: list[dict[str, Any]] = []
    edges_upsert: list[dict[str, Any]] = []
    tool_call_results: list[dict[str, Any]] = []

    now_ms = int(time.time() * 1000)
    utterance_id = utterance_record.get("utterance_id", "")

    for call in tool_calls:
        name = call["name"]
        args = call["arguments"]
        message_id = args.get("message_id", utterance_record.get("message_id", ""))
        applied_nodes: list[dict[str, Any]] = []
        applied_edges: list[dict[str, Any]] = []

        try:
            if name == "upsert_concept_node":
                node = repo_graph.upsert_concept_node(
                    session_id=session_id,
                    label=args["label"],
                    canonical=args["canonical"],
                    now_ms=now_ms,
                )
                nodes_upsert.append(node)
                applied_nodes.append(node)

            elif name == "upsert_relation_edge":
                edge = repo_graph.upsert_relation_edge(
                    session_id=session_id,
                    from_label=args["from_label"],
                    from_canonical=args["from_canonical"],
                    rel_type=args["rel_type"],
                    to_label=args["to_label"],
                    to_canonical=args["to_canonical"],
                    now_ms=now_ms,
                )
                edges_upsert.append(edge)
                applied_edges.append(edge)

            elif name == "link_utterance_mentions":
                mentions = args.get("mentions", [])
                new_edges = repo_graph.link_utterance_mentions(
                    session_id=session_id,
                    utterance_id=utterance_id,
                    mentions=mentions,
                    now_ms=now_ms,
                )
                edges_upsert.extend(new_edges)
                applied_edges.extend(new_edges)

            elif name == "set_session_goal":
                node = repo_graph.set_session_goal(
                    session_id=session_id,
                    canonical=args["canonical"],
                    now_ms=now_ms,
                )
                nodes_upsert.append(node)
                applied_nodes.append(node)

            tool_call_results.append({
                "tool_name": name,
                "tool_arguments": args,
                "message_id": message_id,
                "session_id": session_id,
                "applied_nodes": applied_nodes,
                "applied_edges": applied_edges,
                "status": "applied",
            })

        except Exception as exc:
            logger.error("Tool call '%s' failed: %s", name, exc)
            tool_call_results.append({
                "tool_name": name,
                "tool_arguments": args,
                "message_id": message_id,
                "session_id": session_id,
                "applied_nodes": [],
                "applied_edges": [],
                "status": "failed",
                "error": str(exc),
            })

    return {
        "nodes_upsert": nodes_upsert,
        "edges_upsert": edges_upsert,
        "tool_call_results": tool_call_results,
    }
