from typing import Any

from fastapi import APIRouter

from services.neo4j import repo_graph

router = APIRouter(tags=["graph"])


@router.get("/v1/sessions/{session_id}/graph")
async def get_session_graph(session_id: str) -> dict[str, list[dict]]:
    snapshot = repo_graph.get_graph_snapshot(session_id=session_id)
    return {
        "nodes": snapshot.get("nodes", []),
        "edges": snapshot.get("edges", []),
    }
