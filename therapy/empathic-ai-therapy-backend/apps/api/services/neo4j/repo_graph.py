from typing import Any

from domain.enums import ConceptLabel, GraphRelationshipType
from services.neo4j.driver import execute_read, execute_write

_CONCEPT_RELATIONSHIP_TYPES = {
    GraphRelationshipType.EVOKES.value,
    GraphRelationshipType.DRIVES.value,
    GraphRelationshipType.LEADS_TO.value,
    GraphRelationshipType.AFFECTS.value,
    GraphRelationshipType.SUPPORTS.value,
    GraphRelationshipType.CONFLICTS_WITH.value,
}


def validate_concept_label(label: str) -> None:
    """
    Purpose:
        Ensure concept node labels used in KG mutations are from the approved enum/set.

    Inputs:
        - `label`: proposed Neo4j node label from tool call or API layer.

    Returns:
        None. Raises validation error if unsupported.

    Data structures / implementation notes:
        - Allowed labels come from plan (`Person`, `Trigger`, `Emotion`, etc.)
        - Do not interpolate unvalidated labels into Cypher
    """
    if label not in ConceptLabel.values():
        raise ValueError(f"Unsupported concept label: {label}")


def validate_relationship_type(rel_type: str) -> None:
    """
    Purpose:
        Ensure KG relationship type is allowed before Cypher execution.

    Inputs:
        - `rel_type`: proposed relationship type string.

    Returns:
        None. Raises validation error if unsupported.

    Data structures / implementation notes:
        - Prevent arbitrary Cypher injection via relationship type interpolation
    """
    if rel_type not in _CONCEPT_RELATIONSHIP_TYPES:
        raise ValueError(f"Unsupported concept relationship type: {rel_type}")


def upsert_concept_node(
    *,
    session_id: str,
    label: str,
    canonical: str,
    now_ms: int,
) -> dict[str, Any]:
    """
    Purpose:
        MERGE a session-scoped concept node and update `lastSeenAt`.

    Inputs:
        - `session_id`: session scope key
        - `label`: concept label (validated)
        - `canonical`: canonical text key
        - `now_ms`: current timestamp for `createdAt`/`lastSeenAt`

    Returns:
        Node payload dict for frontend diffing, e.g.:
        - `id`, `label`, `canonical`, `properties`

    Data structures / implementation notes:
        - Composite uniqueness by `(sessionId, canonical)` per label
        - Use `MERGE` + `ON CREATE SET` + `SET lastSeenAt`
    """
    validate_concept_label(label)
    canonical = _normalize_canonical(canonical)
    return execute_write(
        query_fn=_upsert_concept_node_tx,
        session_id=session_id,
        label=label,
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
    """
    Purpose:
        MERGE a validated relationship between two session-scoped concept nodes.

    Inputs:
        - `session_id`
        - `from_label`, `from_canonical`
        - `rel_type`
        - `to_label`, `to_canonical`
        - `now_ms`

    Returns:
        Edge payload dict for frontend diffing, e.g.:
        - `id`, `type`, `source`, `target`, `properties`

    Data structures / implementation notes:
        - Validate labels and relationship type before building Cypher
        - `MATCH`/`MERGE` node patterns should remain session-scoped
        - Set `createdAt`/`lastSeenAt` on relationship properties
    """
    validate_concept_label(from_label)
    validate_concept_label(to_label)
    validate_relationship_type(rel_type)
    return execute_write(
        query_fn=_upsert_relation_edge_tx,
        session_id=session_id,
        from_label=from_label,
        from_canonical=_normalize_canonical(from_canonical),
        rel_type=rel_type,
        to_label=to_label,
        to_canonical=_normalize_canonical(to_canonical),
        now_ms=now_ms,
    )


def link_utterance_mentions(
    *,
    session_id: str,
    utterance_id: str,
    mentions: list[dict[str, Any]],
    now_ms: int,
) -> list[dict[str, Any]]:
    """
    Purpose:
        Create `MENTIONS` relationships from one `Utterance` node to one or more concept nodes.

    Inputs:
        - `session_id`: session scope
        - `utterance_id`: stored utterance node id/key
        - `mentions`: list of mention objects with required keys:
          `label`, `canonical`; optional `start_char`, `end_char`
        - `now_ms`: timestamp for edge metadata

    Returns:
        List of edge payload dicts for diff emission.

    Data structures / implementation notes:
        - Ensure concept nodes exist (upsert before linking or enforce dependency in orchestration)
        - Relationship type is fixed: `MENTIONS`
    """
    if not mentions:
        return []

    normalized_mentions = [_normalize_mention(mention) for mention in mentions]
    return execute_write(
        query_fn=_link_utterance_mentions_tx,
        session_id=session_id,
        utterance_id=utterance_id,
        mentions=normalized_mentions,
        now_ms=now_ms,
    )


def set_session_goal(
    *,
    session_id: str,
    canonical: str,
    now_ms: int,
) -> dict[str, Any]:
    """
    Purpose:
        Upsert the session goal concept and apply any session-level goal metadata.

    Inputs:
        - `session_id`: session scope
        - `canonical`: normalized goal text
        - `now_ms`: timestamp for create/update metadata

    Returns:
        Goal node payload dict for inclusion in `kg.diff`.

    Data structures / implementation notes:
        - Goal is still modeled as session-scoped `Goal` concept node
        - Optional future behavior: also mirror latest goal onto `Session` node properties
    """
    canonical = _normalize_canonical(canonical)
    return execute_write(
        query_fn=_set_session_goal_tx,
        session_id=session_id,
        canonical=canonical,
        now_ms=now_ms,
    )


def get_graph_snapshot(*, session_id: str, node_limit: int = 200, edge_limit: int = 400) -> dict[str, list[dict]]:
    """
    Purpose:
        Fetch the current graph for a session in a frontend-friendly node/edge format.

    Inputs:
        - `session_id`: session id
        - `node_limit`: cap number of nodes returned
        - `edge_limit`: cap number of edges returned

    Returns:
        Dict with keys:
        - `nodes`: list of node payload dicts
        - `edges`: list of edge payload dicts

    Data structures / implementation notes:
        - Exclude noise labels if needed (`Session`, `ProsodyFrame`) or return separately
        - Ensure node IDs match IDs used in live diff events
    """
    nodes = execute_read(
        query_fn=_get_graph_nodes_tx,
        session_id=session_id,
        node_limit=node_limit,
    )
    edges_with_nodes = execute_read(
        query_fn=_get_graph_edges_tx,
        session_id=session_id,
        edge_limit=edge_limit,
    )

    node_map: dict[str, dict[str, Any]] = {node["id"]: node for node in nodes}
    edges: list[dict[str, Any]] = []

    for row in edges_with_nodes:
        source_node = row["source_node"]
        target_node = row["target_node"]
        node_map.setdefault(source_node["id"], source_node)
        node_map.setdefault(target_node["id"], target_node)
        edges.append(row["edge"])

    return {"nodes": list(node_map.values()), "edges": edges}


def get_graph_context_for_llm(*, session_id: str, query_text: str | None = None) -> dict[str, Any]:
    """
    Purpose:
        Retrieve compact graph context (recent nodes/edges/top concepts) for Gemini KG extraction prompts.

    Inputs:
        - `session_id`: session id
        - `query_text`: optional search hint for full-text concept lookup

    Returns:
        Context dict intended for prompt construction, for example:
        - `top_concepts: list[dict]`
        - `recent_edges: list[dict]`
        - `candidate_matches: list[dict]`

    Data structures / implementation notes:
        - May use Neo4j full-text index for concept lookup by canonical text
        - Keep payload size bounded for low-latency prompting
    """
    return {
        "top_concepts": get_top_concepts(session_id=session_id, limit=8),
        "recent_edges": execute_read(
            query_fn=_get_recent_edges_for_llm_tx,
            session_id=session_id,
            limit=8,
        ),
        "candidate_matches": execute_read(
            query_fn=_get_candidate_matches_for_llm_tx,
            session_id=session_id,
            query_text=(query_text or "").strip(),
            limit=5,
        ),
    }


def get_top_concepts(*, session_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """
    Purpose:
        Compute top concepts for session summary/endpoints based on mention frequency or recency weighting.

    Inputs:
        - `session_id`: target session
        - `limit`: max concepts to return

    Returns:
        List of concept summary dicts including:
        - `label`, `canonical`, `score` and/or `mention_count`

    Data structures / implementation notes:
        - Define scoring method explicitly to keep UI stable
    """
    return execute_read(
        query_fn=_get_top_concepts_tx,
        session_id=session_id,
        limit=limit,
    )


def _upsert_concept_node_tx(
    tx: Any,
    *,
    session_id: str,
    label: str,
    canonical: str,
    now_ms: int,
) -> dict[str, Any]:
    result = tx.run(
        f"""
        MERGE (n:{label} {{sessionId: $session_id, canonical: $canonical}})
        ON CREATE SET n.createdAt = $now_ms
        SET n.lastSeenAt = $now_ms
        RETURN labels(n) AS labels, properties(n) AS props
        """,
        session_id=session_id,
        canonical=canonical,
        now_ms=now_ms,
    )
    record = result.single()
    return _node_payload_from_labels_and_props(record["labels"], record["props"])


def _upsert_relation_edge_tx(
    tx: Any,
    *,
    session_id: str,
    from_label: str,
    from_canonical: str,
    rel_type: str,
    to_label: str,
    to_canonical: str,
    now_ms: int,
) -> dict[str, Any]:
    result = tx.run(
        f"""
        MERGE (source:{from_label} {{sessionId: $session_id, canonical: $from_canonical}})
        ON CREATE SET source.createdAt = $now_ms
        SET source.lastSeenAt = $now_ms
        MERGE (target:{to_label} {{sessionId: $session_id, canonical: $to_canonical}})
        ON CREATE SET target.createdAt = $now_ms
        SET target.lastSeenAt = $now_ms
        MERGE (source)-[r:{rel_type}]->(target)
        ON CREATE SET r.createdAt = $now_ms
        SET r.lastSeenAt = $now_ms
        RETURN labels(source) AS source_labels,
               properties(source) AS source_props,
               labels(target) AS target_labels,
               properties(target) AS target_props,
               type(r) AS rel_type,
               properties(r) AS rel_props
        """,
        session_id=session_id,
        from_canonical=from_canonical,
        to_canonical=to_canonical,
        now_ms=now_ms,
    )
    record = result.single()
    source_node = _node_payload_from_labels_and_props(record["source_labels"], record["source_props"])
    target_node = _node_payload_from_labels_and_props(record["target_labels"], record["target_props"])
    return _edge_payload(
        rel_type=record["rel_type"],
        rel_props=record["rel_props"],
        source_node=source_node,
        target_node=target_node,
    )


def _link_utterance_mentions_tx(
    tx: Any,
    *,
    session_id: str,
    utterance_id: str,
    mentions: list[dict[str, Any]],
    now_ms: int,
) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for mention in mentions:
        label = mention["label"]
        result = tx.run(
            f"""
            MATCH (u:Utterance {{sessionId: $session_id, utteranceId: $utterance_id}})
            MERGE (c:{label} {{sessionId: $session_id, canonical: $canonical}})
            ON CREATE SET c.createdAt = $now_ms
            SET c.lastSeenAt = $now_ms
            MERGE (u)-[r:MENTIONS]->(c)
            ON CREATE SET r.createdAt = $now_ms
            SET r.lastSeenAt = $now_ms,
                r.startChar = $start_char,
                r.endChar = $end_char
            RETURN labels(u) AS source_labels,
                   properties(u) AS source_props,
                   labels(c) AS target_labels,
                   properties(c) AS target_props,
                   type(r) AS rel_type,
                   properties(r) AS rel_props
            """,
            session_id=session_id,
            utterance_id=utterance_id,
            canonical=mention["canonical"],
            start_char=mention.get("start_char"),
            end_char=mention.get("end_char"),
            now_ms=now_ms,
        )
        record = result.single()
        if record is None:
            raise ValueError(f"Utterance not found for mention linkage: {utterance_id}")
        source_node = _node_payload_from_labels_and_props(record["source_labels"], record["source_props"])
        target_node = _node_payload_from_labels_and_props(record["target_labels"], record["target_props"])
        edges.append(
            _edge_payload(
                rel_type=record["rel_type"],
                rel_props=record["rel_props"],
                source_node=source_node,
                target_node=target_node,
            )
        )
    return edges


def _set_session_goal_tx(tx: Any, *, session_id: str, canonical: str, now_ms: int) -> dict[str, Any]:
    result = tx.run(
        """
        MATCH (s:Session {sessionId: $session_id})
        MERGE (g:Goal {sessionId: $session_id, canonical: $canonical})
        ON CREATE SET g.createdAt = $now_ms
        SET g.lastSeenAt = $now_ms,
            s.latestGoalCanonical = $canonical,
            s.goalUpdatedAt = $now_ms
        RETURN labels(g) AS labels, properties(g) AS props
        """,
        session_id=session_id,
        canonical=canonical,
        now_ms=now_ms,
    )
    record = result.single()
    if record is None:
        raise ValueError(f"Session not found for goal update: {session_id}")
    return _node_payload_from_labels_and_props(record["labels"], record["props"])


def _get_graph_nodes_tx(tx: Any, *, session_id: str, node_limit: int) -> list[dict[str, Any]]:
    result = tx.run(
        """
        MATCH (n)
        WHERE n.sessionId = $session_id
          AND NOT 'Session' IN labels(n)
          AND NOT 'ProsodyFrame' IN labels(n)
        WITH labels(n) AS labels, properties(n) AS props,
             coalesce(n.lastSeenAt, n.timestampMs, n.createdAt, 0) AS sort_key
        ORDER BY sort_key DESC
        LIMIT $node_limit
        RETURN labels, props
        """,
        session_id=session_id,
        node_limit=node_limit,
    )
    return [_node_payload_from_labels_and_props(record["labels"], record["props"]) for record in result]


def _get_graph_edges_tx(tx: Any, *, session_id: str, edge_limit: int) -> list[dict[str, Any]]:
    result = tx.run(
        """
        MATCH (source)-[r]->(target)
        WHERE source.sessionId = $session_id
          AND target.sessionId = $session_id
          AND NOT 'Session' IN labels(source)
          AND NOT 'Session' IN labels(target)
          AND NOT 'ProsodyFrame' IN labels(source)
          AND NOT 'ProsodyFrame' IN labels(target)
          AND type(r) <> 'HAS_UTTERANCE'
        WITH labels(source) AS source_labels,
             properties(source) AS source_props,
             labels(target) AS target_labels,
             properties(target) AS target_props,
             type(r) AS rel_type,
             properties(r) AS rel_props,
             coalesce(r.lastSeenAt, r.createdAt, 0) AS sort_key
        ORDER BY sort_key DESC
        LIMIT $edge_limit
        RETURN source_labels, source_props, target_labels, target_props, rel_type, rel_props
        """,
        session_id=session_id,
        edge_limit=edge_limit,
    )

    rows: list[dict[str, Any]] = []
    for record in result:
        source_node = _node_payload_from_labels_and_props(record["source_labels"], record["source_props"])
        target_node = _node_payload_from_labels_and_props(record["target_labels"], record["target_props"])
        rows.append(
            {
                "source_node": source_node,
                "target_node": target_node,
                "edge": _edge_payload(
                    rel_type=record["rel_type"],
                    rel_props=record["rel_props"],
                    source_node=source_node,
                    target_node=target_node,
                ),
            }
        )
    return rows


def _get_recent_edges_for_llm_tx(tx: Any, *, session_id: str, limit: int) -> list[dict[str, Any]]:
    result = tx.run(
        """
        MATCH (source)-[r]->(target)
        WHERE source.sessionId = $session_id
          AND target.sessionId = $session_id
          AND type(r) IN $relationship_types
        RETURN labels(source)[0] AS from_label,
               source.canonical AS from_canonical,
               type(r) AS rel_type,
               labels(target)[0] AS to_label,
               target.canonical AS to_canonical,
               coalesce(r.lastSeenAt, r.createdAt, 0) AS last_seen_at_ms
        ORDER BY last_seen_at_ms DESC
        LIMIT $limit
        """,
        session_id=session_id,
        relationship_types=list(_CONCEPT_RELATIONSHIP_TYPES),
        limit=limit,
    )
    return [dict(record) for record in result]


def _get_candidate_matches_for_llm_tx(
    tx: Any,
    *,
    session_id: str,
    query_text: str,
    limit: int,
) -> list[dict[str, Any]]:
    if not query_text:
        return []

    try:
        result = tx.run(
            """
            CALL db.index.fulltext.queryNodes("concept_canonical_fulltext", $query_text, {limit: $limit})
            YIELD node, score
            WHERE node.sessionId = $session_id
            RETURN labels(node)[0] AS label,
                   node.canonical AS canonical,
                   score
            ORDER BY score DESC
            LIMIT $limit
            """,
            query_text=query_text,
            session_id=session_id,
            limit=limit,
        )
        rows = [dict(record) for record in result]
        if rows:
            return rows
    except Exception:
        pass

    fallback = tx.run(
        """
        MATCH (n)
        WHERE n.sessionId = $session_id
          AND any(label IN labels(n) WHERE label IN $concept_labels)
          AND toLower(n.canonical) CONTAINS toLower($query_text)
        RETURN labels(n)[0] AS label,
               n.canonical AS canonical,
               1.0 AS score
        ORDER BY coalesce(n.lastSeenAt, n.createdAt, 0) DESC
        LIMIT $limit
        """,
        session_id=session_id,
        concept_labels=ConceptLabel.values(),
        query_text=query_text,
        limit=limit,
    )
    return [dict(record) for record in fallback]


def _get_top_concepts_tx(tx: Any, *, session_id: str, limit: int) -> list[dict[str, Any]]:
    result = tx.run(
        """
        MATCH (c)
        WHERE c.sessionId = $session_id
          AND any(label IN labels(c) WHERE label IN $concept_labels)
        OPTIONAL MATCH (:Utterance {sessionId: $session_id})-[m:MENTIONS]->(c)
        WITH labels(c)[0] AS label,
             c.canonical AS canonical,
             count(m) AS mention_count,
             coalesce(c.lastSeenAt, c.createdAt, 0) AS last_seen_at_ms
        RETURN label,
               canonical,
               mention_count,
               toFloat(mention_count) + (toFloat(last_seen_at_ms) / 1000000000000.0) AS score
        ORDER BY mention_count DESC, last_seen_at_ms DESC
        LIMIT $limit
        """,
        session_id=session_id,
        concept_labels=ConceptLabel.values(),
        limit=limit,
    )
    return [dict(record) for record in result]


def _normalize_mention(mention: dict[str, Any]) -> dict[str, Any]:
    label = str(mention["label"]).strip()
    canonical = _normalize_canonical(str(mention["canonical"]))
    validate_concept_label(label)
    return {
        "label": label,
        "canonical": canonical,
        "start_char": mention.get("start_char"),
        "end_char": mention.get("end_char"),
    }


def _normalize_canonical(canonical: str) -> str:
    normalized = canonical.strip()
    if not normalized:
        raise ValueError("Canonical value must not be blank")
    return normalized


def _node_payload_from_labels_and_props(labels: list[str], props: dict[str, Any]) -> dict[str, Any]:
    label = labels[0]
    if label == "Utterance":
        utterance_id = props["utteranceId"]
        canonical = props.get("text", "")
        return {
            "id": utterance_id,
            "label": label,
            "canonical": canonical,
            "properties": {
                "utterance_id": utterance_id,
                "session_id": props.get("sessionId"),
                "role": props.get("role"),
                "text": props.get("text"),
                "message_id": props.get("messageId"),
                "timestamp_ms": props.get("timestampMs"),
            },
        }

    canonical = props["canonical"]
    session_id = props["sessionId"]
    return {
        "id": _concept_node_id(session_id=session_id, label=label, canonical=canonical),
        "label": label,
        "canonical": canonical,
        "properties": {
            "session_id": session_id,
            "canonical": canonical,
            "created_at_ms": props.get("createdAt"),
            "last_seen_at_ms": props.get("lastSeenAt"),
            "latest_goal_canonical": props.get("latestGoalCanonical"),
        },
    }


def _edge_payload(
    *,
    rel_type: str,
    rel_props: dict[str, Any],
    source_node: dict[str, Any],
    target_node: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": _edge_id(source_node["id"], rel_type, target_node["id"]),
        "type": rel_type,
        "source": source_node["id"],
        "target": target_node["id"],
        "properties": {
            "created_at_ms": rel_props.get("createdAt"),
            "last_seen_at_ms": rel_props.get("lastSeenAt"),
            "start_char": rel_props.get("startChar"),
            "end_char": rel_props.get("endChar"),
        },
    }


def _concept_node_id(*, session_id: str, label: str, canonical: str) -> str:
    return f"{session_id}:{label}:{canonical}"


def _edge_id(source: str, rel_type: str, target: str) -> str:
    return f"{source}:{rel_type}:{target}"
