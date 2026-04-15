from time import time_ns

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from domain.models import SessionRecord, SessionSummary, TopConceptSummary
from services.neo4j.repo_graph import get_top_concepts
from services.neo4j.repo_sessions import create_session_record, end_session_record, get_session_record
from utils.ids import new_session_id
from utils.security import create_session_token

router = APIRouter(tags=["sessions"])


def _now_ms() -> int:
    return time_ns() // 1_000_000


def _build_session_summary(*, top_concepts: list[dict[str, object]]) -> str:
    if not top_concepts:
        return "Session ended. No graph concepts were extracted yet."

    canonicals = [str(item["canonical"]) for item in top_concepts[:3]]
    return "Session ended. Top concepts captured: " + ", ".join(canonicals) + "."


@router.post("/v1/sessions", response_model=SessionRecord)
async def create_session() -> SessionRecord:
    session_record = await run_in_threadpool(
        create_session_record,
        session_id=new_session_id(),
        created_at_ms=_now_ms(),
    )
    session_record["session_token"] = create_session_token(session_id=session_record["session_id"])
    return SessionRecord.model_validate(session_record)


@router.post("/v1/sessions/{session_id}/end", response_model=SessionSummary)
async def end_session(session_id: str) -> SessionSummary:
    existing_session = await run_in_threadpool(get_session_record, session_id=session_id)
    if existing_session is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "session_not_found",
                "message": f"Session {session_id} was not found.",
            },
        )

    ended_session = await run_in_threadpool(
        end_session_record,
        session_id=session_id,
        ended_at_ms=_now_ms(),
    )
    if ended_session is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "session_not_found",
                "message": f"Session {session_id} was not found.",
            },
        )

    top_concepts_raw = await run_in_threadpool(get_top_concepts, session_id=session_id, limit=10)
    top_concepts = [TopConceptSummary.model_validate(item) for item in top_concepts_raw]
    return SessionSummary(
        summary=_build_session_summary(top_concepts=top_concepts_raw),
        top_concepts=top_concepts,
    )
