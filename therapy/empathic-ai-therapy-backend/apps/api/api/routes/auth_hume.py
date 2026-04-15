from fastapi import APIRouter, HTTPException

from app.deps import get_hume_http_client, get_settings
from services.hume.oauth import fetch_access_token

router = APIRouter(tags=["hume"])


@router.post("/v1/hume/access-token")
async def create_hume_access_token() -> dict[str, object]:
    """
    Purpose:
        Fetch a temporary Hume EVI access token via server-side OAuth client credentials flow.

    Inputs:
        No request body required for the base flow.
        Optional future body fields:
        - `config_id` override (if multiple Hume EVI configs are supported)

    Returns:
        JSON object with shape:
        - `access_token`: `str`
        - `expires_in`: `int` (seconds)
        Optional:
        - `token_type`, `issued_at_ms`

    Data structures / implementation notes:
        - Use `HUME_API_KEY` + `HUME_SECRET_KEY` (server-only)
        - Delegate HTTP call + auth header construction to `services.hume.oauth.fetch_access_token`
        - Never expose secret key to frontend
    """
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
