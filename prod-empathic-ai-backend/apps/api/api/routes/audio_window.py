import json
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from domain.models import AudioWindowResponse
from orchestration.kg_updater import process_utterance_event
from services.neo4j.repo_sessions import get_session_record

router = APIRouter(tags=["audio-window"])


@router.post("/v1/sessions/{session_id}/audio-window", response_model=AudioWindowResponse)
async def ingest_audio_window(
    session_id: str,
    file: UploadFile | None = File(default=None),
    transcript_text: str | None = Form(default=None),
    message_id: str | None = Form(default=None),
    timestamp_ms: int | None = Form(default=None),
    prosody_scores_json: str | None = Form(default=None),
) -> AudioWindowResponse:
    session = await run_in_threadpool(get_session_record, session_id=session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "session_not_found",
                "message": f"Session {session_id} was not found.",
            },
        )

    transcript = (transcript_text or "").strip()
    if not transcript:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "audio_window_transcript_required",
                "message": "This audio-window fallback currently requires transcript_text to be provided.",
            },
        )

    prosody_scores = _parse_prosody_scores(prosody_scores_json)
    result = await process_utterance_event(
        session_id=session_id,
        evi_user_message={
            "message_id": message_id or f"audio-window-{uuid4().hex[:12]}",
            "role": "user",
            "content": transcript,
            "interim": False,
            "prosody_scores": prosody_scores,
            "timestamp_ms": timestamp_ms,
            "raw_event": {
                "source": "audio_window",
                "filename": file.filename if file is not None else None,
                "content_type": file.content_type if file is not None else None,
            },
        },
    )

    warnings = list(result.get("warnings", []))
    if file is not None:
        warnings.append("audio_file_received_without_server_side_transcription")

    return AudioWindowResponse(
        transcript=transcript,
        prosody_scores=prosody_scores,
        kg_diff=result["kg_diff"],
        tool_calls_applied=result["tool_calls_applied"],
        summary_partial=result.get("summary_partial"),
        coach_insight=result.get("coach_insight"),
        safety_event=result.get("safety_event"),
        warnings=warnings,
    )


def _parse_prosody_scores(raw_payload: str | None) -> dict[str, float]:
    if not raw_payload:
        return {}

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "invalid_prosody_scores_json",
                "message": "prosody_scores_json must be valid JSON.",
            },
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "invalid_prosody_scores_json",
                "message": "prosody_scores_json must decode to an object.",
            },
        )

    normalized: dict[str, float] = {}
    for key, value in payload.items():
        try:
            normalized[str(key)] = float(value)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "invalid_prosody_score_value",
                    "message": f"Prosody score for {key} must be numeric.",
                },
            ) from exc
    return normalized
