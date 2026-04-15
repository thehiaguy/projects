from typing import Any
import logging

_CONFIGURED = False


def configure_logging(*, level: str) -> None:
    """
    Purpose:
        Configure structured or standard logging for the backend application.

    Inputs:
        - `level`: log level string from settings (`DEBUG`, `INFO`, etc.)

    Returns:
        None.

    Data structures / implementation notes:
        - Centralize formatter, timestamp format, and correlation-id enrichment
        - Avoid logging secrets, auth headers, or raw provider credentials
    """
    global _CONFIGURED
    if _CONFIGURED:
        logging.getLogger().setLevel(level.upper())
        return

    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    _CONFIGURED = True


def get_logger(name: str) -> Any:
    """
    Purpose:
        Return a module-level logger instance with project-standard configuration.

    Inputs:
        - `name`: logger namespace (usually `__name__`).

    Returns:
        Logger object (`logging.Logger` or wrapper).
    """
    return logging.getLogger(name)


def log_ws_event(
    *,
    direction: str,
    session_id: str,
    message_type: str,
    correlation_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """
    Purpose:
        Emit consistent logs for websocket inbound/outbound packets to aid realtime debugging.

    Inputs:
        - `direction`: `"in"` or `"out"`
        - `session_id`: websocket session id
        - `message_type`: packet discriminator
        - `correlation_id`: optional tracing id
        - `extra`: optional sanitized metadata (counts, latency, warnings)

    Returns:
        None.

    Data structures / implementation notes:
        - Never log raw transcript text if privacy constraints require redaction
        - Prefer payload summaries over full packet dumps in production
    """
    logger = get_logger("ws")
    payload = {
        "direction": direction,
        "session_id": session_id,
        "message_type": message_type,
        "correlation_id": correlation_id,
    }
    if extra:
        payload["extra"] = extra
    logger.info("ws_event %s", payload)
