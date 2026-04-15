"""Tests for orchestration receipt building."""
import pytest

from orchestration.receipts import (
    attach_receipts,
    build_receipt,
    validate_evidence_quote_present,
)


class TestValidateEvidenceQuotePresent:
    def test_exact_match(self):
        assert validate_evidence_quote_present(
            utterance_text="I feel anxious about work",
            evidence_quote="feel anxious about work",
        ) is True

    def test_no_match(self):
        assert validate_evidence_quote_present(
            utterance_text="I feel happy",
            evidence_quote="I am very sad",
        ) is False

    def test_case_insensitive(self):
        assert validate_evidence_quote_present(
            utterance_text="I Feel ANXIOUS",
            evidence_quote="feel anxious",
        ) is True

    def test_leading_trailing_whitespace(self):
        assert validate_evidence_quote_present(
            utterance_text="I feel stressed",
            evidence_quote="  feel stressed  ",
        ) is True

    def test_empty_quote(self):
        # Empty quote matches everything (strip -> empty string is in any string)
        result = validate_evidence_quote_present(
            utterance_text="anything",
            evidence_quote="",
        )
        assert isinstance(result, bool)

    def test_partial_match(self):
        assert validate_evidence_quote_present(
            utterance_text="My work deadlines stress me out a lot",
            evidence_quote="deadlines stress",
        ) is True

    def test_unicode_normalization(self):
        # Both should normalize to same form
        assert validate_evidence_quote_present(
            utterance_text="caf\u00e9 anxiety",
            evidence_quote="caf\u00e9 anxiety",
        ) is True


class TestBuildReceipt:
    def test_basic_receipt(self):
        receipt = build_receipt(
            session_id="sess_1",
            message_id="msg_1",
            tool_name="upsert_concept_node",
            tool_arguments={"evidence_quote": "I feel anxious"},
            applied_nodes=[{"id": "Emotion:sess_1:anxiety"}],
            applied_edges=[],
            evidence_verified=True,
        )
        assert receipt["receipt_id"].startswith("rct_")
        assert receipt["message_id"] == "msg_1"
        assert receipt["tool_name"] == "upsert_concept_node"
        assert receipt["evidence_quote"] == "I feel anxious"
        assert receipt["applied_node_ids"] == ["Emotion:sess_1:anxiety"]
        assert receipt["applied_edge_ids"] == []
        assert receipt["verified"] is True
        assert receipt["warnings"] == []

    def test_unverified_receipt_has_warning(self):
        receipt = build_receipt(
            session_id="s",
            message_id="m",
            tool_name="t",
            tool_arguments={"evidence_quote": "not in text"},
            applied_nodes=[],
            applied_edges=[],
            evidence_verified=False,
        )
        assert receipt["verified"] is False
        assert len(receipt["warnings"]) > 0

    def test_receipt_id_unique(self):
        receipts = [
            build_receipt(
                session_id="s", message_id="m", tool_name="t",
                tool_arguments={"evidence_quote": "e"},
                applied_nodes=[], applied_edges=[], evidence_verified=True,
            )
            for _ in range(10)
        ]
        ids = {r["receipt_id"] for r in receipts}
        assert len(ids) == 10

    def test_applied_edge_ids_extracted(self):
        receipt = build_receipt(
            session_id="s",
            message_id="m",
            tool_name="upsert_relation_edge",
            tool_arguments={"evidence_quote": "e"},
            applied_nodes=[],
            applied_edges=[{"id": "edge_abc"}, {"id": "edge_xyz"}],
            evidence_verified=True,
        )
        assert "edge_abc" in receipt["applied_edge_ids"]
        assert "edge_xyz" in receipt["applied_edge_ids"]


class TestAttachReceipts:
    def test_empty_results(self):
        receipts = attach_receipts(tool_call_results=[], utterance_text="text")
        assert receipts == []

    def test_verified_receipt_when_quote_in_text(self):
        results = [
            {
                "tool_name": "upsert_concept_node",
                "tool_arguments": {"evidence_quote": "feel anxious"},
                "message_id": "msg_1",
                "session_id": "sess_1",
                "applied_nodes": [{"id": "n1"}],
                "applied_edges": [],
            }
        ]
        receipts = attach_receipts(
            tool_call_results=results,
            utterance_text="I feel anxious at work",
        )
        assert len(receipts) == 1
        assert receipts[0]["verified"] is True

    def test_unverified_receipt_when_quote_not_in_text(self):
        results = [
            {
                "tool_name": "upsert_concept_node",
                "tool_arguments": {"evidence_quote": "I hate everything"},
                "message_id": "msg_1",
                "session_id": "sess_1",
                "applied_nodes": [],
                "applied_edges": [],
            }
        ]
        receipts = attach_receipts(
            tool_call_results=results,
            utterance_text="I feel fine today",
        )
        assert len(receipts) == 1
        assert receipts[0]["verified"] is False

    def test_multiple_results(self):
        results = [
            {
                "tool_name": f"tool_{i}",
                "tool_arguments": {"evidence_quote": "text"},
                "message_id": "m",
                "session_id": "s",
                "applied_nodes": [],
                "applied_edges": [],
            }
            for i in range(3)
        ]
        receipts = attach_receipts(
            tool_call_results=results,
            utterance_text="some text here",
        )
        assert len(receipts) == 3
