from typing import Any, Callable

import neo4j

_driver: neo4j.Driver | None = None


def create_driver(*, uri: str, username: str, password: str) -> neo4j.Driver:
    global _driver
    _driver = neo4j.GraphDatabase.driver(
        uri,
        auth=(username, password),
        connection_timeout=3,
        max_transaction_retry_time=0,  # don't retry — fail fast
    )
    return _driver


def get_driver() -> neo4j.Driver:
    if _driver is None:
        raise RuntimeError("Neo4j driver not initialized. Call create_driver() first.")
    return _driver


def close_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def _get_database() -> str:
    from app.deps import get_settings
    return get_settings().neo4j_database


def execute_write(*, query_fn: Callable[..., Any], **kwargs: Any) -> Any:
    driver = get_driver()
    database = _get_database()
    with driver.session(database=database) as session:
        return session.execute_write(query_fn, **kwargs)


def execute_read(*, query_fn: Callable[..., Any], **kwargs: Any) -> Any:
    driver = get_driver()
    database = _get_database()
    with driver.session(database=database) as session:
        return session.execute_read(query_fn, **kwargs)
