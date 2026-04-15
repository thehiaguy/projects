from time import time_ns
from typing import Any
import asyncio

from apps.api.core.config import get_gemini_client, get_settings
from apps.api.domain.models import CoachInsightCard, CoachInsightPayload, SummaryPartial, TopConceptSummary
from services.gemini.client import generate_json_response
from services.gemini.prompts import (
    build_insight_system_prompt,
    build_insight_user_prompt,
    build_summary_system_prompt,
    build_summary_user_prompt,
)
from services.neo4j.repo_graph import get_top_concepts


def _now_ms() -> int:
    return time_ns() // 1_000_000


async def build_summary_partial(
    *,
    session_id: str,
    message_id: str,
    utterance_text: str,
    graph_context: dict[str, Any],
) -> SummaryPartial:
    top_concepts_raw = await asyncio.to_thread(get_top_concepts, session_id=session_id, limit=5)
    top_concepts = [TopConceptSummary.model_validate(item) for item in top_concepts_raw]

    try:
        response = await generate_json_response(
            client=get_gemini_client(),
            model_name=get_settings().gemini_model_kg,
            system_prompt=build_summary_system_prompt(),
            user_prompt=build_summary_user_prompt(
                message_id=message_id,
                utterance_text=utterance_text,
                graph_context=graph_context,
            ),
        )
        summary_text = str(response["content"].get("summary") or "").strip()
    except Exception:
        summary_text = ""

    if not summary_text:
        if top_concepts:
            summary_text = (
                "Current session themes: "
                + ", ".join(concept.canonical for concept in top_concepts[:3])
                + "."
            )
        else:
            summary_text = "Current session summary is still forming."

    return SummaryPartial(
        summary=summary_text,
        based_on_message_id=message_id,
        top_concepts=top_concepts,
        updated_at_ms=_now_ms(),
    )


async def build_coach_insight(
    *,
    message_id: str,
    utterance_text: str,
    graph_context: dict[str, Any],
    receipts: list[dict[str, Any]],
) -> CoachInsightPayload:
    try:
        response = await generate_json_response(
            client=get_gemini_client(),
            model_name=get_settings().gemini_model_kg,
            system_prompt=build_insight_system_prompt(),
            user_prompt=build_insight_user_prompt(
                message_id=message_id,
                utterance_text=utterance_text,
                graph_context=graph_context,
                receipts=receipts,
            ),
        )
        content = response["content"]
    except Exception:
        content = {}

    reflection = str(content.get("reflection") or "").strip() or "You are describing something that feels important right now."
    question = str(content.get("question") or "").strip() or "What feels most important about this for you right now?"
    focus = str(content.get("focus") or "").strip() or "Current theme"

    return CoachInsightPayload(
        card=CoachInsightCard(
            reflection=reflection,
            question=question,
            focus=focus,
        ),
        receipt_ids=[str(receipt.get("receipt_id")) for receipt in receipts if receipt.get("receipt_id")],
        message_id=message_id,
    )
