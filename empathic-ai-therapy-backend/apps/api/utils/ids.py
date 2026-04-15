import uuid


def _new_id(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex}"


def new_session_id() -> str:
    return _new_id("sess_")


def new_utterance_id() -> str:
    return _new_id("utt_")


def new_prosody_frame_id() -> str:
    return _new_id("pf_")


def new_receipt_id() -> str:
    return _new_id("rct_")


def new_correlation_id() -> str:
    return _new_id("corr_")
