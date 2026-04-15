import time
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from orchestration.kg_updater import process_utterance_event
from utils.errors import AppError, to_server_error_payload
from utils.ids import new_correlation_id
from utils.logging import get_logger, log_ws_event
from ws.protocol import (
    EviUserMessagePayload,
    build_ws_envelope,
    parse_client_envelope,
)

router = APIRouter(tags=["ws"])
logger = get_logger(__name__)


@router.websocket("/ws/session/{session_id}")
async def session_ws_endpoint(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    log_ws_event(direction="in", session_id=session_id, message_type="connected")

    try:
        while True:
            raw_packet = await receive_client_packet(websocket)
            if raw_packet is None:
                break
            await process_client_packet(
                session_id=session_id,
                raw_packet=raw_packet,
                websocket=websocket,
            )
    except WebSocketDisconnect:
        log_ws_event(direction="in", session_id=session_id, message_type="disconnected")
    except Exception as exc:
        logger.exception("Unexpected WS error for session %s", session_id)
        corr_id = new_correlation_id()
        payload = to_server_error_payload(exc, correlation_id=corr_id)
        try:
            await websocket.send_json(
                build_ws_envelope(
                    message_type="server.error",
                    session_id=session_id,
                    payload=payload,
                    correlation_id=corr_id,
                )
            )
        except Exception:
            pass


async def receive_client_packet(websocket: WebSocket) -> dict[str, Any] | None:
    try:
        return await websocket.receive_json()
    except WebSocketDisconnect:
        return None
    except Exception as exc:
        logger.warning("Failed to receive packet: %s", exc)
        return None


async def process_client_packet(
    *,
    session_id: str,
    raw_packet: dict[str, Any],
    websocket: WebSocket,
) -> None:
    corr_id = raw_packet.get("correlation_id") or new_correlation_id()

    try:
        envelope = parse_client_envelope(raw_packet)
    except AppError as exc:
        await send_server_error(
            websocket=websocket,
            session_id=session_id,
            code=exc.code,
            message=exc.message,
            correlation_id=corr_id,
        )
        return

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
            payload={"server_ts_ms": int(time.time() * 1000)},
            correlation_id=envelope.correlation_id,
        )
        await websocket.send_json(pong)

    elif envelope.type == "evi.user_message.final":
        await handle_evi_user_message_event(
            session_id=session_id,
            payload=envelope.payload,
            websocket=websocket,
            correlation_id=envelope.correlation_id,
        )

    elif envelope.type == "evi.assistant_message":
        # Store assistant messages for context — no KG mutation needed
        pass

    elif envelope.type == "evi.chat_metadata":
        pass

    else:
        await send_server_error(
            websocket=websocket,
            session_id=session_id,
            code="unknown_message_type",
            message=f"Unknown message type: {envelope.type}",
            correlation_id=corr_id,
        )


async def handle_evi_user_message_event(
    *,
    session_id: str,
    payload: dict[str, Any],
    websocket: WebSocket,
    correlation_id: str | None = None,
) -> None:
    # Skip interim messages early
    if payload.get("interim", False):
        return

    corr_id = correlation_id or new_correlation_id()
    try:
        result = await process_utterance_event(
            session_id=session_id,
            evi_user_message=payload,
        )
    except Exception as exc:
        logger.exception("KG update failed for session %s", session_id)
        err_payload = to_server_error_payload(exc, correlation_id=corr_id)
        await send_server_error(
            websocket=websocket,
            session_id=session_id,
            code=err_payload["code"],
            message=err_payload["message"],
            correlation_id=corr_id,
            retryable=err_payload.get("retryable", False),
        )
        return

    kg_diff = result.get("kg_diff", {})
    tool_calls_applied = result.get("tool_calls_applied", {})
    warnings = result.get("warnings", [])

    # Send kg.diff
    await websocket.send_json(
        build_ws_envelope(
            message_type="kg.diff",
            session_id=session_id,
            payload={
                "nodes_upsert": kg_diff.get("nodes_upsert", []),
                "edges_upsert": kg_diff.get("edges_upsert", []),
                "receipts": kg_diff.get("receipts", []),
                "warnings": warnings,
            },
            correlation_id=corr_id,
        )
    )

    # Send kg.tool_calls_applied
    await websocket.send_json(
        build_ws_envelope(
            message_type="kg.tool_calls_applied",
            session_id=session_id,
            payload=tool_calls_applied,
            correlation_id=corr_id,
        )
    )

    log_ws_event(
        direction="out",
        session_id=session_id,
        message_type="kg.diff",
        correlation_id=corr_id,
        extra={
            "nodes": len(kg_diff.get("nodes_upsert", [])),
            "edges": len(kg_diff.get("edges_upsert", [])),
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
    payload = {
        "code": code,
        "message": message,
        "correlation_id": correlation_id,
        "retryable": retryable,
        "details": details or {},
    }
    try:
        await websocket.send_json(
            build_ws_envelope(
                message_type="server.error",
                session_id=session_id,
                payload=payload,
                correlation_id=correlation_id,
            )
        )
    except Exception as exc:
        logger.warning("Failed to send server.error to client: %s", exc)
