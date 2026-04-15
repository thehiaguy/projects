from typing import Any

from domain.models import Receipt
from utils.ids import new_receipt_id


def validate_evidence_quote_present(*, utterance_text: str, evidence_quote: str) -> bool:
    """
    Purpose:
        Verify that a Gemini-provided evidence quote appears in the source utterance text before applying/marking a receipt.

    Inputs:
        - `utterance_text`: finalized transcript text used as evidence source
        - `evidence_quote`: model-provided quote substring

    Returns:
        `True` if evidence is present/acceptable; `False` otherwise.

    Data structures / implementation notes:
        - Define normalization rules (trim, unicode normalization, punctuation handling)
        - Use strict matching by default to minimize hallucinated updates
    """
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
    """
    Purpose:
        Create a receipt object explaining a graph mutation and its evidence for UI transparency.

    Inputs:
        - `session_id`: session scope
        - `message_id`: source EVI message id
        - `tool_name`: executed Gemini tool name
        - `tool_arguments`: normalized tool args (includes `evidence_quote`)
        - `applied_nodes`: node payloads created/updated by this tool call
        - `applied_edges`: edge payloads created/updated by this tool call
        - `evidence_verified`: result from evidence validation helper

    Returns:
        Receipt dict matching planned `Receipt` model shape.

    Data structures / implementation notes:
        - Generate `receipt_id` via `utils.ids`
        - Include warning markers when evidence is missing/unverified
    """
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
    """
    Purpose:
        Convert a batch of executed tool call results into frontend-ready receipt records.

    Inputs:
        - `tool_call_results`: per-tool execution outputs (tool args + applied nodes/edges + status)
        - `utterance_text`: source text for evidence validation

    Returns:
        List of receipt dicts in execution order.

    Data structures / implementation notes:
        - Each result entry should include `message_id` and `evidence_quote`
        - Receipts should remain serializable and UI-safe
    """
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
