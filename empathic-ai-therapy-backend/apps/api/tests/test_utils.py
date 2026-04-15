"""Tests for utility modules: ids, errors, logging."""
import pytest

from utils.ids import (
    new_correlation_id,
    new_prosody_frame_id,
    new_receipt_id,
    new_session_id,
    new_utterance_id,
)
from utils.errors import (
    AppError,
    to_http_exception,
    to_server_error_payload,
    with_correlation_id,
)
from utils.logging import configure_logging, get_logger, log_ws_event


# ── ID generators ──────────────────────────────────────────────────────────────

class TestIdGenerators:
    def test_new_session_id_prefix(self):
        sid = new_session_id()
        assert sid.startswith("sess_")

    def test_new_session_id_unique(self):
        ids = {new_session_id() for _ in range(100)}
        assert len(ids) == 100

    def test_new_utterance_id_prefix(self):
        uid = new_utterance_id()
        assert uid.startswith("utt_")

    def test_new_prosody_frame_id_prefix(self):
        assert new_prosody_frame_id().startswith("pf_")

    def test_new_receipt_id_prefix(self):
        assert new_receipt_id().startswith("rct_")

    def test_new_correlation_id_prefix(self):
        assert new_correlation_id().startswith("corr_")

    def test_all_ids_are_strings(self):
        for fn in (
            new_session_id, new_utterance_id, new_prosody_frame_id,
            new_receipt_id, new_correlation_id,
        ):
            assert isinstance(fn(), str)


# ── AppError ───────────────────────────────────────────────────────────────────

class TestAppError:
    def test_required_fields(self):
        err = AppError(code="test_err", message="Test error")
        assert err.code == "test_err"
        assert err.message == "Test error"
        assert err.http_status == 500
        assert err.retryable is False
        assert err.correlation_id is None

    def test_optional_fields(self):
        err = AppError(
            code="c", message="m", http_status=400,
            retryable=True, correlation_id="corr_1", details={"k": "v"},
        )
        assert err.http_status == 400
        assert err.retryable is True
        assert err.correlation_id == "corr_1"
        assert err.details == {"k": "v"}

    def test_is_exception(self):
        err = AppError(code="e", message="m")
        with pytest.raises(AppError):
            raise err

    def test_str_representation(self):
        err = AppError(code="e", message="my message")
        assert "my message" in str(err)


class TestToHttpException:
    def test_basic_conversion(self):
        err = AppError(code="not_found", message="Not found", http_status=404)
        http_exc = to_http_exception(err)
        assert http_exc.status_code == 404
        assert http_exc.detail["code"] == "not_found"
        assert http_exc.detail["message"] == "Not found"

    def test_correlation_id_in_detail(self):
        err = AppError(code="e", message="m", correlation_id="corr_x")
        http_exc = to_http_exception(err)
        assert http_exc.detail["correlation_id"] == "corr_x"


class TestToServerErrorPayload:
    def test_app_error_payload(self):
        err = AppError(code="bad", message="Bad thing", retryable=True)
        payload = to_server_error_payload(err)
        assert payload["code"] == "bad"
        assert payload["message"] == "Bad thing"
        assert payload["retryable"] is True

    def test_unexpected_exception_payload(self):
        payload = to_server_error_payload(ValueError("oops"))
        assert payload["code"] == "internal_error"
        assert payload["retryable"] is False

    def test_correlation_id_overrides(self):
        err = AppError(code="e", message="m", correlation_id="old")
        payload = to_server_error_payload(err, correlation_id="new_corr")
        assert payload["correlation_id"] == "new_corr"

    def test_correlation_id_passed_for_generic(self):
        payload = to_server_error_payload(RuntimeError("x"), correlation_id="corr_y")
        assert payload["correlation_id"] == "corr_y"


class TestWithCorrelationId:
    def test_attaches_id(self):
        err = AppError(code="e", message="m")
        result = with_correlation_id(err, "corr_abc")
        assert result.correlation_id == "corr_abc"

    def test_returns_same_error(self):
        err = AppError(code="e", message="m")
        result = with_correlation_id(err, "corr_xyz")
        assert result is err


# ── Logging ────────────────────────────────────────────────────────────────────

class TestLogging:
    def test_configure_logging_does_not_raise(self):
        configure_logging(level="DEBUG")
        configure_logging(level="INFO")
        configure_logging(level="invalid_level")  # falls back gracefully

    def test_get_logger_returns_logger(self):
        import logging
        logger = get_logger("test.module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"

    def test_log_ws_event_does_not_raise(self):
        log_ws_event(
            direction="in",
            session_id="sess_test",
            message_type="client.ping",
            correlation_id="corr_abc",
            extra={"key": "value"},
        )
