import base64
import hashlib
import hmac
import json
from time import time_ns
from typing import Any

from apps.api.core.config import get_settings
from utils.errors import AppError


def _now_s() -> int:
    return time_ns() // 1_000_000_000


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(f"{data}{padding}".encode("ascii"))


def create_session_token(*, session_id: str, expires_in_seconds: int | None = None) -> str:
    settings = get_settings()
    issued_at = _now_s()
    expires_at = issued_at + int(expires_in_seconds or settings.session_token_ttl_seconds)

    payload = {
        "session_id": session_id,
        "scope": "ws",
        "iat": issued_at,
        "exp": expires_at,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_segment = _b64url_encode(payload_bytes)
    signature = hmac.new(
        settings.session_signing_secret.encode("utf-8"),
        payload_segment.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{payload_segment}.{_b64url_encode(signature)}"


def verify_session_token(*, token: str, expected_session_id: str | None = None) -> dict[str, Any]:
    settings = get_settings()

    try:
        payload_segment, signature_segment = token.split(".", 1)
    except ValueError as exc:
        raise AppError(
            "Session token is malformed.",
            code="invalid_session_token",
            http_status=401,
            retryable=False,
        ) from exc

    expected_signature = hmac.new(
        settings.session_signing_secret.encode("utf-8"),
        payload_segment.encode("ascii"),
        hashlib.sha256,
    ).digest()
    actual_signature = _b64url_decode(signature_segment)
    if not hmac.compare_digest(expected_signature, actual_signature):
        raise AppError(
            "Session token signature is invalid.",
            code="invalid_session_token",
            http_status=401,
            retryable=False,
        )

    try:
        payload = json.loads(_b64url_decode(payload_segment).decode("utf-8"))
    except Exception as exc:
        raise AppError(
            "Session token payload is malformed.",
            code="invalid_session_token",
            http_status=401,
            retryable=False,
        ) from exc

    if not isinstance(payload, dict):
        raise AppError(
            "Session token payload is invalid.",
            code="invalid_session_token",
            http_status=401,
            retryable=False,
        )

    if payload.get("scope") != "ws":
        raise AppError(
            "Session token scope is invalid.",
            code="invalid_session_token",
            http_status=401,
            retryable=False,
        )

    if int(payload.get("exp", 0)) < _now_s():
        raise AppError(
            "Session token has expired.",
            code="session_token_expired",
            http_status=401,
            retryable=False,
        )

    if expected_session_id and payload.get("session_id") != expected_session_id:
        raise AppError(
            "Session token does not match the requested session.",
            code="session_token_mismatch",
            http_status=401,
            retryable=False,
            details={"expected_session_id": expected_session_id},
        )

    return payload


def extract_bearer_token(value: str | None) -> str | None:
    if not value:
        return None
    parts = value.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None
