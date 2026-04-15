"""Tests for Hume OAuth service."""
import base64
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.hume.oauth import build_basic_auth_header, fetch_access_token
from utils.errors import AppError


class TestBuildBasicAuthHeader:
    def test_format(self):
        header = build_basic_auth_header("my_key", "my_secret")
        assert header.startswith("Basic ")

    def test_decodes_correctly(self):
        header = build_basic_auth_header("api_key", "secret_key")
        encoded = header[len("Basic "):]
        decoded = base64.b64decode(encoded).decode("utf-8")
        assert decoded == "api_key:secret_key"

    def test_special_characters(self):
        header = build_basic_auth_header("key:with:colons", "secret")
        encoded = header[len("Basic "):]
        decoded = base64.b64decode(encoded).decode("utf-8")
        assert decoded == "key:with:colons:secret"

    def test_empty_strings(self):
        header = build_basic_auth_header("", "")
        assert header.startswith("Basic ")
        encoded = header[len("Basic "):]
        decoded = base64.b64decode(encoded).decode("utf-8")
        assert decoded == ":"


class TestFetchAccessToken:
    @pytest.mark.asyncio
    async def test_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "tok_abc",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        result = await fetch_access_token(
            api_key="key", secret_key="secret", http_client=mock_client
        )

        assert result["access_token"] == "tok_abc"
        assert result["expires_in"] == 3600
        assert result["token_type"] == "Bearer"

    @pytest.mark.asyncio
    async def test_sends_basic_auth_header(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "t", "expires_in": 300}
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        await fetch_access_token(
            api_key="mykey", secret_key="mysecret", http_client=mock_client
        )

        call_kwargs = mock_client.post.call_args.kwargs
        auth_header = call_kwargs["headers"]["Authorization"]
        assert auth_header.startswith("Basic ")

    @pytest.mark.asyncio
    async def test_non_200_raises_app_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {}
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with pytest.raises(AppError) as exc_info:
            await fetch_access_token(
                api_key="k", secret_key="s", http_client=mock_client
            )
        assert exc_info.value.code == "hume_auth_failed"
        assert exc_info.value.http_status == 502

    @pytest.mark.asyncio
    async def test_connection_error_raises_app_error(self):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("connection refused"))

        with pytest.raises(AppError) as exc_info:
            await fetch_access_token(
                api_key="k", secret_key="s", http_client=mock_client
            )
        assert exc_info.value.code == "hume_connection_error"
        assert exc_info.value.retryable is True

    @pytest.mark.asyncio
    async def test_default_token_type(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "tok", "expires_in": 1800}
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        result = await fetch_access_token(
            api_key="k", secret_key="s", http_client=mock_client
        )
        assert result["token_type"] == "Bearer"
