from typing import Any

from services.neo4j.driver import execute_read, execute_write


def create_session_record(*, session_id: str, created_at_ms: int) -> dict[str, Any]:
    """
    Purpose:
        Persist a new `Session` node in Neo4j for the given session ID.

    Inputs:
        - `session_id`: generated unique session identifier
        - `created_at_ms`: server timestamp (epoch milliseconds)

    Returns:
        Session record dict with at least:
        - `session_id`
        - `created_at_ms`
        - optional `neo4j_internal_id`

    Data structures / implementation notes:
        - Node schema: `Session {sessionId, createdAt, endedAt?}`
        - Use `MERGE` only if idempotent create semantics are desired; otherwise `CREATE` + uniqueness constraint
    """
    return execute_write(query_fn=_create_session_record_tx, session_id=session_id, created_at_ms=created_at_ms)


def get_session_record(*, session_id: str) -> dict[str, Any] | None:
    """
    Purpose:
        Fetch a session node by `sessionId`.

    Inputs:
        - `session_id`: session identifier to retrieve.

    Returns:
        Session record dict or `None` if not found.

    Data structures / implementation notes:
        - Return normalized keys (`session_id`, `created_at_ms`, `ended_at_ms`) instead of raw Neo4j property names
    """
    return execute_read(query_fn=_get_session_record_tx, session_id=session_id)


def end_session_record(*, session_id: str, ended_at_ms: int) -> dict[str, Any] | None:
    """
    Purpose:
        Mark a session as ended by setting `endedAt` on the `Session` node.

    Inputs:
        - `session_id`: target session id
        - `ended_at_ms`: server timestamp in milliseconds

    Returns:
        Updated session record dict or `None` if session does not exist.

    Data structures / implementation notes:
        - Use `MATCH` on unique `sessionId`
        - Preserve original `createdAt`; only update `endedAt`
    """
    return execute_write(
        query_fn=_end_session_record_tx,
        session_id=session_id,
        ended_at_ms=ended_at_ms,
    )


def _create_session_record_tx(tx: Any, *, session_id: str, created_at_ms: int) -> dict[str, Any]:
    result = tx.run(
        """
        MERGE (s:Session {sessionId: $session_id})
        ON CREATE SET s.createdAt = $created_at_ms
        RETURN s.sessionId AS session_id,
               s.createdAt AS created_at_ms,
               s.endedAt AS ended_at_ms
        """,
        session_id=session_id,
        created_at_ms=created_at_ms,
    )
    record = result.single()
    return _normalize_session_record(record)


def _get_session_record_tx(tx: Any, *, session_id: str) -> dict[str, Any] | None:
    result = tx.run(
        """
        MATCH (s:Session {sessionId: $session_id})
        RETURN s.sessionId AS session_id,
               s.createdAt AS created_at_ms,
               s.endedAt AS ended_at_ms
        """,
        session_id=session_id,
    )
    record = result.single()
    if record is None:
        return None
    return _normalize_session_record(record)


def _end_session_record_tx(tx: Any, *, session_id: str, ended_at_ms: int) -> dict[str, Any] | None:
    result = tx.run(
        """
        MATCH (s:Session {sessionId: $session_id})
        SET s.endedAt = $ended_at_ms
        RETURN s.sessionId AS session_id,
               s.createdAt AS created_at_ms,
               s.endedAt AS ended_at_ms
        """,
        session_id=session_id,
        ended_at_ms=ended_at_ms,
    )
    record = result.single()
    if record is None:
        return None
    return _normalize_session_record(record)


def _normalize_session_record(record: Any) -> dict[str, Any]:
    return {
        "session_id": record["session_id"],
        "created_at_ms": record["created_at_ms"],
        "ended_at_ms": record["ended_at_ms"],
    }
