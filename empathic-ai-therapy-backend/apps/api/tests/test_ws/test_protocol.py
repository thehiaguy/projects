"""Tests for WebSocket protocol parsing and envelope building."""
import time

import pytest

from utils.errors import AppError
from ws.protocol import (
    EviAssistantMessagePayload,
    EviUserMessagePayload,
    KgDiffPayload,
    ServerErrorPayload,
    ToolCallsAppliedPayload,
    WsEnvelope,
    build_ws_envelope,
    parse_client_envelope,
)


class TestWsEnvelope:
    def test_construction(self):
        env = WsEnvelope(type="client.ping", session_id="sess_1", payload={})
        assert env.type == "client.ping"
        assert env.session_id == "sess_1"
        assert isinstance(env.sent_at_ms, int)

    def test_default_payload(self):
        env = WsEnvelope(type="t", session_id="s")
        assert env.payload == {}

    def test_sent_at_ms_is_recent(self):
        before = int(time.time() * 1000) - 100
        env = WsEnvelope(type="t", session_id="s")
        after = int(time.time() * 1000) + 100
        assert before <= env.sent_at_ms <= after


class TestEviUserMessagePayload:
    def test_defaults(self):
        payload = EviUserMessagePayload(message_id="msg_1", content="Hello")
        assert payload.role == "user"
        assert payload.interim is False
        assert payload.prosody_scores is None

    def test_with_prosody(self):
        payload = EviUserMessagePayload(
            message_id="m", content="text",
            prosody_scores={"joy": 0.8}
        )
        assert payload.prosody_scores["joy"] == pytest.approx(0.8)

    def test_interim_flag(self):
        payload = EviUserMessagePayload(message_id="m", content="t", interim=True)
        assert payload.interim is True


class TestEviAssistantMessagePayload:
    def test_defaults(self):
        payload = EviAssistantMessagePayload(
            message_id="msg_1", content="How are you?"
        )
        assert payload.role == "assistant"
        assert payload.timestamp_ms is None


class TestKgDiffPayload:
    def test_defaults(self):
        payload = KgDiffPayload()
        assert payload.nodes_upsert == []
        assert payload.edges_upsert == []
        assert payload.receipts == []
        assert payload.warnings == []

    def test_with_data(self):
        payload = KgDiffPayload(
            nodes_upsert=[{"id": "n1"}],
            warnings=["low confidence"],
        )
        assert len(payload.nodes_upsert) == 1
        assert "low confidence" in payload.warnings


class TestServerErrorPayload:
    def test_construction(self):
        payload = ServerErrorPayload(
            code="internal_error",
            message="Something went wrong",
        )
        assert payload.retryable is False
        assert payload.details == {}
        assert payload.correlation_id is None


class TestParseClientEnvelope:
    def test_valid_packet(self):
        raw = {
            "type": "client.ping",
            "session_id": "sess_1",
            "payload": {},
        }
        env = parse_client_envelope(raw)
        assert env.type == "client.ping"
        assert env.session_id == "sess_1"

    def test_missing_type_raises(self):
        raw = {"session_id": "sess_1", "payload": {}}
        with pytest.raises(AppError) as exc_info:
            parse_client_envelope(raw)
        assert exc_info.value.code == "missing_type"

    def test_missing_session_id_raises(self):
        raw = {"type": "client.ping", "payload": {}}
        with pytest.raises(AppError) as exc_info:
            parse_client_envelope(raw)
        assert exc_info.value.code == "missing_session_id"

    def test_non_dict_raises(self):
        with pytest.raises(AppError) as exc_info:
            parse_client_envelope("not a dict")  # type: ignore
        assert exc_info.value.code == "invalid_packet"

    def test_correlation_id_auto_generated(self):
        raw = {"type": "t", "session_id": "s", "payload": {}}
        env = parse_client_envelope(raw)
        assert env.correlation_id is not None
        assert env.correlation_id.startswith("corr_")

    def test_existing_correlation_id_preserved(self):
        raw = {
            "type": "t",
            "session_id": "s",
            "payload": {},
            "correlation_id": "corr_existing",
        }
        env = parse_client_envelope(raw)
        assert env.correlation_id == "corr_existing"


class TestBuildWsEnvelope:
    def test_structure(self):
        envelope = build_ws_envelope(
            message_type="kg.diff",
            session_id="sess_1",
            payload={"nodes_upsert": []},
        )
        assert envelope["type"] == "kg.diff"
        assert envelope["session_id"] == "sess_1"
        assert isinstance(envelope["sent_at_ms"], int)
        assert "correlation_id" in envelope

    def test_custom_correlation_id(self):
        envelope = build_ws_envelope(
            message_type="t",
            session_id="s",
            payload={},
            correlation_id="corr_custom",
        )
        assert envelope["correlation_id"] == "corr_custom"

    def test_auto_correlation_id(self):
        envelope = build_ws_envelope(message_type="t", session_id="s", payload={})
        assert envelope["correlation_id"].startswith("corr_")

    def test_sent_at_ms_is_int(self):
        envelope = build_ws_envelope(message_type="t", session_id="s", payload={})
        assert isinstance(envelope["sent_at_ms"], int)

    def test_payload_included(self):
        envelope = build_ws_envelope(
            message_type="t",
            session_id="s",
            payload={"key": "value", "num": 42},
        )
        assert envelope["payload"]["key"] == "value"
        assert envelope["payload"]["num"] == 42
