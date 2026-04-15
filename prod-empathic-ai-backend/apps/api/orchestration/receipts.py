from typing import Any

from domain.models import Receipt
from utils.ids import new_receipt_id


def validate_evidence_quote_present(*, utterance_text: str, evidence_quote: str) -> bool:
    normalized_utterance = " ".join(utterance_text.strip().split())
    normalized_quote = " ".join(evidence_quote.strip().split())
    if not normalized_quote:
        return False
    return normalized_quote in normalized_utterance


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
    evidence_quote = str(tool_arguments.get("evidence_quote") or "")
    warnings: list[str] = []
    if not evidence_verified:
        warnings.append("evidence_quote_not_verified")

    receipt = Receipt(
        receipt_id=new_receipt_id(),
        message_id=message_id,
        tool_name=tool_name,
        evidence_quote=evidence_quote or "[none]",
        applied_node_ids=[str(node.get("id")) for node in applied_nodes if node.get("id")],
        applied_edge_ids=[str(edge.get("id")) for edge in applied_edges if edge.get("id")],
        verified=evidence_verified,
        warnings=warnings,
    )
    return receipt.model_dump()


def attach_receipts(
    *,
    tool_call_results: list[dict[str, Any]],
    utterance_text: str,
) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for result in tool_call_results:
        if result.get("status") != "applied":
            continue
        arguments = result.get("arguments", {})
        evidence_quote = str(arguments.get("evidence_quote") or "")
        receipts.append(
            build_receipt(
                session_id=str(result.get("session_id") or ""),
                message_id=str(result.get("message_id") or arguments.get("message_id") or ""),
                tool_name=str(result.get("name") or ""),
                tool_arguments=arguments,
                applied_nodes=result.get("applied_nodes", []),
                applied_edges=result.get("applied_edges", []),
                evidence_verified=validate_evidence_quote_present(
                    utterance_text=utterance_text,
                    evidence_quote=evidence_quote,
                ),
            )
        )
    return receipts
