from typing import Any

from fastapi import HTTPException


class AppError(Exception):
    """
    Purpose:
        Base application exception carrying structured error metadata for REST and websocket handlers.

    Expected attributes to add:
        - `code: str` (stable machine-readable code)
        - `message: str` (safe human-readable message)
        - `http_status: int`
        - `retryable: bool`
        - `correlation_id: str | None`
        - `details: dict[str, Any] | None`

    Usage:
        Raise from service/repository/orchestration layers and translate at API boundaries.
    """
    def __init__(
        self,
        message: str,
        *,
        code: str = "app_error",
        http_status: int = 400,
        retryable: bool = False,
        correlation_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.retryable = retryable
        self.correlation_id = correlation_id
        self.details = details or {}


def to_http_exception(error: AppError) -> Any:
    """
    Purpose:
        Convert an `AppError` into a FastAPI/Starlette HTTP exception with consistent JSON error shape.

    Inputs:
        - `error`: structured application error instance.

    Returns:
        HTTP exception object suitable for raising from REST routes.

    Data structures / implementation notes:
        - Response body should include `code`, `message`, and `correlation_id`
        - Avoid exposing internal stack traces or secrets
    """
    return HTTPException(
        status_code=error.http_status,
        detail={
            "code": error.code,
            "message": error.message,
            "correlation_id": error.correlation_id,
            "details": error.details or None,
        },
    )


def to_server_error_payload(error: Exception, *, correlation_id: str | None = None) -> dict[str, Any]:
    """
    Purpose:
        Normalize any exception into the websocket `server.error` payload schema.

    Inputs:
        - `error`: raised exception (`AppError` or unexpected exception)
        - `correlation_id`: optional trace id to include in payload

    Returns:
        Dict matching `ws.protocol.ServerErrorPayload` shape:
        - `code`, `message`, `retryable`, `correlation_id`, optional `details`

    Data structures / implementation notes:
        - Unexpected exceptions should be mapped to a generic internal error code/message
        - Preserve `retryable` only for known transient failures
    """
    if isinstance(error, AppError):
        return {
            "code": error.code,
            "message": error.message,
            "retryable": error.retryable,
            "correlation_id": correlation_id or error.correlation_id,
            "details": error.details or None,
        }

    return {
        "code": "internal_error",
        "message": "An unexpected internal error occurred.",
        "retryable": False,
        "correlation_id": correlation_id,
        "details": None,
    }


def with_correlation_id(error: AppError, correlation_id: str) -> AppError:
    """
    Purpose:
        Attach or override a correlation ID on an `AppError` before re-raising/returning.

    Inputs:
        - `error`: structured application error
        - `correlation_id`: trace id generated for the current request/event

    Returns:
        The same or copied `AppError` instance with correlation metadata set.

    Data structures / implementation notes:
        - Decide whether mutation or copying is preferred for your error model
    """
    error.correlation_id = correlation_id
    return error
