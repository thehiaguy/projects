from __future__ import annotations
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT_DIR = Path(__file__).resolve().parent
API_DIR = ROOT_DIR / "apps" / "api"

if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


@dataclass
class RouteCheck:
    name: str
    status: str
    details: dict[str, Any]


def main() -> int:
    _bootstrap_environment()

    print("Backend API route test harness")
    print()
    print("This script tests the FastAPI app in-process using the real app factory.")
    print("It covers REST routes and the websocket route with sample Hume-style events.")
    print()

    try:
        from fastapi.testclient import TestClient
        from app.main import create_app
    except Exception as exc:
        print("Failed to import FastAPI app or test client.")
        print(json.dumps({"error_type": type(exc).__name__, "message": str(exc)}, indent=2))
        return 1

    checks: list[RouteCheck]
    try:
        with TestClient(create_app()) as client:
            checks = run_all_checks(client)
    except Exception as exc:
        print("Failed to start or exercise the FastAPI application.")
        print(json.dumps({"error_type": type(exc).__name__, "message": str(exc)}, indent=2))
        return 1

    print("Route checks:")
    for check in checks:
        print(f"- {check.name}: {check.status}")
        print(json.dumps(check.details, indent=2, sort_keys=True))
        print()

    failures = [check for check in checks if check.status == "FAIL"]
    if failures:
        print("One or more API route checks failed.")
        return 1

    print("All API route checks completed without failures.")
    return 0


def run_all_checks(client: Any) -> list[RouteCheck]:
    checks: list[RouteCheck] = []

    checks.append(_check_health(client))

    session_check = _check_create_session(client)
    checks.append(session_check)
    session_id = session_check.details.get("session_id")
    if session_check.status != "PASS" or not isinstance(session_id, str):
        return checks

    checks.append(_check_hume_access_token(client))
    checks.append(_check_graph_snapshot(client, session_id=session_id, label="graph_pre"))
    checks.extend(
        _check_websocket_session(
            client,
            session_id=session_id,
            session_token=str(session_check.details.get("session_token") or ""),
        )
    )
    checks.append(_check_audio_window(client, session_id=session_id))
    checks.append(_check_graph_snapshot(client, session_id=session_id, label="graph_post"))
    checks.append(_check_end_session(client, session_id=session_id))

    return checks


def _check_health(client: Any) -> RouteCheck:
    try:
        response = client.get("/v1/health")
        payload = response.json()
        if response.status_code != 200 or payload != {"ok": True}:
            return RouteCheck(
                name="GET /v1/health",
                status="FAIL",
                details={
                    "status_code": response.status_code,
                    "payload": payload,
                },
            )
        return RouteCheck(
            name="GET /v1/health",
            status="PASS",
            details=payload,
        )
    except Exception as exc:
        return _exception_check("GET /v1/health", exc)


def _check_create_session(client: Any) -> RouteCheck:
    try:
        response = client.post("/v1/sessions")
        payload = response.json()
        session_id = payload.get("session_id")
        if response.status_code != 200 or not isinstance(session_id, str) or not session_id:
            return RouteCheck(
                name="POST /v1/sessions",
                status="FAIL",
                details={
                    "status_code": response.status_code,
                    "payload": payload,
                },
            )
        return RouteCheck(
            name="POST /v1/sessions",
            status="PASS",
            details=payload,
        )
    except Exception as exc:
        return _exception_check("POST /v1/sessions", exc)


def _check_hume_access_token(client: Any) -> RouteCheck:
    try:
        response = client.post("/v1/hume/access-token")
        payload = response.json()
        if response.status_code != 200:
            return RouteCheck(
                name="POST /v1/hume/access-token",
                status="FAIL",
                details={
                    "status_code": response.status_code,
                    "payload": payload,
                },
            )
        return RouteCheck(
            name="POST /v1/hume/access-token",
            status="PASS",
            details={
                "expires_in": payload.get("expires_in"),
                "token_type": payload.get("token_type"),
                "access_token_prefix": str(payload.get("access_token", ""))[:12],
            },
        )
    except Exception as exc:
        return _exception_check("POST /v1/hume/access-token", exc)


def _check_graph_snapshot(client: Any, *, session_id: str, label: str) -> RouteCheck:
    route_name = f"GET /v1/sessions/{session_id}/graph ({label})"
    try:
        response = client.get(f"/v1/sessions/{session_id}/graph")
        payload = response.json()
        if response.status_code != 200:
            return RouteCheck(
                name=route_name,
                status="FAIL",
                details={"status_code": response.status_code, "payload": payload},
            )

        nodes = payload.get("nodes", [])
        edges = payload.get("edges", [])
        return RouteCheck(
            name=route_name,
            status="PASS",
            details={
                "node_count": len(nodes) if isinstance(nodes, list) else None,
                "edge_count": len(edges) if isinstance(edges, list) else None,
            },
        )
    except Exception as exc:
        return _exception_check(route_name, exc)


def _check_end_session(client: Any, *, session_id: str) -> RouteCheck:
    route_name = f"POST /v1/sessions/{session_id}/end"
    try:
        response = client.post(f"/v1/sessions/{session_id}/end")
        payload = response.json()
        if response.status_code != 200:
            return RouteCheck(
                name=route_name,
                status="FAIL",
                details={"status_code": response.status_code, "payload": payload},
            )

        return RouteCheck(
            name=route_name,
            status="PASS",
            details={
                "summary": payload.get("summary"),
                "top_concepts_count": len(payload.get("top_concepts", [])),
            },
        )
    except Exception as exc:
        return _exception_check(route_name, exc)


def _check_websocket_session(client: Any, *, session_id: str, session_token: str) -> list[RouteCheck]:
    checks: list[RouteCheck] = []
    route_name = f"WS /ws/session/{session_id}"

    try:
        with client.websocket_connect(f"/ws/session/{session_id}?session_token={session_token}") as websocket:
            checks.append(_ws_ping_check(websocket, session_id=session_id, route_name=route_name))
            checks.append(_ws_assistant_check(websocket, session_id=session_id, route_name=route_name))
            checks.append(_ws_user_message_check(websocket, session_id=session_id, route_name=route_name))
    except Exception as exc:
        checks.append(_exception_check(route_name, exc))

    return checks


def _ws_ping_check(websocket: Any, *, session_id: str, route_name: str) -> RouteCheck:
    correlation_id = f"ping-{uuid4().hex[:8]}"
    websocket.send_json(
        {
            "type": "client.ping",
            "session_id": session_id,
            "payload": {},
            "correlation_id": correlation_id,
        }
    )
    response = websocket.receive_json()
    if response.get("type") != "server.pong":
        return RouteCheck(
            name=f"{route_name} client.ping",
            status="FAIL",
            details={"payload": response},
        )
    return RouteCheck(
        name=f"{route_name} client.ping",
        status="PASS",
        details={"payload": response},
    )


def _ws_assistant_check(websocket: Any, *, session_id: str, route_name: str) -> RouteCheck:
    message_id = f"assistant-{uuid4().hex[:8]}"
    websocket.send_json(
        {
            "type": "evi.assistant_message",
            "session_id": session_id,
            "payload": {
                "message_id": message_id,
                "role": "assistant",
                "content": "I hear that work stress is really affecting you.",
                "timestamp_ms": 1772326200000,
            },
        }
    )
    response = websocket.receive_json()
    if response.get("type") != "server.ack":
        return RouteCheck(
            name=f"{route_name} evi.assistant_message",
            status="FAIL",
            details={"payload": response},
        )
    return RouteCheck(
        name=f"{route_name} evi.assistant_message",
        status="PASS",
        details={"payload": response},
    )


def _ws_user_message_check(websocket: Any, *, session_id: str, route_name: str) -> RouteCheck:
    message_id = f"user-{uuid4().hex[:8]}"
    websocket.send_json(
        {
            "type": "evi.user_message.final",
            "session_id": session_id,
            "payload": {
                "message_id": message_id,
                "role": "user",
                "content": "Work stress makes me anxious and I want to sleep better.",
                "interim": False,
                "prosody_scores": {
                    "Anxiety": 0.91,
                    "Stress": 0.88,
                    "Tiredness": 0.52,
                },
                "timestamp_ms": 1772326201000,
            },
        }
    )

    first = websocket.receive_json()
    if first.get("type") == "server.error":
        return RouteCheck(
            name=f"{route_name} evi.user_message.final",
            status="FAIL",
            details={"payload": first},
        )

    second = websocket.receive_json()
    third = websocket.receive_json()
    fourth = websocket.receive_json()
    fifth = websocket.receive_json()
    packets = {
        first.get("type"): first,
        second.get("type"): second,
        third.get("type"): third,
        fourth.get("type"): fourth,
        fifth.get("type"): fifth,
    }
    required_types = {"kg.diff", "kg.tool_calls_applied", "summary.partial", "coach.insight"}
    if not required_types.issubset(packets):
        return RouteCheck(
            name=f"{route_name} evi.user_message.final",
            status="FAIL",
            details={"first": first, "second": second, "third": third, "fourth": fourth, "fifth": fifth},
        )

    kg_diff = packets["kg.diff"]["payload"]
    tool_calls = packets["kg.tool_calls_applied"]["payload"]
    safety_type = "safety.alert" if "safety.alert" in packets else "safety.status" if "safety.status" in packets else None
    return RouteCheck(
        name=f"{route_name} evi.user_message.final",
        status="PASS",
        details={
            "nodes_upsert": len(kg_diff.get("nodes_upsert", [])),
            "edges_upsert": len(kg_diff.get("edges_upsert", [])),
            "receipts": len(kg_diff.get("receipts", [])),
            "tool_calls": len(tool_calls.get("calls", [])),
            "dropped_calls": len(tool_calls.get("dropped_calls", [])),
            "safety_event_type": safety_type,
        },
    )


def _check_audio_window(client: Any, *, session_id: str) -> RouteCheck:
    route_name = f"POST /v1/sessions/{session_id}/audio-window"
    try:
        response = client.post(
            f"/v1/sessions/{session_id}/audio-window",
            files={"file": ("window.wav", b"fake-audio", "audio/wav")},
            data={
                "transcript_text": "Work stress keeps me up at night and I want better sleep.",
                "prosody_scores_json": json.dumps({"Stress": 0.87, "Fatigue": 0.63}),
            },
        )
        payload = response.json()
        if response.status_code != 200:
            return RouteCheck(
                name=route_name,
                status="FAIL",
                details={"status_code": response.status_code, "payload": payload},
            )

        return RouteCheck(
            name=route_name,
            status="PASS",
            details={
                "transcript": payload.get("transcript"),
                "warnings": payload.get("warnings", []),
                "kg_nodes": len(payload.get("kg_diff", {}).get("nodes_upsert", [])),
            },
        )
    except Exception as exc:
        return _exception_check(route_name, exc)


def _exception_check(name: str, exc: Exception) -> RouteCheck:
    return RouteCheck(
        name=name,
        status="FAIL",
        details={
            "error_type": type(exc).__name__,
            "message": str(exc),
        },
    )


def _bootstrap_environment() -> None:
    candidate_files = [
        ROOT_DIR / ".env",
        API_DIR / ".env",
        API_DIR / ".env.example",
    ]
    for file_path in candidate_files:
        if file_path.exists():
            for key, value in _parse_env_file(file_path).items():
                os.environ.setdefault(key, value)

    defaults = {
        "CORS_ALLOW_ORIGINS": "http://localhost:3000",
        "LOG_LEVEL": "INFO",
        "GEMINI_MODEL_KG": "gemini-2.5-flash-lite",
    }
    for key, value in defaults.items():
        os.environ.setdefault(key, value)


def _parse_env_file(path: Path) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip()] = value.strip().strip("'\"")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
