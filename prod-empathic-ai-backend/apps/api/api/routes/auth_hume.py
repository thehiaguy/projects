from fastapi import APIRouter, HTTPException

from apps.api.core.config import get_hume_http_client, get_settings
from services.hume.oauth import fetch_access_token

router = APIRouter(tags=["hume"])


@router.post("/v1/hume/access-token")
async def create_hume_access_token() -> dict[str, object]:
    settings = get_settings()
    http_client = get_hume_http_client()

    try:
        token_payload = await fetch_access_token(
            api_key=settings.hume_api_key,
            secret_key=settings.hume_secret_key,
            http_client=http_client,
        )
    except Exception as exc:
        http_status = getattr(exc, "http_status", 502)
        detail = {
            "code": getattr(exc, "code", "hume_access_token_failed"),
            "message": getattr(exc, "message", "Failed to fetch a Hume access token."),
            "correlation_id": getattr(exc, "correlation_id", None),
        }
        raise HTTPException(status_code=http_status, detail=detail) from exc

    return token_payload
