import logging
from typing import Any


def configure_logging(*, level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_ws_event(
    *,
    direction: str,
    session_id: str,
    message_type: str,
    correlation_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    logger = get_logger("ws.events")
    logger.info(
        "[ws:%s] session=%s type=%s corr=%s extra=%s",
        direction,
        session_id,
        message_type,
        correlation_id,
        extra,
    )
