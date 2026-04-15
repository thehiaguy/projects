from typing import Any
from time import time_ns
import asyncio

from apps.api.core.config import get_gemini_client, get_settings
from apps.api.orchestration.insights import build_coach_insight, build_summary_partial
from apps.api.orchestration.receipts import attach_receipts, validate_evidence_quote_present
from apps.api.orchestration.safety import classify_safety_event
from services.gemini.client import generate_kg_tool_calls
from services.gemini.kg_tools import tool_decls, validate_tool_call_shape
from services.gemini.prompts import build_kg_system_prompt, build_kg_user_prompt
from services.gemini.schemas import get_tool_argument_model, validate_tool_call_batch_limits
from services.neo4j.repo_graph import (
    get_graph_context_for_llm,
    link_utterance_mentions,
    set_session_goal,
    upsert_concept_node,
    upsert_relation_edge,
)
from services.neo4j.repo_utterances import insert_prosody_frame, upsert_utterance
from utils.ids import new_prosody_frame_id, new_utterance_id


def _now_ms() -> int:
    return time_ns() // 1_000_000


async def process_utterance_event(
    *,
    session_id: str,
    evi_user_message: dict[str, Any],
) -> dict[str, Any]:
    if bool(evi_user_message.get("interim")):
        return {
            "kg_diff": {"nodes_upsert": [], "edges_upsert": [], "receipts": [], "warnings": ["interim_ignored"]},
            "tool_calls_applied": {"calls": [], "dropped_calls": []},
            "summary_partial": None,
            "coach_insight": None,
            "safety_event": None,
            "warnings": ["interim_ignored"],
        }

    message_id = str(evi_user_message.get("message_id") or "").strip()
    utterance_text = str(evi_user_message.get("content") or "").strip()
    role = str(evi_user_message.get("role") or "user").strip() or "user"
    timestamp_ms = evi_user_message.get("timestamp_ms")
    prosody_scores = evi_user_message.get("prosody_scores")

    utterance_record = await asyncio.to_thread(
        upsert_utterance,
        utterance_id=new_utterance_id(),
        session_id=session_id,
        role=role,
        text=utterance_text,
        message_id=message_id or None,
        timestamp_ms=timestamp_ms,
    )

    prosody_frame = None
    if message_id and isinstance(prosody_scores, dict) and prosody_scores:
        prosody_frame = await asyncio.to_thread(
            insert_prosody_frame,
            frame_id=new_prosody_frame_id(),
            session_id=session_id,
            message_id=message_id,
            top_json={str(key): float(value) for key, value in prosody_scores.items()},
            created_at_ms=_now_ms(),
        )

    graph_context = await asyncio.to_thread(
        build_graph_context_for_event,
        session_id=session_id,
        utterance_text=utterance_text,
    )

    settings = get_settings()
    response = await generate_kg_tool_calls(
        client=get_gemini_client(),
        model_name=settings.gemini_model_kg,
        system_prompt=build_kg_system_prompt(),
        user_prompt=build_kg_user_prompt(
            session_id=session_id,
            utterance_text=utterance_text,
            message_id=message_id,
            prosody_scores=prosody_scores if isinstance(prosody_scores, dict) else None,
            graph_context=graph_context,
        ),
        tool_declarations=tool_decls(),
    )

    raw_tool_calls = response.get("tool_calls", [])
    dropped_calls: list[dict[str, Any]] = []
    valid_tool_calls: list[dict[str, Any]] = []
    for tool_call in raw_tool_calls:
        try:
            validate_tool_call_shape(tool_call)
            if tool_call["name"] != "skip_kg_update":
                evidence_quote = str(tool_call.get("arguments", {}).get("evidence_quote") or "")
                if not validate_evidence_quote_present(
                    utterance_text=utterance_text,
                    evidence_quote=evidence_quote,
                ):
                    raise ValueError("Tool call evidence quote was not found in the utterance text")
            valid_tool_calls.append(tool_call)
        except Exception as exc:
            dropped_calls.append(
                {
                    "name": tool_call.get("name"),
                    "arguments": tool_call.get("arguments", {}),
                    "status": "dropped",
                    "reason": str(exc),
                }
            )

    try:
        validate_tool_call_batch_limits(tool_calls=valid_tool_calls)
    except Exception as exc:
        dropped_calls.extend(
            {
                "name": tool_call.get("name"),
                "arguments": tool_call.get("arguments", {}),
                "status": "dropped",
                "reason": f"batch_limit_violation: {exc}",
            }
            for tool_call in valid_tool_calls
        )
        valid_tool_calls = []

    mutation_results = await asyncio.to_thread(
        apply_tool_calls_to_graph,
        session_id=session_id,
        tool_calls=valid_tool_calls,
        utterance_record=utterance_record,
    )

    post_update_graph_context = await asyncio.to_thread(
        build_graph_context_for_event,
        session_id=session_id,
        utterance_text=utterance_text,
    )

    receipts = attach_receipts(
        tool_call_results=mutation_results["tool_call_results"],
        utterance_text=utterance_text,
    )

    warnings: list[str] = []
    if prosody_frame is None and prosody_scores:
        warnings.append("prosody_not_persisted")

    summary_partial = await build_summary_partial(
        session_id=session_id,
        message_id=message_id,
        utterance_text=utterance_text,
        graph_context=post_update_graph_context,
    )
    coach_insight = await build_coach_insight(
        message_id=message_id,
        utterance_text=utterance_text,
        graph_context=post_update_graph_context,
        receipts=receipts,
    )
    safety_event_type, safety_payload = await classify_safety_event(
        message_id=message_id,
        utterance_text=utterance_text,
        graph_context=post_update_graph_context,
    )

    return {
        "kg_diff": {
            "nodes_upsert": mutation_results["nodes_upsert"],
            "edges_upsert": mutation_results["edges_upsert"],
            "receipts": receipts,
            "warnings": warnings,
        },
        "tool_calls_applied": {
            "calls": mutation_results["tool_call_results"],
            "dropped_calls": dropped_calls,
        },
        "summary_partial": summary_partial.model_dump(),
        "coach_insight": coach_insight.model_dump(),
        "safety_event": {
            "type": safety_event_type,
            "payload": safety_payload.model_dump(),
        },
        "warnings": warnings,
        "provider_usage": response.get("usage"),
    }


def build_graph_context_for_event(
    *,
    session_id: str,
    utterance_text: str,
) -> dict[str, Any]:
    return get_graph_context_for_llm(session_id=session_id, query_text=utterance_text)


def apply_tool_calls_to_graph(
    *,
    session_id: str,
    tool_calls: list[dict[str, Any]],
    utterance_record: dict[str, Any],
) -> dict[str, Any]:
    nodes_by_id: dict[str, dict[str, Any]] = {}
    edges_by_id: dict[str, dict[str, Any]] = {}
    tool_call_results: list[dict[str, Any]] = []

    for tool_call in tool_calls:
        name = str(tool_call.get("name") or "")
        arguments = dict(tool_call.get("arguments", {}))
        now_ms = _now_ms()
        applied_nodes: list[dict[str, Any]] = []
        applied_edges: list[dict[str, Any]] = []
        status = "applied"

        if name == "skip_kg_update":
            status = "skipped"
        elif name == "upsert_concept_node":
            parsed = get_tool_argument_model(name).model_validate(arguments)
            node = upsert_concept_node(
                session_id=session_id,
                label=parsed.label,
                canonical=parsed.canonical,
                now_ms=now_ms,
            )
            applied_nodes.append(node)
        elif name == "upsert_relation_edge":
            parsed = get_tool_argument_model(name).model_validate(arguments)
            source_node = upsert_concept_node(
                session_id=session_id,
                label=parsed.from_label,
                canonical=parsed.from_canonical,
                now_ms=now_ms,
            )
            target_node = upsert_concept_node(
                session_id=session_id,
                label=parsed.to_label,
                canonical=parsed.to_canonical,
                now_ms=now_ms,
            )
            edge = upsert_relation_edge(
                session_id=session_id,
                from_label=parsed.from_label,
                from_canonical=parsed.from_canonical,
                rel_type=parsed.rel_type,
                to_label=parsed.to_label,
                to_canonical=parsed.to_canonical,
                now_ms=now_ms,
            )
            applied_nodes.extend([source_node, target_node])
            applied_edges.append(edge)
        elif name == "link_utterance_mentions":
            parsed = get_tool_argument_model(name).model_validate(arguments)
            for mention in parsed.mentions:
                node = upsert_concept_node(
                    session_id=session_id,
                    label=mention.label,
                    canonical=mention.canonical,
                    now_ms=now_ms,
                )
                applied_nodes.append(node)
            mention_edges = link_utterance_mentions(
                session_id=session_id,
                utterance_id=utterance_record["utterance_id"],
                mentions=[mention.model_dump() for mention in parsed.mentions],
                now_ms=now_ms,
            )
            applied_edges.extend(mention_edges)
        elif name == "set_session_goal":
            parsed = get_tool_argument_model(name).model_validate(arguments)
            node = set_session_goal(
                session_id=session_id,
                canonical=parsed.canonical,
                now_ms=now_ms,
            )
            applied_nodes.append(node)
        else:
            status = "dropped"

        for node in applied_nodes:
            if node.get("id"):
                nodes_by_id[str(node["id"])] = node
        for edge in applied_edges:
            if edge.get("id"):
                edges_by_id[str(edge["id"])] = edge

        tool_call_results.append(
            {
                "name": name,
                "arguments": arguments,
                "status": status,
                "message_id": arguments.get("message_id") or utterance_record.get("message_id"),
                "session_id": session_id,
                "receipt_id": None,
                "applied_nodes": applied_nodes,
                "applied_edges": applied_edges,
            }
        )

    return {
        "nodes_upsert": list(nodes_by_id.values()),
        "edges_upsert": list(edges_by_id.values()),
        "tool_call_results": tool_call_results,
    }
