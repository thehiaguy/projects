from typing import Any

from fastapi import HTTPException


class AppError(Exception):
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
    error.correlation_id = correlation_id
    return error
