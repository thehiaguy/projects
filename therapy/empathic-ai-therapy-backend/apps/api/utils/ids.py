from uuid import uuid4


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def new_session_id() -> str:
    """
    Purpose:
        Generate a unique session identifier for `/v1/sessions` and websocket channel routing.

    Inputs:
        None.

    Returns:
        Opaque string ID (UUID/ULID/nanoid) safe for URLs and database keys.

    Data structures / implementation notes:
        - Prefer sortable IDs (e.g., ULID) if chronological debugging/querying matters
        - Keep format consistent across frontend/backend logs and receipts
    """
    return _new_id("session")


def new_utterance_id() -> str:
    """
    Purpose:
        Generate a stable internal utterance identifier independent of provider message IDs.

    Inputs:
        None.

    Returns:
        Opaque string ID used as `Utterance.utteranceId`.

    Data structures / implementation notes:
        - Separate from Hume `message_id` so backend can normalize multiple sources later
    """
    return _new_id("utterance")


def new_prosody_frame_id() -> str:
    """
    Purpose:
        Generate a unique ID for storing `ProsodyFrame` records linked to user messages.

    Inputs:
        None.

    Returns:
        Opaque string frame ID.
    """
    return _new_id("prosody")


def new_receipt_id() -> str:
    """
    Purpose:
        Generate a unique receipt identifier for mutation evidence tracking.

    Inputs:
        None.

    Returns:
        Opaque string receipt ID.
    """
    return _new_id("receipt")


def new_correlation_id() -> str:
    """
    Purpose:
        Generate a request/event correlation ID for tracing REST and websocket processing paths.

    Inputs:
        None.

    Returns:
        Opaque string correlation ID.

    Data structures / implementation notes:
        - Can be attached to logs, `server.error` packets, and route responses
    """
    return _new_id("corr")
