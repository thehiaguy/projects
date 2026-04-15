from typing import Any, Callable

from utils.errors import AppError

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
    """
    Purpose:
        Construct a Neo4j driver connection object using application credentials.

    Inputs:
        - `uri`: Neo4j connection URI (e.g., `bolt://localhost:7687`)
        - `username`: Neo4j username
        - `password`: Neo4j password

    Returns:
        Neo4j driver instance (from official Python driver).

    Data structures / implementation notes:
        - Driver should be created once and reused globally
        - Verify connectivity on startup (optional but recommended)
    """
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
    """
    Purpose:
        Return the initialized singleton Neo4j driver used across repositories/services.

    Inputs:
        None.

    Returns:
        Neo4j driver instance.

    Data structures / implementation notes:
        - Raise clear error if called before initialization
        - Backed by module-level cache or app state
    """
    if _driver is None:
        raise _build_app_error(
            code="neo4j_driver_uninitialized",
            message="Neo4j driver has not been initialized.",
            http_status=500,
            retryable=False,
        )
    return _driver


def close_driver() -> None:
    """
    Purpose:
        Close the shared Neo4j driver during app shutdown.

    Inputs:
        None.

    Returns:
        None.

    Data structures / implementation notes:
        - Safe to call multiple times (idempotent behavior recommended)
        - Clear cached singleton after closing
    """
    global _driver

    if _driver is not None:
        _driver.close()
        _driver = None


def execute_write(
    *,
    query_fn: Callable[..., Any],
    **kwargs: Any,
) -> Any:
    """
    Purpose:
        Run a managed Neo4j write transaction using a short-lived session and a repository transaction callback.

    Inputs:
        - `query_fn`: transaction callback accepting `(tx, **kwargs)`
        - `**kwargs`: callback arguments (query parameters / domain objects)

    Returns:
        Arbitrary callback result (records transformed into domain dicts/models).

    Data structures / implementation notes:
        - Open `with driver.session(database=...) as session`
        - Use `session.execute_write(query_fn, **kwargs)` pattern
        - Sessions are not thread-safe; create per operation
    """
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
    """
    Purpose:
        Run a managed Neo4j read transaction using a short-lived session and callback.

    Inputs:
        - `query_fn`: transaction callback accepting `(tx, **kwargs)`
        - `**kwargs`: callback arguments

    Returns:
        Arbitrary callback result.

    Data structures / implementation notes:
        - Use `session.execute_read(...)`
        - Keep transaction functions pure (no external side effects)
    """
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
