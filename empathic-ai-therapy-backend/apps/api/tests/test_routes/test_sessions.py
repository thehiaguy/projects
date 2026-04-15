"""Tests for session REST endpoints."""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    with patch("services.neo4j.driver.create_driver", return_value=MagicMock()), \
         patch("services.neo4j.migrate.run_migrations", return_value={"applied": True}):
        from app.main import create_app
        app = create_app()
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


class TestCreateSession:
    def test_returns_201_or_200(self, client):
        mock_record = {
            "session_id": "sess_abc",
            "created_at_ms": 1000000,
            "status": "active",
        }
        with patch("api.routes.sessions.repo_sessions.create_session_record", return_value=mock_record):
            response = client.post("/v1/sessions")
        assert response.status_code == 200

    def test_response_has_session_id(self, client):
        mock_record = {
            "session_id": "sess_abc",
            "created_at_ms": 1000000,
            "status": "active",
        }
        with patch("api.routes.sessions.repo_sessions.create_session_record", return_value=mock_record):
            response = client.post("/v1/sessions")
        data = response.json()
        assert "session_id" in data
        assert data["session_id"] == "sess_abc"

    def test_response_has_created_at_ms(self, client):
        mock_record = {
            "session_id": "sess_xyz",
            "created_at_ms": 9999999,
            "status": "active",
        }
        with patch("api.routes.sessions.repo_sessions.create_session_record", return_value=mock_record):
            response = client.post("/v1/sessions")
        data = response.json()
        assert "created_at_ms" in data

    def test_session_id_is_string(self, client):
        mock_record = {"session_id": "sess_abc", "created_at_ms": 1, "status": "active"}
        with patch("api.routes.sessions.repo_sessions.create_session_record", return_value=mock_record):
            response = client.post("/v1/sessions")
        assert isinstance(response.json()["session_id"], str)


class TestEndSession:
    def test_returns_200_for_existing_session(self, client):
        mock_record = {
            "session_id": "sess_1",
            "created_at_ms": 1000,
            "ended_at_ms": 2000,
            "status": "ended",
        }
        with patch("api.routes.sessions.repo_sessions.end_session_record", return_value=mock_record), \
             patch("api.routes.sessions.repo_graph.get_top_concepts", return_value=[]):
            response = client.post("/v1/sessions/sess_1/end")
        assert response.status_code == 200

    def test_response_has_summary(self, client):
        mock_record = {"session_id": "sess_1", "created_at_ms": 1, "ended_at_ms": 2, "status": "ended"}
        with patch("api.routes.sessions.repo_sessions.end_session_record", return_value=mock_record), \
             patch("api.routes.sessions.repo_graph.get_top_concepts", return_value=[]):
            response = client.post("/v1/sessions/sess_1/end")
        data = response.json()
        assert "summary" in data
        assert isinstance(data["summary"], str)

    def test_response_has_top_concepts(self, client):
        mock_record = {"session_id": "s", "created_at_ms": 1, "ended_at_ms": 2, "status": "ended"}
        mock_concepts = [
            {"label": "Emotion", "canonical": "anxiety", "mention_count": 5, "score": 5.0}
        ]
        with patch("api.routes.sessions.repo_sessions.end_session_record", return_value=mock_record), \
             patch("api.routes.sessions.repo_graph.get_top_concepts", return_value=mock_concepts):
            response = client.post("/v1/sessions/sess_1/end")
        data = response.json()
        assert "top_concepts" in data
        assert len(data["top_concepts"]) == 1
        assert data["top_concepts"][0]["canonical"] == "anxiety"

    def test_returns_404_for_missing_session(self, client):
        with patch("api.routes.sessions.repo_sessions.end_session_record", return_value=None):
            response = client.post("/v1/sessions/nonexistent/end")
        assert response.status_code == 404

    def test_summary_includes_top_concepts(self, client):
        mock_record = {"session_id": "s", "created_at_ms": 1, "ended_at_ms": 2, "status": "ended"}
        mock_concepts = [
            {"label": "Emotion", "canonical": "anxiety", "mention_count": 3, "score": 3.0},
        ]
        with patch("api.routes.sessions.repo_sessions.end_session_record", return_value=mock_record), \
             patch("api.routes.sessions.repo_graph.get_top_concepts", return_value=mock_concepts):
            response = client.post("/v1/sessions/s/end")
        data = response.json()
        assert "anxiety" in data["summary"]
