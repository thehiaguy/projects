from typing import Any

from services.neo4j import driver as neo4j_driver


def _record_to_dict(record: Any) -> dict[str, Any]:
    node = record["s"]
    return {
        "session_id": node["sessionId"],
        "created_at_ms": node["createdAt"],
        "ended_at_ms": node.get("endedAt"),
        "status": "ended" if node.get("endedAt") else "active",
    }


def create_session_record(*, session_id: str, created_at_ms: int) -> dict[str, Any]:
    def _tx(tx: Any, session_id: str, created_at_ms: int) -> dict[str, Any]:
        result = tx.run(
            """
            CREATE (s:Session {sessionId: $session_id, createdAt: $created_at_ms})
            RETURN s
            """,
            session_id=session_id,
            created_at_ms=created_at_ms,
        )
        record = result.single()
        return _record_to_dict(record)

    return neo4j_driver.execute_write(
        query_fn=_tx,
        session_id=session_id,
        created_at_ms=created_at_ms,
    )


def get_session_record(*, session_id: str) -> dict[str, Any] | None:
    def _tx(tx: Any, session_id: str) -> dict[str, Any] | None:
        result = tx.run(
            "MATCH (s:Session {sessionId: $session_id}) RETURN s",
            session_id=session_id,
        )
        record = result.single()
        if record is None:
            return None
        return _record_to_dict(record)

    return neo4j_driver.execute_read(query_fn=_tx, session_id=session_id)


def end_session_record(*, session_id: str, ended_at_ms: int) -> dict[str, Any] | None:
    def _tx(tx: Any, session_id: str, ended_at_ms: int) -> dict[str, Any] | None:
        result = tx.run(
            """
            MATCH (s:Session {sessionId: $session_id})
            SET s.endedAt = $ended_at_ms
            RETURN s
            """,
            session_id=session_id,
            ended_at_ms=ended_at_ms,
        )
        record = result.single()
        if record is None:
            return None
        return _record_to_dict(record)

    return neo4j_driver.execute_write(
        query_fn=_tx,
        session_id=session_id,
        ended_at_ms=ended_at_ms,
    )
