from typing import Any

import json

from services.neo4j.driver import execute_read, execute_write
from apps.api.utils.errors import AppError


def upsert_utterance(
    *,
    utterance_id: str,
    session_id: str,
    role: str,
    text: str,
    message_id: str | None,
    timestamp_ms: int | None,
) -> dict[str, Any]:
    """
    Purpose:
        Persist or update an `Utterance` node and link it to the parent `Session`.

    Inputs:
        - `utterance_id`: internal/stable utterance identifier
        - `session_id`: owning session
        - `role`: `user` or `assistant`
        - `text`: transcript content
        - `message_id`: provider message id (e.g., Hume EVI id)
        - `timestamp_ms`: event timestamp if available

    Returns:
        Utterance record dict including identifiers and stored timestamps.

    Data structures / implementation notes:
        - Node schema: `Utterance {utteranceId, sessionId, role, text, messageId?, timestampMs}`
        - Relationship: `(Session)-[:HAS_UTTERANCE]->(Utterance)`
        - Use uniqueness constraint on `utteranceId`
    """
    return execute_write(
        query_fn=_upsert_utterance_tx,
        utterance_id=utterance_id,
        session_id=session_id,
        role=role,
        text=text,
        message_id=message_id,
        timestamp_ms=timestamp_ms,
    )


def insert_prosody_frame(
    *,
    frame_id: str,
    session_id: str,
    message_id: str,
    top_json: dict[str, float],
    created_at_ms: int,
) -> dict[str, Any]:
    """
    Purpose:
        Store a prosody snapshot associated with a message for later receipts/analysis.

    Inputs:
        - `frame_id`: unique prosody frame id
        - `session_id`: owning session id
        - `message_id`: EVI message id this prosody frame came from
        - `top_json`: compact prosody score map (`label -> score`)
        - `created_at_ms`: server ingest time

    Returns:
        Prosody frame record dict with persisted metadata.

    Data structures / implementation notes:
        - Node schema: `ProsodyFrame {frameId, sessionId, messageId, topJson, createdAt}`
        - Decide whether to serialize `topJson` as JSON string or map property set
    """
    return execute_write(
        query_fn=_insert_prosody_frame_tx,
        frame_id=frame_id,
        session_id=session_id,
        message_id=message_id,
        top_json=top_json,
        created_at_ms=created_at_ms,
    )


def list_recent_utterances(*, session_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """
    Purpose:
        Fetch recent utterances for prompt context, summaries, or transcript recovery on reconnect.

    Inputs:
        - `session_id`: target session
        - `limit`: max utterances to return (most recent first or chronological after reordering)

    Returns:
        List of utterance dicts containing at minimum:
        - `utterance_id`, `role`, `text`, `message_id`, `timestamp_ms`

    Data structures / implementation notes:
        - Keep output ordering explicit/documented
        - Use indexed predicates on `sessionId` and sort by timestamp if available
    """
    return execute_read(
        query_fn=_list_recent_utterances_tx,
        session_id=session_id,
        limit=limit,
    )


def _upsert_utterance_tx(
    tx: Any,
    *,
    utterance_id: str,
    session_id: str,
    role: str,
    text: str,
    message_id: str | None,
    timestamp_ms: int | None,
) -> dict[str, Any]:
    result = tx.run(
        """
        MATCH (s:Session {sessionId: $session_id})
        MERGE (u:Utterance {utteranceId: $utterance_id})
        ON CREATE SET u.createdAt = timestamp()
        SET u.sessionId = $session_id,
            u.role = $role,
            u.text = $text,
            u.messageId = $message_id,
            u.timestampMs = $timestamp_ms
        MERGE (s)-[:HAS_UTTERANCE]->(u)
        RETURN u.utteranceId AS utterance_id,
               u.sessionId AS session_id,
               u.role AS role,
               u.text AS text,
               u.messageId AS message_id,
               u.timestampMs AS timestamp_ms
        """,
        utterance_id=utterance_id,
        session_id=session_id,
        role=role,
        text=text,
        message_id=message_id,
        timestamp_ms=timestamp_ms,
    )
    record = result.single()
    if record is None:
        raise _build_app_error(
            code="neo4j_session_missing",
            message="Cannot store an utterance for a session that does not exist.",
            http_status=404,
            retryable=False,
            details={"session_id": session_id, "utterance_id": utterance_id},
        )
    return _normalize_utterance_record(record)


def _insert_prosody_frame_tx(
    tx: Any,
    *,
    frame_id: str,
    session_id: str,
    message_id: str,
    top_json: dict[str, float],
    created_at_ms: int,
) -> dict[str, Any]:
    result = tx.run(
        """
        MATCH (s:Session {sessionId: $session_id})
        MERGE (p:ProsodyFrame {frameId: $frame_id})
        ON CREATE SET p.createdAt = $created_at_ms
        SET p.sessionId = $session_id,
            p.messageId = $message_id,
            p.topJson = $top_json
        RETURN p.frameId AS frame_id,
               p.sessionId AS session_id,
               p.messageId AS message_id,
               p.topJson AS top_json,
               p.createdAt AS created_at_ms
        """,
        frame_id=frame_id,
        session_id=session_id,
        message_id=message_id,
        top_json=json.dumps(top_json, ensure_ascii=True, sort_keys=True),
        created_at_ms=created_at_ms,
    )
    record = result.single()
    if record is None:
        raise _build_app_error(
            code="neo4j_session_missing",
            message="Cannot store a prosody frame for a session that does not exist.",
            http_status=404,
            retryable=False,
            details={"session_id": session_id, "frame_id": frame_id},
        )
    return _normalize_prosody_frame_record(record)


def _list_recent_utterances_tx(tx: Any, *, session_id: str, limit: int) -> list[dict[str, Any]]:
    result = tx.run(
        """
        MATCH (u:Utterance {sessionId: $session_id})
        WITH u, coalesce(u.timestampMs, u.createdAt, 0) AS sort_key
        ORDER BY sort_key DESC
        LIMIT $limit
        RETURN u.utteranceId AS utterance_id,
               u.sessionId AS session_id,
               u.role AS role,
               u.text AS text,
               u.messageId AS message_id,
               u.timestampMs AS timestamp_ms,
               sort_key
        ORDER BY sort_key ASC
        """,
        session_id=session_id,
        limit=limit,
    )
    return [_normalize_utterance_record(record) for record in result]


def _normalize_utterance_record(record: Any) -> dict[str, Any]:
    return {
        "utterance_id": record["utterance_id"],
        "session_id": record["session_id"],
        "role": record["role"],
        "text": record["text"],
        "message_id": record["message_id"],
        "timestamp_ms": record["timestamp_ms"],
    }


def _normalize_prosody_frame_record(record: Any) -> dict[str, Any]:
    raw_top_json = record["top_json"]
    top_scores = json.loads(raw_top_json) if isinstance(raw_top_json, str) and raw_top_json else {}
    return {
        "frame_id": record["frame_id"],
        "session_id": record["session_id"],
        "message_id": record["message_id"],
        "top_scores": top_scores,
        "created_at_ms": record["created_at_ms"],
    }


def _build_app_error(
    *,
    code: str,
    message: str,
    http_status: int,
    retryable: bool,
    details: dict[str, Any] | None = None,
) -> AppError:
    error = AppError(message)
    error.code = code
    error.message = message
    error.http_status = http_status
    error.retryable = retryable
    error.correlation_id = None
    error.details = details
    return error
