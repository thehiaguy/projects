import base64
from typing import Any
import httpx
from utils.errors import AppError

HUME_OAUTH_TOKEN_URL = "https://api.hume.ai/oauth2-cc/token"


async def fetch_access_token(*, api_key: str, secret_key: str, http_client: Any,) -> dict[str, Any]:
    if not api_key.strip():
        raise _build_app_error( code="hume_api_key_missing", message="Hume API key is not configured.", http_status=500, retryable=False )
    if not secret_key.strip():
        raise _build_app_error( code="hume_secret_key_missing", message="Hume secret key is not configured.", http_status=500, retryable=False )

    try:
        response = await http_client.post(
            HUME_OAUTH_TOKEN_URL,
            data={"grant_type": "client_credentials"},
            headers={
                "Authorization": build_basic_auth_header(api_key, secret_key),
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
    except httpx.TimeoutException as exc:
        raise _build_app_error(
            code="hume_oauth_timeout",
            message="Timed out while requesting a Hume access token.",
            http_status=504,
            retryable=True,
            details={"provider": "hume", "url": HUME_OAUTH_TOKEN_URL},
        ) from exc
    except httpx.RequestError as exc:
        raise _build_app_error(
            code="hume_oauth_unreachable",
            message="Failed to reach Hume while requesting an access token.",
            http_status=502,
            retryable=True,
            details={"provider": "hume", "url": HUME_OAUTH_TOKEN_URL},
        ) from exc

    if response.status_code >= 400:
        response_text = response.text.strip()
        raise _build_app_error(
            code="hume_oauth_failed",
            message="Hume rejected the access token request.",
            http_status=502 if response.status_code >= 500 else 401,
            retryable=response.status_code >= 500,
            details={
                "provider": "hume",
                "provider_status": response.status_code,
                "response_body": response_text[:500] if response_text else None,
            },
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise _build_app_error(
            code="hume_oauth_invalid_response",
            message="Hume returned an invalid access token response.",
            http_status=502,
            retryable=True,
            details={"provider": "hume", "provider_status": response.status_code},
        ) from exc

    access_token = payload.get("access_token")
    expires_in = payload.get("expires_in")
    token_type = payload.get("token_type")

    if not isinstance(access_token, str) or not access_token:
        raise _build_app_error(
            code="hume_oauth_missing_access_token",
            message="Hume did not return a usable access token.",
            http_status=502,
            retryable=True,
            details={"provider": "hume", "provider_status": response.status_code},
        )

    normalized: dict[str, Any] = {
        "access_token": access_token,
        "expires_in": _normalize_expires_in(expires_in, provider_status=response.status_code),
    }
    if isinstance(token_type, str) and token_type:
        normalized["token_type"] = token_type

    return normalized


def build_basic_auth_header(api_key: str, secret_key: str) -> str:
    credentials = f"{api_key}:{secret_key}".encode("utf-8")
    encoded_credentials = base64.b64encode(credentials).decode("ascii")
    return f"Basic {encoded_credentials}"


def _build_app_error(
    *,
    code: str,
    message: str,
    http_status: int,
    retryable: bool,
    details: dict[str, Any] | None = None,
) -> AppError:
    error = AppError(message)
    error.code = code
    error.message = message
    error.http_status = http_status
    error.retryable = retryable
    error.correlation_id = None
    error.details = details
    return error


def _normalize_expires_in(expires_in: Any, *, provider_status: int) -> int:
    if isinstance(expires_in, bool):
        raise _build_app_error(
            code="hume_oauth_invalid_expires_in",
            message="Hume returned an invalid token expiry value.",
            http_status=502,
            retryable=True,
            details={"provider": "hume", "provider_status": provider_status},
        )

    if isinstance(expires_in, (int, float)):
        return int(expires_in)

    if isinstance(expires_in, str) and expires_in.strip():
        try:
            return int(expires_in.strip())
        except ValueError as exc:
            raise _build_app_error(
                code="hume_oauth_invalid_expires_in",
                message="Hume returned an invalid token expiry value.",
                http_status=502,
                retryable=True,
                details={"provider": "hume", "provider_status": provider_status},
            ) from exc

    raise _build_app_error(
        code="hume_oauth_missing_expires_in",
        message="Hume did not return a usable token expiry value.",
        http_status=502,
        retryable=True,
        details={"provider": "hume", "provider_status": provider_status},
    )
