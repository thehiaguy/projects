"""Tests for the Hume OAuth token endpoint."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from utils.errors import AppError


@pytest.fixture(scope="module")
def client():
    with patch("services.neo4j.driver.create_driver", return_value=MagicMock()), \
         patch("services.neo4j.migrate.run_migrations", return_value={"applied": True}):
        from app.main import create_app
        app = create_app()
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


class TestCreateHumeAccessToken:
    def test_success_returns_200(self, client):
        mock_token = {
            "access_token": "tok_test",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        with patch("api.routes.auth_hume.fetch_access_token", new_callable=AsyncMock, return_value=mock_token):
            response = client.post("/v1/hume/access-token")
        assert response.status_code == 200

    def test_response_has_access_token(self, client):
        mock_token = {"access_token": "tok_xyz", "expires_in": 1800, "token_type": "Bearer"}
        with patch("api.routes.auth_hume.fetch_access_token", new_callable=AsyncMock, return_value=mock_token):
            response = client.post("/v1/hume/access-token")
        data = response.json()
        assert "access_token" in data
        assert data["access_token"] == "tok_xyz"

    def test_response_has_expires_in(self, client):
        mock_token = {"access_token": "t", "expires_in": 900, "token_type": "Bearer"}
        with patch("api.routes.auth_hume.fetch_access_token", new_callable=AsyncMock, return_value=mock_token):
            response = client.post("/v1/hume/access-token")
        data = response.json()
        assert "expires_in" in data
        assert data["expires_in"] == 900

    def test_hume_error_returns_502(self, client):
        err = AppError(code="hume_auth_failed", message="Hume failed", http_status=502)
        with patch("api.routes.auth_hume.fetch_access_token", new_callable=AsyncMock, side_effect=err):
            response = client.post("/v1/hume/access-token")
        assert response.status_code == 502

    def test_token_type_included(self, client):
        mock_token = {"access_token": "t", "expires_in": 3600, "token_type": "Bearer"}
        with patch("api.routes.auth_hume.fetch_access_token", new_callable=AsyncMock, return_value=mock_token):
            response = client.post("/v1/hume/access-token")
        data = response.json()
        assert "token_type" in data
