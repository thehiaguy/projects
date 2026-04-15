from typing import Any

from apps.api.core.config import get_gemini_client, get_settings
from apps.api.domain.models import SafetyPayload
from services.gemini.client import generate_json_response
from services.gemini.prompts import build_safety_system_prompt, build_safety_user_prompt

_ALLOWED_RISK_LEVELS = {"none", "low", "medium", "high"}


async def classify_safety_event(
    *,
    message_id: str,
    utterance_text: str,
    graph_context: dict[str, Any],
) -> tuple[str, SafetyPayload]:
    try:
        response = await generate_json_response(
            client=get_gemini_client(),
            model_name=get_settings().gemini_model_kg,
            system_prompt=build_safety_system_prompt(),
            user_prompt=build_safety_user_prompt(
                message_id=message_id,
                utterance_text=utterance_text,
                graph_context=graph_context,
            ),
        )
        content = response["content"]
    except Exception:
        content = {}

    risk_level = str(content.get("risk_level") or "none").strip().lower()
    if risk_level not in _ALLOWED_RISK_LEVELS:
        risk_level = "none"

    recommended_actions = content.get("recommended_actions", [])
    if not isinstance(recommended_actions, list):
        recommended_actions = []
    recommended_actions = [str(action).strip() for action in recommended_actions if str(action).strip()]

    rationale = str(content.get("rationale") or "").strip() or None
    payload = SafetyPayload(
        risk_level=risk_level,
        recommended_actions=recommended_actions,
        message_id=message_id,
        rationale=rationale,
    )
    event_type = "safety.alert" if risk_level in {"medium", "high"} else "safety.status"
    return event_type, payload
