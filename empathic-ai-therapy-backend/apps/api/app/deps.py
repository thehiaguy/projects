import os
from functools import lru_cache
from typing import Any

import httpx


class Settings:
    def __init__(self) -> None:
        self.hume_api_key: str = os.environ.get("HUME_API_KEY", "")
        self.hume_secret_key: str = os.environ.get("HUME_SECRET_KEY", "")
        self.hume_config_id: str = os.environ.get("HUME_CONFIG_ID", "")
        self.gcp_project: str = os.environ.get("GCP_PROJECT", "")
        self.gcp_location: str = os.environ.get("GCP_LOCATION", "us-central1")
        self.gemini_model_kg: str = os.environ.get("GEMINI_MODEL_KG", "gemini-2.0-flash-001")
        self.neo4j_uri: str = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_username: str = os.environ.get("NEO4J_USERNAME", "neo4j")
        self.neo4j_password: str = os.environ.get("NEO4J_PASSWORD", "")
        self.neo4j_database: str = os.environ.get("NEO4J_DATABASE", "neo4j")
        _raw_origins = os.environ.get("CORS_ALLOW_ORIGINS", "http://localhost:3000")
        self.cors_allow_origins: list[str] = [o.strip() for o in _raw_origins.split(",")]
        self.ws_max_size_bytes: int = int(os.environ.get("WS_MAX_SIZE_BYTES", str(16 * 1024 * 1024)))
        self.log_level: str = os.environ.get("LOG_LEVEL", "INFO")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def get_neo4j_driver() -> Any:
    from services.neo4j.driver import get_driver
    return get_driver()


def get_gemini_client() -> Any:
    from services.gemini.client import get_client
    settings = get_settings()
    return get_client(project=settings.gcp_project, location=settings.gcp_location)


def get_hume_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=10.0)
