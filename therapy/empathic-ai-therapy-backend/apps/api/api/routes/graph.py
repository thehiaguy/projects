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
    """
    Purpose:
        Return the current graph snapshot for a session so the UI can render or recover after reconnect.

    Inputs:
        - `session_id`: path parameter for the therapy session.
        Optional query parameters (future):
        - `limit_nodes`, `limit_edges`
        - `include_receipts`

    Returns:
        JSON object with shape:
        - `nodes`: `list[dict]`
        - `edges`: `list[dict]`
        Node item (expected):
        - `id`, `label`, `canonical`, `properties`
        Edge item (expected):
        - `id`, `type`, `source`, `target`, `properties`

    Data structures / implementation notes:
        - Data should be session-scoped
        - Query via `services.neo4j.repo_graph.get_graph_snapshot`
        - Preserve stable IDs for frontend diff application
    """
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
