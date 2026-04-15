from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool

from orchestration.kg_updater import process_utterance_event
from services.neo4j.repo_sessions import get_session_record
from services.neo4j.repo_utterances import upsert_utterance
from utils.errors import AppError, to_server_error_payload, with_correlation_id
from utils.ids import new_correlation_id, new_utterance_id
from utils.logging import get_logger, log_ws_event
from utils.security import extract_bearer_token, verify_session_token
from ws.protocol import (
    EviAssistantMessagePayload,
    EviUserMessagePayload,
    build_ws_envelope,
    parse_client_envelope,
)

router = APIRouter(tags=["ws"])
logger = get_logger(__name__)


@router.websocket("/ws/session/{session_id}")
async def session_ws_endpoint(websocket: WebSocket, session_id: str) -> None:
    """
    Purpose:
        Main realtime channel for client->backend forwarded EVI events and backend->client KG updates.

    Inputs:
        - `websocket`: FastAPI WebSocket connection object
        - `session_id`: path parameter identifying the active session

    Returns:
        None. Runs an async receive/process/send loop until disconnect.

    Data structures / implementation notes:
        - Accept JSON packets only for KG stream
        - Supported incoming types:
          `evi.user_message.final`, `evi.assistant_message`, `evi.chat_metadata`, `client.ping`
        - Outgoing types:
          `kg.diff`, `kg.tool_calls_applied`, `summary.partial`, `server.error`
        - Voice audio stays direct-to-Hume; this WS is for text/events/graph only
    """
    await websocket.accept()

    try:
        token = (
            websocket.query_params.get("session_token")
            or extract_bearer_token(websocket.headers.get("authorization"))
        )
        if not token:
            raise AppError(
                "A session token is required to open the websocket.",
                code="session_token_required",
                http_status=401,
                retryable=False,
            )
        verify_session_token(token=token, expected_session_id=session_id)
    except Exception as exc:
        await send_server_error(
            websocket=websocket,
            session_id=session_id,
            code=getattr(exc, "code", "invalid_session_token"),
            message=getattr(exc, "message", str(exc)),
            correlation_id=getattr(exc, "correlation_id", None),
            retryable=False,
            details=getattr(exc, "details", None),
        )
        await websocket.close(code=4401)
        return

    session = await run_in_threadpool(get_session_record, session_id=session_id)
    if session is None:
        await send_server_error(
            websocket=websocket,
            session_id=session_id,
            code="session_not_found",
            message=f"Session {session_id} was not found.",
            retryable=False,
        )
        await websocket.close(code=4404)
        return

    while True:
        try:
            raw_packet = await receive_client_packet(websocket)
            await process_client_packet(
                session_id=session_id,
                raw_packet=raw_packet,
                websocket=websocket,
            )
        except WebSocketDisconnect:
            logger.info("websocket disconnected for session %s", session_id)
            return
        except Exception as exc:
            await send_server_error(
                websocket=websocket,
                session_id=session_id,
                code=getattr(exc, "code", "ws_processing_error"),
                message=getattr(exc, "message", str(exc)),
                correlation_id=getattr(exc, "correlation_id", None),
                retryable=getattr(exc, "retryable", False),
                details=getattr(exc, "details", None),
            )


async def receive_client_packet(websocket: WebSocket) -> dict[str, Any]:
    """
    Purpose:
        Read a single JSON packet from the websocket and return the decoded object.

    Inputs:
        - `websocket`: active FastAPI WebSocket connection.

    Returns:
        JSON object representing the raw client packet.

    Data structures / implementation notes:
        - Use `receive_json`
        - Handle disconnect exceptions and malformed JSON separately
        - Size and timeout handling may be configured globally via Uvicorn/settings
    """
    packet = await websocket.receive_json()
    if not isinstance(packet, dict):
        raise AppError(
            "Websocket packet must be a JSON object.",
            code="invalid_ws_packet",
            http_status=400,
            retryable=False,
        )
    return packet


async def process_client_packet(
    *,
    session_id: str,
    raw_packet: dict[str, Any],
    websocket: WebSocket,
) -> None:
    """
    Purpose:
        Route a validated client packet to the correct handler (ping, EVI user message, assistant message, metadata).

    Inputs:
        - `session_id`: websocket session path id
        - `raw_packet`: JSON payload received from client
        - `websocket`: connection for sending responses

    Returns:
        None. Sends zero or more backend packets to the client.

    Data structures / implementation notes:
        - Parse via `ws.protocol.parse_client_envelope`
        - For `evi.user_message.final`, invoke KG updater orchestration
        - For `client.ping`, reply with server timestamp / pong envelope
    """
    envelope = parse_client_envelope(raw_packet)
    if envelope.session_id != session_id:
        raise AppError(
            "Packet session_id does not match websocket path session_id.",
            code="session_id_mismatch",
            http_status=400,
            retryable=False,
            correlation_id=envelope.correlation_id,
        )

    log_ws_event(
        direction="in",
        session_id=session_id,
        message_type=envelope.type,
        correlation_id=envelope.correlation_id,
    )

    if envelope.type == "client.ping":
        pong = build_ws_envelope(
            message_type="server.pong",
            session_id=session_id,
            payload={"ok": True},
            correlation_id=envelope.correlation_id,
        )
        await websocket.send_json(pong)
        return

    if envelope.type == "evi.user_message.final":
        await handle_evi_user_message_event(
            session_id=session_id,
            payload=envelope.payload,
            websocket=websocket,
        )
        return

    if envelope.type == "evi.assistant_message":
        payload = EviAssistantMessagePayload.model_validate(envelope.payload)
        await run_in_threadpool(
            upsert_utterance,
            utterance_id=new_utterance_id(),
            session_id=session_id,
            role=payload.role,
            text=payload.content,
            message_id=payload.message_id,
            timestamp_ms=payload.timestamp_ms,
        )
        await websocket.send_json(
            build_ws_envelope(
                message_type="server.ack",
                session_id=session_id,
                payload={"accepted_type": envelope.type, "message_id": payload.message_id},
                correlation_id=envelope.correlation_id,
            )
        )
        return

    if envelope.type == "evi.chat_metadata":
        await websocket.send_json(
            build_ws_envelope(
                message_type="server.ack",
                session_id=session_id,
                payload={"accepted_type": envelope.type},
                correlation_id=envelope.correlation_id,
            )
        )
        return

    raise AppError(
        f"Unsupported websocket packet type: {envelope.type}",
        code="unsupported_ws_message_type",
        http_status=400,
        retryable=False,
        correlation_id=envelope.correlation_id,
    )


async def handle_evi_user_message_event(
    *,
    session_id: str,
    payload: dict[str, Any],
    websocket: WebSocket,
) -> None:
    """
    Purpose:
        Process a finalized user transcript + prosody event and emit KG diffs/tool-call receipts back to client.

    Inputs:
        - `session_id`: active session identifier
        - `payload`: JSON matching `EviUserMessagePayload`
        - `websocket`: active connection used to send `kg.diff` and related packets

    Returns:
        None. Sends backend events based on processing result.

    Data structures / implementation notes:
        - Drop interim transcripts unless explicitly enabled
        - Persist utterance/prosody first, then run KG updater
        - KG updater result should include `nodes_upsert`, `edges_upsert`, and `receipts`
    """
    event = EviUserMessagePayload.model_validate(payload)
    result = await process_utterance_event(
        session_id=session_id,
        evi_user_message=event.model_dump(),
    )

    await websocket.send_json(
        build_ws_envelope(
            message_type="kg.diff",
            session_id=session_id,
            payload=result["kg_diff"],
        )
    )
    await websocket.send_json(
        build_ws_envelope(
            message_type="kg.tool_calls_applied",
            session_id=session_id,
            payload=result["tool_calls_applied"],
        )
    )
    if result.get("summary_partial"):
        await websocket.send_json(
            build_ws_envelope(
                message_type="summary.partial",
                session_id=session_id,
                payload=result["summary_partial"],
            )
        )
    if result.get("coach_insight"):
        await websocket.send_json(
            build_ws_envelope(
                message_type="coach.insight",
                session_id=session_id,
                payload=result["coach_insight"],
            )
        )
    if result.get("safety_event"):
        safety_event = result["safety_event"]
        await websocket.send_json(
            build_ws_envelope(
                message_type=str(safety_event["type"]),
                session_id=session_id,
                payload=dict(safety_event["payload"]),
            )
        )

    log_ws_event(
        direction="out",
        session_id=session_id,
        message_type="kg.diff",
        extra={
            "node_count": len(result["kg_diff"].get("nodes_upsert", [])),
            "edge_count": len(result["kg_diff"].get("edges_upsert", [])),
            "receipt_count": len(result["kg_diff"].get("receipts", [])),
        },
    )


async def send_server_error(
    *,
    websocket: WebSocket,
    session_id: str,
    code: str,
    message: str,
    correlation_id: str | None = None,
    retryable: bool = False,
    details: dict[str, Any] | None = None,
) -> None:
    """
    Purpose:
        Send a standardized websocket error envelope to the client without closing the connection immediately.

    Inputs:
        - `websocket`: active connection
        - `session_id`: session identifier for envelope
        - `code`: stable machine-readable error code
        - `message`: UI-safe human-readable message
        - `correlation_id`: optional trace id
        - `retryable`: whether the client may retry/resend
        - `details`: optional structured error metadata (non-sensitive)

    Returns:
        None. Sends `server.error` JSON packet.

    Data structures / implementation notes:
        - Reuse `ws.protocol.build_ws_envelope`
        - Keep payload schema aligned with `ServerErrorPayload`
    """
    if correlation_id:
        payload = {
            "code": code,
            "message": message,
            "retryable": retryable,
            "correlation_id": correlation_id,
            "details": details,
        }
    else:
        error = with_correlation_id(
            AppError(
                message,
                code=code,
                retryable=retryable,
                details=details,
            ),
            new_correlation_id(),
        )
        payload = to_server_error_payload(error)

    await websocket.send_json(
        build_ws_envelope(
            message_type="server.error",
            session_id=session_id,
            payload=payload,
            correlation_id=payload.get("correlation_id"),
        )
    )
