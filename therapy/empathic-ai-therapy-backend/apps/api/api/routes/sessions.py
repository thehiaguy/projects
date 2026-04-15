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
    """
    Purpose:
        Create a new therapy conversation session and persist the `Session` node in Neo4j.

    Inputs:
        Request body should be optional/minimal for hackathon mode. If added, support:
        - `client_metadata` (device/app version)
        - `started_at_ms` override (optional; server should still generate canonical timestamp)

    Returns:
        JSON object with shape:
        - `{"session_id": "<string>"}` (required)
        Optional later:
        - `created_at_ms`, `status`

    Data structures / implementation notes:
        - Generate session IDs in `utils.ids`
        - Use `services.neo4j.repo_sessions.create_session_record`
        - Session node schema from plan: `Session {sessionId, createdAt, endedAt?}`
    """
    session_record = await run_in_threadpool(
        create_session_record,
        session_id=new_session_id(),
        created_at_ms=_now_ms(),
    )
    session_record["session_token"] = create_session_token(session_id=session_record["session_id"])
    return SessionRecord.model_validate(session_record)


@router.post("/v1/sessions/{session_id}/end", response_model=SessionSummary)
async def end_session(session_id: str) -> SessionSummary:
    """
    Purpose:
        Mark a session as ended, compute/return session summary, and expose top concepts for the UI.

    Inputs:
        - `session_id`: path parameter identifying the conversation session.
        Optional request body (future):
        - `ended_at_ms`
        - `include_graph_snapshot` flag

    Returns:
        JSON object with shape:
        - `summary`: `str`
        - `top_concepts`: `list[dict]`
        Where each top concept item should include at minimum:
        - `label`, `canonical`, `mention_count` or `score`

    Data structures / implementation notes:
        - Persist `endedAt` on the Session node
        - Summary may be produced from Neo4j graph + transcript history
        - Failure should not destroy already stored session state
    """
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
