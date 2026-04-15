from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from domain.models import GraphSnapshot
from services.neo4j.repo_graph import get_graph_snapshot
from services.neo4j.repo_sessions import get_session_record

router = APIRouter(tags=["graph"])


@router.get("/v1/sessions/{session_id}/graph", response_model=GraphSnapshot)
async def get_session_graph(
    session_id: str,
    limit_nodes: int = Query(default=200, ge=1, le=1000),
    limit_edges: int = Query(default=400, ge=1, le=2000),
) -> GraphSnapshot:
    session = await run_in_threadpool(get_session_record, session_id=session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "session_not_found",
                "message": f"Session {session_id} was not found.",
            },
        )

    snapshot = await run_in_threadpool(
        get_graph_snapshot,
        session_id=session_id,
        node_limit=limit_nodes,
        edge_limit=limit_edges,
    )
    return GraphSnapshot.model_validate(snapshot)
