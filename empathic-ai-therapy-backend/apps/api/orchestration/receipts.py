import unicodedata
from typing import Any

from utils.ids import new_receipt_id


def validate_evidence_quote_present(*, utterance_text: str, evidence_quote: str) -> bool:
    def _normalize(s: str) -> str:
        s = unicodedata.normalize("NFC", s)
        return s.strip().lower()

    return _normalize(evidence_quote) in _normalize(utterance_text)


def build_receipt(
    *,
    session_id: str,
    message_id: str,
    tool_name: str,
    tool_arguments: dict[str, Any],
    applied_nodes: list[dict[str, Any]],
    applied_edges: list[dict[str, Any]],
    evidence_verified: bool,
) -> dict[str, Any]:
    receipt_id = new_receipt_id()
    warnings: list[str] = []

    if not evidence_verified:
        warnings.append("evidence_quote not found verbatim in utterance text")

    return {
        "receipt_id": receipt_id,
        "message_id": message_id,
        "tool_name": tool_name,
        "evidence_quote": tool_arguments.get("evidence_quote", ""),
        "applied_node_ids": [n["id"] for n in applied_nodes],
        "applied_edge_ids": [e["id"] for e in applied_edges],
        "verified": evidence_verified,
        "warnings": warnings,
    }


def attach_receipts(
    *,
    tool_call_results: list[dict[str, Any]],
    utterance_text: str,
) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for result in tool_call_results:
        args = result.get("tool_arguments", {})
        evidence_quote = args.get("evidence_quote", "")
        verified = validate_evidence_quote_present(
            utterance_text=utterance_text,
            evidence_quote=evidence_quote,
        )
        receipt = build_receipt(
            session_id=result.get("session_id", ""),
            message_id=result.get("message_id", ""),
            tool_name=result.get("tool_name", ""),
            tool_arguments=args,
            applied_nodes=result.get("applied_nodes", []),
            applied_edges=result.get("applied_edges", []),
            evidence_verified=verified,
        )
        receipts.append(receipt)
    return receipts
