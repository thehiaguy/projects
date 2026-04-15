"""Tests for the graph snapshot endpoint."""
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


class TestGetSessionGraph:
    def test_returns_200(self, client):
        mock_snapshot = {"nodes": [], "edges": []}
        with patch("api.routes.graph.repo_graph.get_graph_snapshot", return_value=mock_snapshot):
            response = client.get("/v1/sessions/sess_1/graph")
        assert response.status_code == 200

    def test_response_has_nodes_and_edges(self, client):
        mock_snapshot = {"nodes": [], "edges": []}
        with patch("api.routes.graph.repo_graph.get_graph_snapshot", return_value=mock_snapshot):
            response = client.get("/v1/sessions/sess_1/graph")
        data = response.json()
        assert "nodes" in data
        assert "edges" in data

    def test_nodes_and_edges_are_lists(self, client):
        with patch("api.routes.graph.repo_graph.get_graph_snapshot", return_value={"nodes": [], "edges": []}):
            response = client.get("/v1/sessions/sess_1/graph")
        data = response.json()
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)

    def test_nodes_included_in_response(self, client):
        mock_snapshot = {
            "nodes": [
                {"id": "Emotion:sess:anxiety", "label": "Emotion", "canonical": "anxiety", "properties": {}}
            ],
            "edges": [],
        }
        with patch("api.routes.graph.repo_graph.get_graph_snapshot", return_value=mock_snapshot):
            response = client.get("/v1/sessions/sess_1/graph")
        data = response.json()
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["label"] == "Emotion"

    def test_edges_included_in_response(self, client):
        mock_snapshot = {
            "nodes": [],
            "edges": [
                {
                    "id": "e1", "type": "EVOKES",
                    "source": "Trigger:sess:work", "target": "Emotion:sess:stress",
                    "properties": {},
                }
            ],
        }
        with patch("api.routes.graph.repo_graph.get_graph_snapshot", return_value=mock_snapshot):
            response = client.get("/v1/sessions/sess_1/graph")
        data = response.json()
        assert len(data["edges"]) == 1
        assert data["edges"][0]["type"] == "EVOKES"

    def test_different_session_ids(self, client):
        for sid in ["sess_aaa", "sess_bbb", "sess_ccc"]:
            with patch("api.routes.graph.repo_graph.get_graph_snapshot", return_value={"nodes": [], "edges": []}):
                response = client.get(f"/v1/sessions/{sid}/graph")
            assert response.status_code == 200
