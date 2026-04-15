"""Tests for WebSocket session endpoint."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def ws_client():
    """Create a TestClient with patches active through the full lifespan."""
    with patch("services.neo4j.driver.create_driver", return_value=MagicMock()), \
         patch("services.neo4j.migrate.run_migrations", return_value={"applied": True}):
        from app.main import create_app
        app = create_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client


class TestSessionWsEndpoint:
    def test_ws_connects_and_accepts(self, ws_client):
        with ws_client.websocket_connect("/ws/session/sess_1") as ws:
            ws.send_json({
                "type": "client.ping",
                "session_id": "sess_1",
                "payload": {},
            })
            data = ws.receive_json()
            assert data["type"] == "server.pong"

    def test_pong_has_server_timestamp(self, ws_client):
        with ws_client.websocket_connect("/ws/session/sess_1") as ws:
            ws.send_json({
                "type": "client.ping",
                "session_id": "sess_1",
                "payload": {},
            })
            data = ws.receive_json()
            assert "server_ts_ms" in data["payload"]
            assert isinstance(data["payload"]["server_ts_ms"], int)

    def test_unknown_message_type_returns_error(self, ws_client):
        with ws_client.websocket_connect("/ws/session/sess_1") as ws:
            ws.send_json({
                "type": "unknown.type",
                "session_id": "sess_1",
                "payload": {},
            })
            data = ws.receive_json()
            assert data["type"] == "server.error"
            assert data["payload"]["code"] == "unknown_message_type"

    def test_missing_type_returns_error(self, ws_client):
        with ws_client.websocket_connect("/ws/session/sess_1") as ws:
            ws.send_json({"session_id": "sess_1", "payload": {}})
            data = ws.receive_json()
            assert data["type"] == "server.error"

    def test_missing_session_id_returns_error(self, ws_client):
        with ws_client.websocket_connect("/ws/session/sess_1") as ws:
            ws.send_json({"type": "client.ping", "payload": {}})
            data = ws.receive_json()
            assert data["type"] == "server.error"

    def test_evi_user_message_final_triggers_kg_update(self, ws_client):
        mock_result = {
            "kg_diff": {
                "nodes_upsert": [{"id": "n1", "label": "Emotion", "canonical": "anxiety", "properties": {}}],
                "edges_upsert": [],
                "receipts": [],
            },
            "tool_calls_applied": {"calls": [], "dropped_calls": []},
            "warnings": [],
        }
        with patch("ws.session_ws.process_utterance_event", new_callable=AsyncMock, return_value=mock_result):
            with ws_client.websocket_connect("/ws/session/sess_1") as ws:
                ws.send_json({
                    "type": "evi.user_message.final",
                    "session_id": "sess_1",
                    "payload": {
                        "message_id": "msg_1",
                        "content": "I feel anxious",
                        "role": "user",
                        "interim": False,
                    },
                })
                kg_diff_msg = ws.receive_json()
                assert kg_diff_msg["type"] == "kg.diff"
                assert len(kg_diff_msg["payload"]["nodes_upsert"]) == 1

                tool_calls_msg = ws.receive_json()
                assert tool_calls_msg["type"] == "kg.tool_calls_applied"

    def test_interim_evi_message_drops_silently(self, ws_client):
        """Interim messages should be silently dropped — pong is the next response."""
        with ws_client.websocket_connect("/ws/session/sess_1") as ws:
            ws.send_json({
                "type": "evi.user_message.final",
                "session_id": "sess_1",
                "payload": {
                    "message_id": "msg_1",
                    "content": "partial...",
                    "role": "user",
                    "interim": True,
                },
            })
            ws.send_json({"type": "client.ping", "session_id": "sess_1", "payload": {}})
            data = ws.receive_json()
            assert data["type"] == "server.pong"

    def test_session_id_in_responses(self, ws_client):
        with ws_client.websocket_connect("/ws/session/my_session") as ws:
            ws.send_json({
                "type": "client.ping",
                "session_id": "my_session",
                "payload": {},
            })
            data = ws.receive_json()
            assert data["session_id"] == "my_session"

    def test_error_on_kg_failure_does_not_close_connection(self, ws_client):
        with patch(
            "ws.session_ws.process_utterance_event",
            new_callable=AsyncMock,
            side_effect=Exception("KG failure"),
        ):
            with ws_client.websocket_connect("/ws/session/sess_1") as ws:
                ws.send_json({
                    "type": "evi.user_message.final",
                    "session_id": "sess_1",
                    "payload": {
                        "message_id": "msg_1",
                        "content": "text",
                        "role": "user",
                        "interim": False,
                    },
                })
                data = ws.receive_json()
                assert data["type"] == "server.error"
                # Connection should still be alive
                ws.send_json({"type": "client.ping", "session_id": "sess_1", "payload": {}})
                pong = ws.receive_json()
                assert pong["type"] == "server.pong"

    def test_envelope_has_correlation_id(self, ws_client):
        with ws_client.websocket_connect("/ws/session/sess_1") as ws:
            ws.send_json({"type": "client.ping", "session_id": "sess_1", "payload": {}})
            data = ws.receive_json()
            assert "correlation_id" in data
            assert data["correlation_id"] is not None

    def test_envelope_has_sent_at_ms(self, ws_client):
        with ws_client.websocket_connect("/ws/session/sess_1") as ws:
            ws.send_json({"type": "client.ping", "session_id": "sess_1", "payload": {}})
            data = ws.receive_json()
            assert "sent_at_ms" in data
            assert isinstance(data["sent_at_ms"], int)
