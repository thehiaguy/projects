from typing import Any
import json

from services.gemini.kg_tools import get_allowed_concept_labels, get_allowed_relationship_types


def build_kg_system_prompt() -> str:
    """
    Purpose:
        Produce the stable instruction prompt that constrains Gemini to evidence-backed KG mutation tool calls.

    Inputs:
        None.

    Returns:
        System prompt string covering:
        - session-scoped graph semantics
        - allowed labels/relationships
        - evidence requirements (`message_id`, exact quote)
        - per-utterance mutation caps
        - behavior when information is ambiguous (emit no mutation rather than guess)

    Data structures / implementation notes:
        - Keep this deterministic and versioned for prompt auditing
        - Mirror validation rules enforced in code to reduce tool-call drift
    """
    labels = ", ".join(get_allowed_concept_labels())
    relationships = ", ".join(get_allowed_relationship_types())
    return (
        "You are the therapy knowledge-graph extraction model for a live session.\n"
        "Your job is to emit only evidence-backed tool calls for the current user utterance.\n"
        "Graph semantics:\n"
        f"- Allowed concept labels: {labels}.\n"
        f"- Allowed concept-to-concept relationships: {relationships}.\n"
        "- Use `link_utterance_mentions` for transcript-to-concept mention edges.\n"
        "- Use `set_session_goal` only when the user clearly states a goal or desired outcome.\n"
        "- Use `skip_kg_update` when the utterance is ambiguous, purely phatic, too vague, or unsupported by evidence.\n"
        "Evidence rules:\n"
        "- Every mutation tool call must include the current `message_id` and an exact `evidence_quote` substring from the utterance text.\n"
        "- Never quote text that is not present verbatim in the current utterance.\n"
        "- If you are not sure, do not guess; call `skip_kg_update`.\n"
        "Safety and scope rules:\n"
        "- The graph is session-scoped. Do not resolve across sessions.\n"
        "- Prosody scores are expression signals, not emotional truth. Use them only as weak supporting context.\n"
        "- Prefer a small number of precise mutations.\n"
        "- Hard caps per utterance: at most 4 node upserts and at most 6 edge upserts.\n"
        "- Do not use tools to store assistant policy, diagnosis, or unsupported clinical claims."
    )


def build_kg_user_prompt(
    *,
    session_id: str,
    utterance_text: str,
    message_id: str,
    prosody_scores: dict[str, float] | None,
    graph_context: dict[str, Any],
) -> str:
    """
    Purpose:
        Build the per-event user prompt that includes transcript text, prosody summary, and local graph context.

    Inputs:
        - `session_id`: current session id
        - `utterance_text`: finalized user transcript text
        - `message_id`: EVI message identifier for evidence attribution
        - `prosody_scores`: optional prosody label->score mapping
        - `graph_context`: recent nodes/edges/top concepts retrieved from Neo4j

    Returns:
        Prompt string suitable for Gemini tool-calling request.

    Data structures / implementation notes:
        - Keep prompt compact to preserve latency
        - Present prosody as "expression signals", not emotional truth
        - Include explicit reminder to quote only text present in `utterance_text`
    """
    context_payload = {
        "top_concepts": graph_context.get("top_concepts", []),
        "recent_edges": graph_context.get("recent_edges", []),
        "candidate_matches": graph_context.get("candidate_matches", []),
    }
    return (
        f"session_id: {session_id}\n"
        f"message_id: {message_id}\n"
        f"utterance_text: {utterance_text}\n"
        f"prosody_summary: {summarize_prosody_for_prompt(prosody_scores)}\n"
        f"graph_context_json: {_compact_json(context_payload)}\n"
        "Select the smallest safe set of tool calls for this utterance.\n"
        "If no evidence-backed mutation is justified, call `skip_kg_update`.\n"
        "When linking mentions, include only concepts grounded in the utterance text."
    )


def summarize_prosody_for_prompt(prosody_scores: dict[str, float] | None, top_k: int = 5) -> str:
    """
    Purpose:
        Convert raw prosody score map into a compact prompt-ready summary string.

    Inputs:
        - `prosody_scores`: mapping of label -> confidence score (0.0-1.0 or provider scale)
        - `top_k`: number of highest scoring labels to include

    Returns:
        Human-readable summary string (or sentinel text when no prosody available).

    Data structures / implementation notes:
        - Sort descending by score
        - Round scores for prompt brevity
        - Preserve deterministic ordering for reproducibility
    """
    if not prosody_scores:
        return "none"

    ranked_scores = sorted(
        ((label, score) for label, score in prosody_scores.items()),
        key=lambda item: item[1],
        reverse=True,
    )[:top_k]
    if not ranked_scores:
        return "none"

    return ", ".join(f"{label}={score:.3f}" for label, score in ranked_scores)


def _compact_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def build_summary_system_prompt() -> str:
    return (
        "You generate a concise rolling session summary for a therapy support UI.\n"
        "Return only valid JSON with keys: summary, top_concepts.\n"
        "- summary must be 1-2 sentences.\n"
        "- top_concepts must be an array of canonical concept strings.\n"
        "- Stay grounded in the provided utterance and graph context.\n"
        "- Do not include markdown."
    )


def build_summary_user_prompt(
    *,
    message_id: str,
    utterance_text: str,
    graph_context: dict[str, Any],
) -> str:
    return (
        f"message_id: {message_id}\n"
        f"utterance_text: {utterance_text}\n"
        f"graph_context_json: {_compact_json(graph_context)}\n"
        "Return the rolling summary JSON."
    )


def build_insight_system_prompt() -> str:
    return (
        "You create one supportive insight card for a frontend therapy UI.\n"
        "Return only valid JSON with keys: reflection, question, focus.\n"
        "- reflection: 1 sentence grounded in the user's words.\n"
        "- question: 1 open-ended follow-up question.\n"
        "- focus: short label for the card's focus.\n"
        "- Do not diagnose. Do not mention hidden model reasoning.\n"
        "- Do not include markdown."
    )


def build_insight_user_prompt(
    *,
    message_id: str,
    utterance_text: str,
    graph_context: dict[str, Any],
    receipts: list[dict[str, Any]],
) -> str:
    return (
        f"message_id: {message_id}\n"
        f"utterance_text: {utterance_text}\n"
        f"graph_context_json: {_compact_json(graph_context)}\n"
        f"receipts_json: {_compact_json({'receipts': receipts})}\n"
        "Return the insight card JSON."
    )


def build_safety_system_prompt() -> str:
    return (
        "You classify conversational safety risk for a frontend support UI.\n"
        "Return only valid JSON with keys: risk_level, recommended_actions, rationale.\n"
        "- risk_level must be one of: none, low, medium, high.\n"
        "- recommended_actions must be an array of short strings.\n"
        "- rationale must be one short sentence.\n"
        "- Be conservative and evidence-grounded.\n"
        "- Do not include markdown."
    )


def build_safety_user_prompt(
    *,
    message_id: str,
    utterance_text: str,
    graph_context: dict[str, Any],
) -> str:
    return (
        f"message_id: {message_id}\n"
        f"utterance_text: {utterance_text}\n"
        f"graph_context_json: {_compact_json(graph_context)}\n"
        "Return the safety JSON."
    )
