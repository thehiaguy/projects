import time
from typing import Any, Literal

from pydantic import BaseModel, Field

from utils.errors import AppError
from utils.ids import new_correlation_id


class WsEnvelope(BaseModel):
    type: str
    session_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    sent_at_ms: int = Field(default_factory=lambda: int(time.time() * 1000))
    correlation_id: str | None = None


class EviUserMessagePayload(BaseModel):
    message_id: str
    role: Literal["user"] = "user"
    content: str
    interim: bool = False
    prosody_scores: dict[str, float] | None = None
    timestamp_ms: int | None = None
    raw_event: dict[str, Any] | None = None


class EviAssistantMessagePayload(BaseModel):
    message_id: str
    role: Literal["assistant"] = "assistant"
    content: str
    timestamp_ms: int | None = None


class KgDiffPayload(BaseModel):
    nodes_upsert: list[dict[str, Any]] = Field(default_factory=list)
    edges_upsert: list[dict[str, Any]] = Field(default_factory=list)
    receipts: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ToolCallsAppliedPayload(BaseModel):
    calls: list[dict[str, Any]] = Field(default_factory=list)
    dropped_calls: list[dict[str, Any]] = Field(default_factory=list)


class ServerErrorPayload(BaseModel):
    code: str
    message: str
    correlation_id: str | None = None
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


def parse_client_envelope(raw_packet: dict[str, Any]) -> WsEnvelope:
    if not isinstance(raw_packet, dict):
        raise AppError(
            code="invalid_packet",
            message="WebSocket packet must be a JSON object.",
            http_status=400,
        )
    if "type" not in raw_packet:
        raise AppError(
            code="missing_type",
            message="WebSocket packet missing required 'type' field.",
            http_status=400,
        )
    if "session_id" not in raw_packet:
        raise AppError(
            code="missing_session_id",
            message="WebSocket packet missing required 'session_id' field.",
            http_status=400,
        )

    if "correlation_id" not in raw_packet or not raw_packet["correlation_id"]:
        raw_packet = {**raw_packet, "correlation_id": new_correlation_id()}

    return WsEnvelope(**raw_packet)


def build_ws_envelope(
    *,
    message_type: str,
    session_id: str,
    payload: dict[str, Any],
    correlation_id: str | None = None,
) -> dict[str, Any]:
    return {
        "type": message_type,
        "session_id": session_id,
        "payload": payload,
        "sent_at_ms": int(time.time() * 1000),
        "correlation_id": correlation_id or new_correlation_id(),
    }
