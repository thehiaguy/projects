"""Tests for the health endpoint."""
import sys
import os

import pytest
from fastapi.testclient import TestClient

# Patch Neo4j driver before importing app
from unittest.mock import MagicMock, patch


@pytest.fixture(scope="module")
def client():
    with patch("services.neo4j.driver.create_driver", return_value=MagicMock()), \
         patch("services.neo4j.migrate.run_migrations", return_value={"applied": True}):
        from app.main import create_app
        app = create_app()
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


class TestHealthEndpoint:
    def test_get_health_returns_200(self, client):
        response = client.get("/v1/health")
        assert response.status_code == 200

    def test_get_health_returns_ok_true(self, client):
        response = client.get("/v1/health")
        data = response.json()
        assert data == {"ok": True}

    def test_content_type_json(self, client):
        response = client.get("/v1/health")
        assert "application/json" in response.headers["content-type"]
