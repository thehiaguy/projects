import base64
from typing import Any

from utils.errors import AppError


def build_basic_auth_header(api_key: str, secret_key: str) -> str:
    credentials = f"{api_key}:{secret_key}"
    encoded = base64.b64encode(credentials.encode("utf-8")).decode("ascii")
    return f"Basic {encoded}"


async def fetch_access_token(
    *,
    api_key: str,
    secret_key: str,
    http_client: Any,
) -> dict[str, Any]:
    auth_header = build_basic_auth_header(api_key, secret_key)
    try:
        response = await http_client.post(
            "https://api.hume.ai/oauth2-cc/token",
            headers={
                "Authorization": auth_header,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials"},
        )
    except Exception as exc:
        raise AppError(
            code="hume_connection_error",
            message="Failed to reach Hume OAuth endpoint.",
            http_status=502,
            retryable=True,
        ) from exc

    if response.status_code != 200:
        raise AppError(
            code="hume_auth_failed",
            message=f"Hume OAuth returned status {response.status_code}.",
            http_status=502,
        )

    data = response.json()
    return {
        "access_token": data["access_token"],
        "expires_in": data.get("expires_in", 3600),
        "token_type": data.get("token_type", "Bearer"),
    }
