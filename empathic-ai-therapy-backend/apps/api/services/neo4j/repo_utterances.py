import json
from typing import Any

from services.neo4j import driver as neo4j_driver


def upsert_utterance(
    *,
    utterance_id: str,
    session_id: str,
    role: str,
    text: str,
    message_id: str | None,
    timestamp_ms: int | None,
) -> dict[str, Any]:
    def _tx(tx: Any, **kw: Any) -> dict[str, Any]:
        result = tx.run(
            """
            MERGE (s:Session {sessionId: $session_id})
            MERGE (u:Utterance {utteranceId: $utterance_id})
            ON CREATE SET
                u.sessionId    = $session_id,
                u.role         = $role,
                u.text         = $text,
                u.messageId    = $message_id,
                u.timestampMs  = $timestamp_ms,
                u.createdAt    = timestamp()
            MERGE (s)-[:HAS_UTTERANCE]->(u)
            RETURN u
            """,
            session_id=session_id,
            utterance_id=utterance_id,
            role=role,
            text=text,
            message_id=message_id,
            timestamp_ms=timestamp_ms,
        )
        record = result.single()
        node = record["u"]
        return {
            "utterance_id": node["utteranceId"],
            "session_id": node["sessionId"],
            "role": node["role"],
            "text": node["text"],
            "message_id": node.get("messageId"),
            "timestamp_ms": node.get("timestampMs"),
        }

    return neo4j_driver.execute_write(query_fn=_tx)


def insert_prosody_frame(
    *,
    frame_id: str,
    session_id: str,
    message_id: str,
    top_json: dict[str, float],
    created_at_ms: int,
) -> dict[str, Any]:
    top_str = json.dumps(top_json)

    def _tx(tx: Any, **kw: Any) -> dict[str, Any]:
        result = tx.run(
            """
            CREATE (p:ProsodyFrame {
                frameId:    $frame_id,
                sessionId:  $session_id,
                messageId:  $message_id,
                topJson:    $top_str,
                createdAt:  $created_at_ms
            })
            RETURN p
            """,
            frame_id=frame_id,
            session_id=session_id,
            message_id=message_id,
            top_str=top_str,
            created_at_ms=created_at_ms,
        )
        record = result.single()
        node = record["p"]
        return {
            "frame_id": node["frameId"],
            "session_id": node["sessionId"],
            "message_id": node["messageId"],
            "top_scores": json.loads(node["topJson"]),
            "created_at_ms": node["createdAt"],
        }

    return neo4j_driver.execute_write(query_fn=_tx)


def list_recent_utterances(*, session_id: str, limit: int = 20) -> list[dict[str, Any]]:
    def _tx(tx: Any, session_id: str, limit: int) -> list[dict[str, Any]]:
        result = tx.run(
            """
            MATCH (s:Session {sessionId: $session_id})-[:HAS_UTTERANCE]->(u:Utterance)
            RETURN u
            ORDER BY u.timestampMs ASC, u.createdAt ASC
            LIMIT $limit
            """,
            session_id=session_id,
            limit=limit,
        )
        rows = []
        for record in result:
            node = record["u"]
            rows.append({
                "utterance_id": node["utteranceId"],
                "session_id": node["sessionId"],
                "role": node["role"],
                "text": node["text"],
                "message_id": node.get("messageId"),
                "timestamp_ms": node.get("timestampMs"),
            })
        return rows

    return neo4j_driver.execute_read(query_fn=_tx, session_id=session_id, limit=limit)
