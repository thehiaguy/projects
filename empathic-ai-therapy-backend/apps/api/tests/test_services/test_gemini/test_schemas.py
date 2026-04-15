"""Tests for Gemini schema models and normalization."""
import pytest

from services.gemini.schemas import (
    LinkUtteranceMentionsArgs,
    MentionItem,
    SetSessionGoalArgs,
    SkipKgUpdateArgs,
    UpsertConceptNodeArgs,
    UpsertRelationEdgeArgs,
    normalize_tool_calls,
    validate_tool_call_batch_limits,
)
from utils.errors import AppError


class TestUpsertConceptNodeArgs:
    def test_valid(self):
        args = UpsertConceptNodeArgs(
            label="Emotion",
            canonical="anxiety",
            message_id="msg_1",
            evidence_quote="I feel anxious",
        )
        assert args.canonical == "anxiety"

    def test_invalid_label_raises(self):
        with pytest.raises(Exception):
            UpsertConceptNodeArgs(
                label="NotAllowed",
                canonical="x",
                message_id="m",
                evidence_quote="e",
            )

    def test_optional_fields(self):
        args = UpsertConceptNodeArgs(
            label="Goal",
            canonical="reduce stress",
            message_id="m",
            evidence_quote="e",
            confidence=0.9,
            aliases=["less stress"],
        )
        assert args.confidence == pytest.approx(0.9)
        assert "less stress" in args.aliases


class TestUpsertRelationEdgeArgs:
    def test_valid(self):
        args = UpsertRelationEdgeArgs(
            from_label="Trigger",
            from_canonical="work",
            rel_type="EVOKES",
            to_label="Emotion",
            to_canonical="stress",
            message_id="msg_1",
            evidence_quote="work stresses me",
        )
        assert args.rel_type == "EVOKES"

    def test_invalid_from_label_raises(self):
        with pytest.raises(Exception):
            UpsertRelationEdgeArgs(
                from_label="INVALID",
                from_canonical="x",
                rel_type="EVOKES",
                to_label="Emotion",
                to_canonical="y",
                message_id="m",
                evidence_quote="e",
            )

    def test_invalid_rel_type_raises(self):
        with pytest.raises(Exception):
            UpsertRelationEdgeArgs(
                from_label="Trigger",
                from_canonical="x",
                rel_type="INVALID_REL",
                to_label="Emotion",
                to_canonical="y",
                message_id="m",
                evidence_quote="e",
            )


class TestLinkUtteranceMentionsArgs:
    def test_valid(self):
        args = LinkUtteranceMentionsArgs(
            message_id="msg_1",
            mentions=[MentionItem(label="Emotion", canonical="joy")],
            evidence_quote="I feel joy",
        )
        assert len(args.mentions) == 1

    def test_empty_mentions(self):
        args = LinkUtteranceMentionsArgs(
            message_id="m", mentions=[], evidence_quote="e"
        )
        assert args.mentions == []


class TestSetSessionGoalArgs:
    def test_valid(self):
        args = SetSessionGoalArgs(
            canonical="reduce work anxiety",
            message_id="msg_1",
            evidence_quote="I want to feel less anxious about work",
        )
        assert args.canonical == "reduce work anxiety"


class TestNormalizeToolCalls:
    def test_empty_input(self):
        result = normalize_tool_calls({"tool_calls": []})
        assert result == []

    def test_single_call(self):
        raw = {
            "tool_calls": [
                {"name": "upsert_concept_node", "arguments": {"label": "Emotion"}}
            ]
        }
        result = normalize_tool_calls(raw)
        assert len(result) == 1
        assert result[0]["name"] == "upsert_concept_node"
        assert result[0]["arguments"]["label"] == "Emotion"
        assert result[0]["provider_index"] == 0

    def test_multiple_calls_preserve_order(self):
        raw = {
            "tool_calls": [
                {"name": "a", "arguments": {}},
                {"name": "b", "arguments": {}},
                {"name": "c", "arguments": {}},
            ]
        }
        result = normalize_tool_calls(raw)
        assert [r["name"] for r in result] == ["a", "b", "c"]
        assert [r["provider_index"] for r in result] == [0, 1, 2]

    def test_missing_tool_calls_key(self):
        result = normalize_tool_calls({})
        assert result == []


class TestValidateToolCallBatchLimits:
    def test_within_limits(self):
        calls = [
            {"name": "upsert_concept_node"} for _ in range(4)
        ] + [
            {"name": "upsert_relation_edge"} for _ in range(6)
        ]
        validate_tool_call_batch_limits(tool_calls=calls)  # should not raise

    def test_exceeds_node_limit(self):
        calls = [{"name": "upsert_concept_node"} for _ in range(5)]
        with pytest.raises(AppError) as exc_info:
            validate_tool_call_batch_limits(tool_calls=calls, max_nodes_per_utterance=4)
        assert exc_info.value.code == "batch_limit_exceeded"

    def test_exceeds_edge_limit(self):
        calls = [{"name": "upsert_relation_edge"} for _ in range(7)]
        with pytest.raises(AppError) as exc_info:
            validate_tool_call_batch_limits(tool_calls=calls, max_edges_per_utterance=6)
        assert exc_info.value.code == "batch_limit_exceeded"

    def test_other_tools_not_counted(self):
        calls = [
            {"name": "set_session_goal"},
            {"name": "link_utterance_mentions"},
            {"name": "skip_kg_update"},
        ]
        validate_tool_call_batch_limits(tool_calls=calls)  # should not raise

    def test_custom_limits(self):
        calls = [{"name": "upsert_concept_node"} for _ in range(2)]
        with pytest.raises(AppError):
            validate_tool_call_batch_limits(
                tool_calls=calls, max_nodes_per_utterance=1
            )

    def test_empty_list(self):
        validate_tool_call_batch_limits(tool_calls=[])  # should not raise
