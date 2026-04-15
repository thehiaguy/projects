from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_API_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
_ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"
_UNINITIALIZED = object()
_gemini_client: Any = _UNINITIALIZED
_hume_http_client: httpx.AsyncClient | object = _UNINITIALIZED


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_API_ENV_FILE, _ROOT_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
        enable_decoding=False,
    )

    hume_api_key: str
    hume_secret_key: str
    hume_config_id: str | None = None

    gemini_api_key: str
    gemini_model_kg: str = "gemini-2.5-flash-lite"

    neo4j_uri: str
    neo4j_username: str
    neo4j_password: str
    neo4j_database: str = "neo4j"

    session_signing_secret: str = "dev-session-secret-change-me"
    session_token_ttl_seconds: int = 21_600

    cors_allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    ws_max_size_bytes: int = 16_000_000
    log_level: str = "INFO"

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def parse_cors_allow_origins(cls, value: str | list[str] | None) -> list[str]:
        if value is None:
            return ["http://localhost:3000"]
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        if isinstance(value, list):
            return [str(origin).strip() for origin in value if str(origin).strip()]
        raise TypeError("cors_allow_origins must be a comma-separated string or list of strings")

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        return value.strip().upper()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def get_neo4j_driver() -> Any:
    from services.neo4j.driver import get_driver

    return get_driver()


def get_gemini_client() -> Any:
    global _gemini_client

    if _gemini_client is _UNINITIALIZED:
        settings = get_settings()
        from services.gemini.client import get_client

        _gemini_client = get_client(api_key=settings.gemini_api_key)

    return _gemini_client


def get_hume_http_client() -> Any:
    global _hume_http_client

    if _hume_http_client is _UNINITIALIZED:
        _hume_http_client = _build_hume_http_client()

    return _hume_http_client


def _build_hume_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, connect=5.0),
        headers={
            "Accept": "application/json",
            "User-Agent": "empathic-ai-therapy-backend/0.1.0",
        },
    )


async def close_hume_http_client() -> None:
    global _hume_http_client

    if isinstance(_hume_http_client, httpx.AsyncClient):
        await _hume_http_client.aclose()
    _hume_http_client = _UNINITIALIZED


def reset_dependency_caches() -> None:
    global _gemini_client

    get_settings.cache_clear()
    _gemini_client = _UNINITIALIZED
