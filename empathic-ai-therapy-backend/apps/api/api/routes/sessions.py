import time
from typing import Any

from fastapi import APIRouter, HTTPException

from services.neo4j import repo_graph, repo_sessions
from utils.ids import new_session_id

router = APIRouter(tags=["sessions"])


@router.post("/v1/sessions")
async def create_session() -> dict[str, Any]:
    session_id = new_session_id()
    created_at_ms = int(time.time() * 1000)
    record = repo_sessions.create_session_record(
        session_id=session_id,
        created_at_ms=created_at_ms,
    )
    return {
        "session_id": record["session_id"],
        "created_at_ms": record["created_at_ms"],
        "status": record.get("status", "active"),
    }


@router.post("/v1/sessions/{session_id}/end")
async def end_session(session_id: str) -> dict[str, Any]:
    ended_at_ms = int(time.time() * 1000)
    record = repo_sessions.end_session_record(
        session_id=session_id,
        ended_at_ms=ended_at_ms,
    )
    if record is None:
        raise HTTPException(status_code=404, detail={"code": "session_not_found", "message": f"Session '{session_id}' not found."})

    top_concepts_raw = repo_graph.get_top_concepts(session_id=session_id, limit=10)
    top_concepts = [
        {
            "label": c["label"],
            "canonical": c["canonical"],
            "mention_count": c["mention_count"],
            "score": c["score"],
        }
        for c in top_concepts_raw
    ]

    summary = _build_summary_text(session_id=session_id, top_concepts=top_concepts)

    return {
        "session_id": session_id,
        "ended_at_ms": ended_at_ms,
        "summary": summary,
        "top_concepts": top_concepts,
    }


def _build_summary_text(*, session_id: str, top_concepts: list[dict[str, Any]]) -> str:
    if not top_concepts:
        return "Session completed. No significant concepts were identified."
    concept_list = ", ".join(
        f"{c['canonical']} ({c['label']})" for c in top_concepts[:5]
    )
    return f"Session completed. Key themes discussed: {concept_list}."
