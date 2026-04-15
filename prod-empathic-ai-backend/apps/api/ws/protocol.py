from typing import Any
from time import time_ns

from pydantic import BaseModel, ConfigDict, Field

from utils.ids import new_correlation_id


def _now_ms() -> int:
    return time_ns() // 1000000

##Wrapper contains all the info of the message from user
class WsEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    sent_at_ms: int = Field(ge=0)
    correlation_id: str | None = None

##forces all the info from Hume into what we need 
##especially prosody_score(emotinoal tone of user)
class EviUserMessagePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message_id: str = Field(min_length=1)
    role: str = Field(default="user", min_length=1)
    content: str = Field(min_length=1)
    interim: bool = False
    prosody_scores: dict[str, float] | None = None
    timestamp_ms: int | None = Field(default=None, ge=0)
    raw_event: dict[str, Any] | None = None

##payload(message) ai gives to user
class EviAssistantMessagePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message_id: str = Field(min_length=1)
    role: str = Field(default="assistant", min_length=1)
    content: str = Field(min_length=1)
    timestamp_ms: int | None = Field(default=None, ge=0)

##payload to user after the knowledge graph updates it has all the new nodes or edges
class KgDiffPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nodes_upsert: list[dict[str, Any]] = Field(default_factory=list)
    edges_upsert: list[dict[str, Any]] = Field(default_factory=list)
    receipts: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

##tells front what gem calls worked and which didn't 
class ToolCallsAppliedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    calls: list[dict[str, Any]] = Field(default_factory=list)
    dropped_calls: list[dict[str, Any]] = Field(default_factory=list)

##error to the user 
class ServerErrorPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    correlation_id: str | None = None
    retryable: bool = False
    details: dict[str, Any] | None = None

##summary 
class SummaryPartialPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1)
    based_on_message_id: str = Field(min_length=1)
    top_concepts: list[dict[str, Any]] = Field(default_factory=list)
    updated_at_ms: int = Field(ge=0)

##suggestions based on the convo
class CoachInsightWsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card: dict[str, Any]
    receipt_ids: list[str] = Field(default_factory=list)
    message_id: str = Field(min_length=1)

##put ai into high alert and makes it adapt fast
class SafetyWsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_level: str = Field(min_length=1)
    recommended_actions: list[str] = Field(default_factory=list)
    message_id: str = Field(min_length=1)
    rationale: str | None = None

##parse from json into envelope 
def parse_client_envelope(raw_packet: dict[str, Any]) -> WsEnvelope:
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

##takes payload wraps into the envelope, adds the timestamps 
##outputs clean dict ready to be sent to the websock
def build_ws_envelope(
    *,
    message_type: str,
    session_id: str,
    payload: dict[str, Any],
    correlation_id: str | None = None,
) -> dict[str, Any]:
    envelope = WsEnvelope(
        type=message_type,
        session_id=session_id,
        payload=payload,
        sent_at_ms=_now_ms(),
        correlation_id=correlation_id,
    )
    return envelope.model_dump()
