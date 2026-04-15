from typing import Any
import logging

_CONFIGURED = False


def configure_logging(*, level: str) -> None:
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
    return logging.getLogger(name)


def log_ws_event(
    *,
    direction: str,
    session_id: str,
    message_type: str,
    correlation_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
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
