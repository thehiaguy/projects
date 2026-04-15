import ulid


def _new_id(prefix: str | None = None) -> str:
    value = ulid.new().str # 26-char Crockford Base32, sortable
    return f"{prefix}_{value}" if prefix else value


def new_session_id() -> str:
    return _new_id("sess")


def new_utterance_id() -> str:
    return _new_id("utt")


def new_prosody_frame_id() -> str:
    return _new_id("pf")


def new_receipt_id() -> str:
    return _new_id("rcpt")


def new_correlation_id() -> str:
    return _new_id("corr")