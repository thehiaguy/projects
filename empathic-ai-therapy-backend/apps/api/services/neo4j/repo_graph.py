from typing import Any

from domain.enums import ConceptLabel, GraphRelationshipType
from services.neo4j import driver as neo4j_driver
from utils.errors import AppError

_ALLOWED_LABELS = {e.value for e in ConceptLabel}
_ALLOWED_REL_TYPES = {e.value for e in GraphRelationshipType}


def validate_concept_label(label: str) -> None:
    if label not in _ALLOWED_LABELS:
        raise AppError(
            code="invalid_concept_label",
            message=f"Label '{label}' is not allowed. Must be one of: {sorted(_ALLOWED_LABELS)}",
            http_status=400,
        )


def validate_relationship_type(rel_type: str) -> None:
    if rel_type not in _ALLOWED_REL_TYPES:
        raise AppError(
            code="invalid_relationship_type",
            message=f"Relationship type '{rel_type}' is not allowed.",
            http_status=400,
        )


def upsert_concept_node(
    *,
    session_id: str,
    label: str,
    canonical: str,
    now_ms: int,
) -> dict[str, Any]:
    validate_concept_label(label)

    def _tx(tx: Any, session_id: str, canonical: str, now_ms: int) -> dict[str, Any]:
        query = f"""
        MERGE (n:{label} {{sessionId: $session_id, canonical: $canonical}})
        ON CREATE SET n.createdAt = $now_ms
        SET n.lastSeenAt = $now_ms
        RETURN n, id(n) AS neo_id
        """
        result = tx.run(query, session_id=session_id, canonical=canonical, now_ms=now_ms)
        record = result.single()
        node = record["n"]
        neo_id = record["neo_id"]
        return {
            "id": f"{label}:{session_id}:{canonical}",
            "label": label,
            "canonical": canonical,
            "properties": {
                "sessionId": node["sessionId"],
                "createdAt": node.get("createdAt"),
                "lastSeenAt": node.get("lastSeenAt"),
                "neo_id": neo_id,
            },
        }

    return neo4j_driver.execute_write(
        query_fn=_tx,
        session_id=session_id,
        canonical=canonical,
        now_ms=now_ms,
    )


def upsert_relation_edge(
    *,
    session_id: str,
    from_label: str,
    from_canonical: str,
    rel_type: str,
    to_label: str,
    to_canonical: str,
    now_ms: int,
) -> dict[str, Any]:
    validate_concept_label(from_label)
    validate_concept_label(to_label)
    validate_relationship_type(rel_type)

    def _tx(
        tx: Any,
        session_id: str,
        from_canonical: str,
        to_canonical: str,
        now_ms: int,
    ) -> dict[str, Any]:
        query = f"""
        MATCH (a:{from_label} {{sessionId: $session_id, canonical: $from_canonical}})
        MATCH (b:{to_label}   {{sessionId: $session_id, canonical: $to_canonical}})
        MERGE (a)-[r:{rel_type}]->(b)
        ON CREATE SET r.createdAt = $now_ms
        SET r.lastSeenAt = $now_ms
        RETURN id(r) AS rel_id
        """
        result = tx.run(
            query,
            session_id=session_id,
            from_canonical=from_canonical,
            to_canonical=to_canonical,
            now_ms=now_ms,
        )
        record = result.single()
        rel_id = record["rel_id"] if record else None
        edge_id = f"{from_label}:{from_canonical}-{rel_type}->{to_label}:{to_canonical}:{session_id}"
        return {
            "id": edge_id,
            "type": rel_type,
            "source": f"{from_label}:{session_id}:{from_canonical}",
            "target": f"{to_label}:{session_id}:{to_canonical}",
            "properties": {"createdAt": now_ms, "neo_rel_id": rel_id},
        }

    return neo4j_driver.execute_write(
        query_fn=_tx,
        session_id=session_id,
        from_canonical=from_canonical,
        to_canonical=to_canonical,
        now_ms=now_ms,
    )


def link_utterance_mentions(
    *,
    session_id: str,
    utterance_id: str,
    mentions: list[dict[str, Any]],
    now_ms: int,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for mention in mentions:
        label = mention["label"]
        canonical = mention["canonical"]
        validate_concept_label(label)

        def _tx(
            tx: Any,
            session_id: str = session_id,
            utterance_id: str = utterance_id,
            label: str = label,
            canonical: str = canonical,
            now_ms: int = now_ms,
        ) -> dict[str, Any]:
            query = f"""
            MATCH (u:Utterance {{utteranceId: $utterance_id}})
            MATCH (c:{label} {{sessionId: $session_id, canonical: $canonical}})
            MERGE (u)-[r:MENTIONS]->(c)
            ON CREATE SET r.createdAt = $now_ms
            RETURN id(r) AS rel_id
            """
            result = tx.run(
                query,
                utterance_id=utterance_id,
                session_id=session_id,
                canonical=canonical,
                now_ms=now_ms,
            )
            record = result.single()
            rel_id = record["rel_id"] if record else None
            return {
                "id": f"MENTIONS:{utterance_id}->{label}:{canonical}",
                "type": "MENTIONS",
                "source": utterance_id,
                "target": f"{label}:{session_id}:{canonical}",
                "properties": {"createdAt": now_ms, "neo_rel_id": rel_id},
            }

        edge = neo4j_driver.execute_write(query_fn=_tx)
        results.append(edge)
    return results


def set_session_goal(
    *,
    session_id: str,
    canonical: str,
    now_ms: int,
) -> dict[str, Any]:
    node = upsert_concept_node(
        session_id=session_id,
        label=ConceptLabel.GOAL.value,
        canonical=canonical,
        now_ms=now_ms,
    )

    def _update_session(tx: Any, session_id: str, canonical: str, now_ms: int) -> None:
        tx.run(
            """
            MATCH (s:Session {sessionId: $session_id})
            SET s.latestGoalCanonical = $canonical, s.goalUpdatedAt = $now_ms
            """,
            session_id=session_id,
            canonical=canonical,
            now_ms=now_ms,
        )

    neo4j_driver.execute_write(
        query_fn=_update_session,
        session_id=session_id,
        canonical=canonical,
        now_ms=now_ms,
    )
    return node


def get_graph_snapshot(
    *, session_id: str, node_limit: int = 200, edge_limit: int = 400
) -> dict[str, list[dict]]:
    def _tx(tx: Any, session_id: str, node_limit: int, edge_limit: int) -> dict:
        # Fetch concept nodes (exclude Session, Utterance, ProsodyFrame)
        node_result = tx.run(
            """
            MATCH (n)
            WHERE n.sessionId = $session_id
              AND NOT n:Session
              AND NOT n:Utterance
              AND NOT n:ProsodyFrame
            RETURN n, labels(n)[0] AS label
            LIMIT $node_limit
            """,
            session_id=session_id,
            node_limit=node_limit,
        )
        nodes = []
        for rec in node_result:
            node = rec["n"]
            lbl = rec["label"]
            nodes.append({
                "id": f"{lbl}:{session_id}:{node['canonical']}",
                "label": lbl,
                "canonical": node["canonical"],
                "properties": {
                    "createdAt": node.get("createdAt"),
                    "lastSeenAt": node.get("lastSeenAt"),
                },
            })

        edge_result = tx.run(
            """
            MATCH (a)-[r]->(b)
            WHERE a.sessionId = $session_id
              AND b.sessionId = $session_id
              AND NOT a:Session
              AND NOT a:Utterance
              AND NOT b:Utterance
            RETURN a, labels(a)[0] AS a_label, r, type(r) AS rel_type, b, labels(b)[0] AS b_label
            LIMIT $edge_limit
            """,
            session_id=session_id,
            edge_limit=edge_limit,
        )
        edges = []
        for rec in edge_result:
            a, b = rec["a"], rec["b"]
            al, bl = rec["a_label"], rec["b_label"]
            edges.append({
                "id": f"{al}:{a['canonical']}-{rec['rel_type']}->{bl}:{b['canonical']}:{session_id}",
                "type": rec["rel_type"],
                "source": f"{al}:{session_id}:{a['canonical']}",
                "target": f"{bl}:{session_id}:{b['canonical']}",
                "properties": {},
            })

        return {"nodes": nodes, "edges": edges}

    return neo4j_driver.execute_read(
        query_fn=_tx,
        session_id=session_id,
        node_limit=node_limit,
        edge_limit=edge_limit,
    )


def get_graph_context_for_llm(*, session_id: str, query_text: str | None = None) -> dict[str, Any]:
    def _tx(tx: Any, session_id: str) -> dict[str, Any]:
        node_result = tx.run(
            """
            MATCH (n)
            WHERE n.sessionId = $session_id
              AND NOT n:Session AND NOT n:Utterance AND NOT n:ProsodyFrame
            RETURN labels(n)[0] AS label, n.canonical AS canonical, n.lastSeenAt AS last_seen
            ORDER BY n.lastSeenAt DESC
            LIMIT 30
            """,
            session_id=session_id,
        )
        top_concepts = [
            {"label": r["label"], "canonical": r["canonical"]}
            for r in node_result
        ]

        edge_result = tx.run(
            """
            MATCH (a)-[r]->(b)
            WHERE a.sessionId = $session_id AND b.sessionId = $session_id
              AND NOT a:Session AND NOT a:Utterance
            RETURN labels(a)[0] AS a_lbl, a.canonical AS a_can,
                   type(r) AS rel, labels(b)[0] AS b_lbl, b.canonical AS b_can
            ORDER BY r.lastSeenAt DESC
            LIMIT 20
            """,
            session_id=session_id,
        )
        recent_edges = [
            {
                "from": f"{r['a_lbl']}:{r['a_can']}",
                "rel": r["rel"],
                "to": f"{r['b_lbl']}:{r['b_can']}",
            }
            for r in edge_result
        ]

        return {"top_concepts": top_concepts, "recent_edges": recent_edges}

    return neo4j_driver.execute_read(query_fn=_tx, session_id=session_id)


def get_top_concepts(*, session_id: str, limit: int = 10) -> list[dict[str, Any]]:
    def _tx(tx: Any, session_id: str, limit: int) -> list[dict[str, Any]]:
        result = tx.run(
            """
            MATCH (n)
            WHERE n.sessionId = $session_id
              AND NOT n:Session AND NOT n:Utterance AND NOT n:ProsodyFrame
            OPTIONAL MATCH (:Utterance)-[:MENTIONS]->(n)
            WITH n, labels(n)[0] AS label, count(*) AS mention_count
            RETURN label, n.canonical AS canonical, mention_count
            ORDER BY mention_count DESC
            LIMIT $limit
            """,
            session_id=session_id,
            limit=limit,
        )
        return [
            {
                "label": r["label"],
                "canonical": r["canonical"],
                "mention_count": r["mention_count"],
                "score": float(r["mention_count"]),
            }
            for r in result
        ]

    return neo4j_driver.execute_read(query_fn=_tx, session_id=session_id, limit=limit)
