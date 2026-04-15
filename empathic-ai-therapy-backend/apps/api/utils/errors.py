from typing import Any

from fastapi import HTTPException


class AppError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        http_status: int = 500,
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
        self.details: dict[str, Any] = details or {}


def to_http_exception(error: AppError) -> HTTPException:
    return HTTPException(
        status_code=error.http_status,
        detail={
            "code": error.code,
            "message": error.message,
            "correlation_id": error.correlation_id,
        },
    )


def to_server_error_payload(
    error: Exception, *, correlation_id: str | None = None
) -> dict[str, Any]:
    if isinstance(error, AppError):
        return {
            "code": error.code,
            "message": error.message,
            "retryable": error.retryable,
            "correlation_id": correlation_id or error.correlation_id,
            "details": error.details,
        }
    return {
        "code": "internal_error",
        "message": "An unexpected error occurred.",
        "retryable": False,
        "correlation_id": correlation_id,
        "details": {},
    }


def with_correlation_id(error: AppError, correlation_id: str) -> AppError:
    error.correlation_id = correlation_id
    return error
