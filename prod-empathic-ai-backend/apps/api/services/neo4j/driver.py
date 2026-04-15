from typing import Any, Callable

from apps.api.utils.errors import AppError

try:
    from neo4j import GraphDatabase
    from neo4j.exceptions import Neo4jError
except ImportError:  # pragma: no cover - handled at runtime when dependency is missing
    GraphDatabase = None
    Neo4jError = Exception

_driver: Any | None = None


def create_driver(
    *,
    uri: str,
    username: str,
    password: str,
) -> Any:
    global _driver

    if _driver is not None:
        return _driver

    if GraphDatabase is None:
        raise _build_app_error(
            code="neo4j_driver_dependency_missing",
            message="The Neo4j Python driver is not installed.",
            http_status=500,
            retryable=False,
        )

    driver = None
    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        driver.verify_connectivity()
    except Exception as exc:  # pragma: no cover - depends on live driver/runtime
        if driver is not None:
            driver.close()
        raise _build_app_error(
            code="neo4j_connect_failed",
            message="Failed to connect to Neo4j.",
            http_status=500,
            retryable=True,
            details={"uri": uri, "username": username},
        ) from exc

    _driver = driver
    return _driver


def get_driver() -> Any:
    if _driver is None:
        raise _build_app_error(
            code="neo4j_driver_uninitialized",
            message="Neo4j driver has not been initialized.",
            http_status=500,
            retryable=False,
        )
    return _driver


def close_driver() -> None:
    global _driver

    if _driver is not None:
        _driver.close()
        _driver = None


def execute_write(
    *,
    query_fn: Callable[..., Any],
    **kwargs: Any,
) -> Any:
    driver = get_driver()
    database = _get_database_name()

    try:
        with driver.session(database=database) as session:
            return session.execute_write(query_fn, **kwargs)
    except Neo4jError as exc:  # pragma: no cover - depends on live driver/runtime
        raise _build_app_error(
            code="neo4j_write_failed",
            message="Neo4j write transaction failed.",
            http_status=500,
            retryable=True,
            details={"database": database, "query_fn": getattr(query_fn, "__name__", "unknown")},
        ) from exc


def execute_read(
    *,
    query_fn: Callable[..., Any],
    **kwargs: Any,
) -> Any:
    driver = get_driver()
    database = _get_database_name()

    try:
        with driver.session(database=database) as session:
            return session.execute_read(query_fn, **kwargs)
    except Neo4jError as exc:  # pragma: no cover - depends on live driver/runtime
        raise _build_app_error(
            code="neo4j_read_failed",
            message="Neo4j read transaction failed.",
            http_status=500,
            retryable=True,
            details={"database": database, "query_fn": getattr(query_fn, "__name__", "unknown")},
        ) from exc


def _get_database_name() -> str:
    from app.deps import get_settings

    return get_settings().neo4j_database


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
