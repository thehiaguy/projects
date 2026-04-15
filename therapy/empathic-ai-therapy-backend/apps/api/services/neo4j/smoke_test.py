from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from time import time
from typing import Any
from uuid import uuid4

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


@dataclass
class SmokeTestResult:
    connectivity_ok: bool
    migrations: dict[str, Any]
    created_session: dict[str, Any]
    fetched_session: dict[str, Any] | None
    utterance: dict[str, Any]
    prosody_frame: dict[str, Any]
    concept_nodes: list[dict[str, Any]]
    concept_edges: list[dict[str, Any]]
    mention_edges: list[dict[str, Any]]
    goal_node: dict[str, Any]
    recent_utterances: list[dict[str, Any]]
    graph_context: dict[str, Any]
    graph_snapshot: dict[str, list[dict[str, Any]]]
    top_concepts: list[dict[str, Any]]
    ended_session: dict[str, Any] | None


def run_smoke_test(*, cleanup: bool = True) -> SmokeTestResult:
    _bootstrap_environment()

    from app.deps import get_settings, reset_dependency_caches
    from services.neo4j.driver import close_driver, create_driver, get_driver
    from services.neo4j.migrate import run_migrations
    from services.neo4j.repo_graph import (
        get_graph_context_for_llm,
        get_graph_snapshot,
        get_top_concepts,
        link_utterance_mentions,
        set_session_goal,
        upsert_concept_node,
        upsert_relation_edge,
    )
    from services.neo4j.repo_sessions import create_session_record, end_session_record, get_session_record
    from services.neo4j.repo_utterances import insert_prosody_frame, list_recent_utterances, upsert_utterance

    reset_dependency_caches()
    settings = get_settings()
    session_id = f"smoke-session-{uuid4().hex[:12]}"
    utterance_id = f"utterance-{uuid4().hex[:12]}"
    frame_id = f"prosody-{uuid4().hex[:12]}"
    message_id = f"hume-message-{uuid4().hex[:12]}"
    now_ms = _now_ms()

    concept_nodes: list[dict[str, Any]] = []
    concept_edges: list[dict[str, Any]] = []
    mention_edges: list[dict[str, Any]] = []
    goal_node: dict[str, Any] = {}
    connectivity_ok = False

    try:
        create_driver(
            uri=settings.neo4j_uri,
            username=settings.neo4j_username,
            password=settings.neo4j_password,
        )
        _verify_connection()
        connectivity_ok = True

        migrations = run_migrations()
        created_session = create_session_record(session_id=session_id, created_at_ms=now_ms)
        fetched_session = get_session_record(session_id=session_id)

        utterance = upsert_utterance(
            utterance_id=utterance_id,
            session_id=session_id,
            role="user",
            text="Work stress makes me anxious, and I want to sleep better.",
            message_id=message_id,
            timestamp_ms=now_ms,
        )
        prosody_frame = insert_prosody_frame(
            frame_id=frame_id,
            session_id=session_id,
            message_id=message_id,
            top_json={"Anxiety": 0.91, "Stress": 0.88, "Tiredness": 0.52},
            created_at_ms=now_ms,
        )

        concept_nodes.append(
            upsert_concept_node(
                session_id=session_id,
                label="Trigger",
                canonical="work stress",
                now_ms=now_ms,
            )
        )
        concept_nodes.append(
            upsert_concept_node(
                session_id=session_id,
                label="Emotion",
                canonical="anxious",
                now_ms=now_ms,
            )
        )
        concept_nodes.append(
            upsert_concept_node(
                session_id=session_id,
                label="Need",
                canonical="better sleep",
                now_ms=now_ms,
            )
        )

        concept_edges.append(
            upsert_relation_edge(
                session_id=session_id,
                from_label="Trigger",
                from_canonical="work stress",
                rel_type="EVOKES",
                to_label="Emotion",
                to_canonical="anxious",
                now_ms=now_ms,
            )
        )

        mention_edges = link_utterance_mentions(
            session_id=session_id,
            utterance_id=utterance_id,
            mentions=[
                {"label": "Trigger", "canonical": "work stress", "start_char": 0, "end_char": 11},
                {"label": "Emotion", "canonical": "anxious", "start_char": 21, "end_char": 28},
            ],
            now_ms=now_ms,
        )

        goal_node = set_session_goal(
            session_id=session_id,
            canonical="sleep better",
            now_ms=now_ms,
        )
        concept_nodes.append(goal_node)
        concept_edges.append(
            upsert_relation_edge(
                session_id=session_id,
                from_label="Need",
                from_canonical="better sleep",
                rel_type="SUPPORTS",
                to_label="Goal",
                to_canonical="sleep better",
                now_ms=now_ms,
            )
        )

        recent_utterances = list_recent_utterances(session_id=session_id, limit=10)
        graph_context = get_graph_context_for_llm(
            session_id=session_id,
            query_text="sleep stress",
        )
        graph_snapshot = get_graph_snapshot(session_id=session_id, node_limit=50, edge_limit=50)
        top_concepts = get_top_concepts(session_id=session_id, limit=10)
        ended_session = end_session_record(session_id=session_id, ended_at_ms=_now_ms())

        return SmokeTestResult(
            connectivity_ok=connectivity_ok,
            migrations=migrations,
            created_session=created_session,
            fetched_session=fetched_session,
            utterance=utterance,
            prosody_frame=prosody_frame,
            concept_nodes=concept_nodes,
            concept_edges=concept_edges,
            mention_edges=mention_edges,
            goal_node=goal_node,
            recent_utterances=recent_utterances,
            graph_context=graph_context,
            graph_snapshot=graph_snapshot,
            top_concepts=top_concepts,
            ended_session=ended_session,
        )
    finally:
        if cleanup:
            _cleanup_session_data(session_id)
        close_driver()


def main() -> int:
    try:
        result = run_smoke_test(cleanup=True)
    except Exception as exc:
        print("Neo4j smoke test failed.", file=sys.stderr)
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    print()
    print("Neo4j smoke test completed successfully.")
    return 0


def _bootstrap_environment() -> None:
    root_dir = Path(__file__).resolve().parents[4]
    candidate_files = [
        root_dir / ".env",
        root_dir / "apps" / "api" / ".env",
    ]

    for file_path in candidate_files:
        if file_path.exists():
            for key, value in _parse_env_file(file_path).items():
                os.environ.setdefault(key, value)

    defaults = {
        "HUME_API_KEY": "smoke-test",
        "HUME_SECRET_KEY": "smoke-test",
        "GEMINI_API_KEY": "smoke-test",
        "CORS_ALLOW_ORIGINS": "http://localhost:3000",
        "LOG_LEVEL": "INFO",
    }
    for key, value in defaults.items():
        os.environ.setdefault(key, value)


def _parse_env_file(file_path: Path) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip()] = value.strip().strip('"').strip("'")
    return parsed


def _verify_connection() -> None:
    from app.deps import get_settings
    from services.neo4j.driver import get_driver

    settings = get_settings()
    driver = get_driver()
    with driver.session(database=settings.neo4j_database) as session:
        record = session.run("RETURN 1 AS ok").single()
        if record is None or record["ok"] != 1:
            raise RuntimeError("Neo4j connectivity check returned an unexpected result.")


def _cleanup_session_data(session_id: str) -> None:
    try:
        from app.deps import get_settings
        from services.neo4j.driver import get_driver
    except Exception:
        return

    try:
        settings = get_settings()
        driver = get_driver()
    except Exception:
        return

    with driver.session(database=settings.neo4j_database) as session:
        session.run(
            """
            MATCH (n)
            WHERE n.sessionId = $session_id
            DETACH DELETE n
            """,
            session_id=session_id,
        ).consume()


def _now_ms() -> int:
    return int(time() * 1000)


if __name__ == "__main__":
    raise SystemExit(main())
