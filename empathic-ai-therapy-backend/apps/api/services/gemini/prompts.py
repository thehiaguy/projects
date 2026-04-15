from typing import Any

from services.gemini.kg_tools import get_allowed_concept_labels, get_allowed_relationship_types


def build_kg_system_prompt() -> str:
    labels = ", ".join(get_allowed_concept_labels())
    rels = ", ".join(get_allowed_relationship_types())
    return f"""You are a therapeutic knowledge graph (KG) extractor. Your sole job is to analyze a user utterance from a therapy conversation and emit precise, evidence-backed knowledge graph mutations using the provided tools.

## Session-scoped graph semantics
- All nodes belong to the current session. Each node is identified by (sessionId, canonical).
- Canonical values must be lowercase, concise, and stable (e.g., "work anxiety" not "My anxiety about work").

## Allowed concept labels
{labels}

## Allowed relationship types
{rels}

## Evidence requirements
- Every tool call MUST include:
  - `message_id`: the EVI message identifier provided in the user prompt
  - `evidence_quote`: an EXACT verbatim substring from the utterance text
- Never infer or hallucinate concepts that are not explicitly stated.
- If a concept is ambiguous, omit it rather than guess.

## Per-utterance limits
- At most 4 `upsert_concept_node` calls per utterance.
- At most 6 `upsert_relation_edge` calls per utterance.
- Prefer `skip_kg_update` when the utterance contains no extractable therapeutic information.

## Behavior rules
- Do not create duplicate nodes for the same concept — use the same canonical form.
- Prosody/emotion signals are hints, not ground truth. Only create Emotion nodes when the user explicitly names an emotion.
- Use `link_utterance_mentions` to connect utterances to the concepts you extract.
- Use `set_session_goal` only when the user clearly states a desired outcome or therapeutic goal.
"""


def build_kg_user_prompt(
    *,
    session_id: str,
    utterance_text: str,
    message_id: str,
    prosody_scores: dict[str, float] | None,
    graph_context: dict[str, Any],
) -> str:
    prosody_summary = summarize_prosody_for_prompt(prosody_scores)
    top_concepts = graph_context.get("top_concepts", [])
    recent_edges = graph_context.get("recent_edges", [])

    concepts_str = (
        "\n".join(f"  - {c['label']}: {c['canonical']}" for c in top_concepts)
        if top_concepts
        else "  (none yet)"
    )
    edges_str = (
        "\n".join(f"  - {e['from']} --[{e['rel']}]--> {e['to']}" for e in recent_edges)
        if recent_edges
        else "  (none yet)"
    )

    return f"""## Current utterance
session_id: {session_id}
message_id: {message_id}

Text: "{utterance_text}"

Expression signals (prosody): {prosody_summary}

## Existing graph context for this session
Top concepts:
{concepts_str}

Recent relationships:
{edges_str}

---
Instructions:
1. Identify therapeutic concepts clearly present in the utterance text above.
2. Call the appropriate tools to upsert nodes, edges, and mentions.
3. Use ONLY text from the utterance above as your evidence_quote.
4. Use message_id = "{message_id}" in every tool call.
5. If nothing extractable is present, call skip_kg_update.
"""


def summarize_prosody_for_prompt(
    prosody_scores: dict[str, float] | None, top_k: int = 5
) -> str:
    if not prosody_scores:
        return "none available"

    sorted_scores = sorted(prosody_scores.items(), key=lambda x: x[1], reverse=True)
    top = sorted_scores[:top_k]
    parts = [f"{label}={score:.2f}" for label, score in top]
    return ", ".join(parts)
