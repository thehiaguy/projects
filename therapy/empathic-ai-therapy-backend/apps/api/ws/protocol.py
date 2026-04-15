from typing import Any
from time import time_ns

from pydantic import BaseModel, ConfigDict, Field

from utils.ids import new_correlation_id


def _now_ms() -> int:
    return time_ns() // 1_000_000


class WsEnvelope(BaseModel):
    """
    Purpose:
        Canonical JSON envelope exchanged over `WS /ws/session/{session_id}`.

    Expected fields to add:
        - `type: str` (message discriminator; e.g., `evi.user_message.final`, `kg.diff`)
        - `session_id: str`
        - `payload: dict[str, Any]`
        - `sent_at_ms: int`
        - optional `correlation_id: str`

    Usage:
        Shared wrapper for both client->server and server->client websocket messages.
    """
    model_config = ConfigDict(extra="forbid")

    type: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    sent_at_ms: int = Field(ge=0)
    correlation_id: str | None = None


class EviUserMessagePayload(BaseModel):
    """
    Purpose:
        Schema for finalized (or interim) user transcript events forwarded from the browser's Hume EVI client.

    Expected fields to add:
        - `message_id: str`
        - `role: Literal["user"]`
        - `content: str`
        - `interim: bool` (default False)
        - `prosody_scores: dict[str, float] | None`
        - `timestamp_ms: int | None`
        - optional `raw_event: dict[str, Any]` for debugging

    Usage:
        `interim=True` messages should be ignored by KG mutation pipeline unless explicitly supported.
    """
    model_config = ConfigDict(extra="ignore")

    message_id: str = Field(min_length=1)
    role: str = Field(default="user", min_length=1)
    content: str = Field(min_length=1)
    interim: bool = False
    prosody_scores: dict[str, float] | None = None
    timestamp_ms: int | None = Field(default=None, ge=0)
    raw_event: dict[str, Any] | None = None


class EviAssistantMessagePayload(BaseModel):
    """
    Purpose:
        Schema for assistant transcript events forwarded from the browser for transcript/receipts context.

    Expected fields to add:
        - `message_id: str`
        - `role: Literal["assistant"]`
        - `content: str`
        - `timestamp_ms: int | None`

    Usage:
        Assistant messages may be stored for transcript context and UI display; KG updates are optional.
    """
    model_config = ConfigDict(extra="ignore")

    message_id: str = Field(min_length=1)
    role: str = Field(default="assistant", min_length=1)
    content: str = Field(min_length=1)
    timestamp_ms: int | None = Field(default=None, ge=0)


class KgDiffPayload(BaseModel):
    """
    Purpose:
        Payload emitted by backend when graph mutations were applied for a session.

    Expected fields to add:
        - `nodes_upsert: list[dict]` (or `list[KgNode]`)
        - `edges_upsert: list[dict]` (or `list[KgEdge]`)
        - `receipts: list[dict]` (or `list[Receipt]`)
        - optional `warnings: list[str]`

    Usage:
        Frontend applies upserts to live graph state and renders receipt/evidence UI.
    """
    model_config = ConfigDict(extra="forbid")

    nodes_upsert: list[dict[str, Any]] = Field(default_factory=list)
    edges_upsert: list[dict[str, Any]] = Field(default_factory=list)
    receipts: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ToolCallsAppliedPayload(BaseModel):
    """
    Purpose:
        Structured record of Gemini tool calls that passed validation and were executed.

    Expected fields to add:
        - `calls: list[dict]` where each item includes:
          `name`, `arguments`, `status`, `receipt_id`, `message_id`
        - `dropped_calls: list[dict]` for rejected/invalid calls

    Usage:
        Supports receipt transparency and debugging in the frontend.
    """
    model_config = ConfigDict(extra="forbid")

    calls: list[dict[str, Any]] = Field(default_factory=list)
    dropped_calls: list[dict[str, Any]] = Field(default_factory=list)


class ServerErrorPayload(BaseModel):
    """
    Purpose:
        Error payload sent over websocket when a request/event cannot be processed safely.

    Expected fields to add:
        - `code: str`
        - `message: str`
        - `correlation_id: str | None`
        - `retryable: bool`
        - optional `details: dict[str, Any]`

    Usage:
        Should be UI-safe; do not leak secrets or stack traces.
    """
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    correlation_id: str | None = None
    retryable: bool = False
    details: dict[str, Any] | None = None


class SummaryPartialPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1)
    based_on_message_id: str = Field(min_length=1)
    top_concepts: list[dict[str, Any]] = Field(default_factory=list)
    updated_at_ms: int = Field(ge=0)


class CoachInsightWsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card: dict[str, Any]
    receipt_ids: list[str] = Field(default_factory=list)
    message_id: str = Field(min_length=1)


class SafetyWsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_level: str = Field(min_length=1)
    recommended_actions: list[str] = Field(default_factory=list)
    message_id: str = Field(min_length=1)
    rationale: str | None = None


def parse_client_envelope(raw_packet: dict[str, Any]) -> WsEnvelope:
    """
    Purpose:
        Validate and normalize an incoming client websocket JSON packet into the canonical envelope model.

    Inputs:
        - `raw_packet`: JSON-decoded object from `websocket.receive_json()`.

    Returns:
        `WsEnvelope` populated with validated fields.

    Data structures / implementation notes:
        - Reject unknown/malformed top-level shapes
        - Attach a correlation ID if missing (optional normalization step)
        - Raise domain/app validation error used by `ws.session_ws` for `server.error` responses
    """
    if not isinstance(raw_packet, dict):
        raise ValueError("Websocket packet must be a JSON object")

    normalized = dict(raw_packet)
    normalized.setdefault("payload", {})
    normalized.setdefault("sent_at_ms", _now_ms())
    normalized.setdefault("correlation_id", new_correlation_id())
    envelope = WsEnvelope.model_validate(normalized)
    if not isinstance(envelope.payload, dict):
        raise ValueError("Envelope payload must be an object")
    return envelope


def build_ws_envelope(
    *,
    message_type: str,
    session_id: str,
    payload: dict[str, Any],
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """
    Purpose:
        Create a serializable websocket envelope for backend->client messages.

    Inputs:
        - `message_type`: event name (`kg.diff`, `server.error`, etc.)
        - `session_id`: session identifier
        - `payload`: message-specific JSON payload
        - `correlation_id`: optional tracing identifier

    Returns:
        JSON-serializable `dict` matching the `WsEnvelope` schema.

    Data structures / implementation notes:
        - Add `sent_at_ms` using server timestamp helper
        - Keep output strictly JSON-safe (no datetime objects)
    """
    envelope = WsEnvelope(
        type=message_type,
        session_id=session_id,
        payload=payload,
        sent_at_ms=_now_ms(),
        correlation_id=correlation_id,
    )
    return envelope.model_dump()
