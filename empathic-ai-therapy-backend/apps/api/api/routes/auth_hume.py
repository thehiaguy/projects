from typing import Any

from fastapi import APIRouter

from app.deps import get_hume_http_client, get_settings
from services.hume.oauth import fetch_access_token
from utils.errors import AppError, to_http_exception

router = APIRouter(tags=["hume"])


@router.post("/v1/hume/access-token")
async def create_hume_access_token() -> dict[str, Any]:
    settings = get_settings()
    async with get_hume_http_client() as http_client:
        try:
            token_data = await fetch_access_token(
                api_key=settings.hume_api_key,
                secret_key=settings.hume_secret_key,
                http_client=http_client,
            )
        except AppError as exc:
            raise to_http_exception(exc) from exc

    return {
        "access_token": token_data["access_token"],
        "expires_in": token_data["expires_in"],
        "token_type": token_data.get("token_type", "Bearer"),
    }
