"""Tests for Gemini KG tool declarations and validation."""
import pytest

from services.gemini.kg_tools import (
    get_allowed_concept_labels,
    get_allowed_relationship_types,
    tool_decls,
    validate_tool_call_shape,
)
from utils.errors import AppError


class TestGetAllowedConceptLabels:
    def test_returns_list(self):
        labels = get_allowed_concept_labels()
        assert isinstance(labels, list)

    def test_expected_labels_present(self):
        labels = get_allowed_concept_labels()
        expected = {"Person", "Trigger", "Emotion", "Belief", "Need", "Goal", "Action", "Event"}
        assert expected.issubset(set(labels))

    def test_no_duplicates(self):
        labels = get_allowed_concept_labels()
        assert len(labels) == len(set(labels))


class TestGetAllowedRelationshipTypes:
    def test_returns_list(self):
        rels = get_allowed_relationship_types()
        assert isinstance(rels, list)

    def test_expected_rels_present(self):
        rels = get_allowed_relationship_types()
        for r in ("EVOKES", "DRIVES", "LEADS_TO", "AFFECTS", "SUPPORTS", "CONFLICTS_WITH"):
            assert r in rels


class TestToolDecls:
    def test_returns_list(self):
        decls = tool_decls()
        assert isinstance(decls, list)
        assert len(decls) > 0

    def test_has_function_declarations(self):
        from vertexai.generative_models import Tool
        decls = tool_decls()
        assert isinstance(decls[0], Tool)

    def _tool_names(self):
        return {fd.name for tool in tool_decls() for fd in tool._raw_tool.function_declarations}

    def test_upsert_concept_node_present(self):
        assert "upsert_concept_node" in self._tool_names()

    def test_upsert_relation_edge_present(self):
        assert "upsert_relation_edge" in self._tool_names()

    def test_skip_kg_update_present(self):
        assert "skip_kg_update" in self._tool_names()

    def test_all_required_tools_present(self):
        required = {
            "upsert_concept_node", "upsert_relation_edge",
            "link_utterance_mentions", "set_session_goal", "skip_kg_update",
        }
        assert required.issubset(self._tool_names())

    def test_concept_node_has_required_fields(self):
        for tool in tool_decls():
            for fd in tool._raw_tool.function_declarations:
                if fd.name == "upsert_concept_node":
                    required = list(fd.parameters.required)
                    assert "label" in required
                    assert "canonical" in required
                    assert "message_id" in required
                    assert "evidence_quote" in required


class TestValidateToolCallShape:
    def test_valid_upsert_concept_node(self):
        call = {
            "name": "upsert_concept_node",
            "arguments": {
                "label": "Emotion",
                "canonical": "anxiety",
                "message_id": "msg_1",
                "evidence_quote": "I feel anxious",
            },
        }
        validate_tool_call_shape(call)  # should not raise

    def test_valid_skip_kg_update(self):
        call = {"name": "skip_kg_update", "arguments": {"reason": "No info"}}
        validate_tool_call_shape(call)  # should not raise

    def test_invalid_tool_name_raises(self):
        call = {"name": "drop_database", "arguments": {}}
        with pytest.raises(AppError) as exc_info:
            validate_tool_call_shape(call)
        assert exc_info.value.code == "invalid_tool_name"

    def test_missing_message_id_raises(self):
        call = {
            "name": "upsert_concept_node",
            "arguments": {
                "label": "Emotion",
                "canonical": "anxiety",
                "evidence_quote": "quote",
            },
        }
        with pytest.raises(AppError) as exc_info:
            validate_tool_call_shape(call)
        assert exc_info.value.code == "missing_message_id"

    def test_missing_evidence_quote_raises(self):
        call = {
            "name": "upsert_concept_node",
            "arguments": {
                "label": "Emotion",
                "canonical": "anxiety",
                "message_id": "msg_1",
            },
        }
        with pytest.raises(AppError) as exc_info:
            validate_tool_call_shape(call)
        assert exc_info.value.code == "missing_evidence_quote"

    def test_invalid_label_raises(self):
        call = {
            "name": "upsert_concept_node",
            "arguments": {
                "label": "Malware",
                "canonical": "virus",
                "message_id": "msg_1",
                "evidence_quote": "quote",
            },
        }
        with pytest.raises(AppError) as exc_info:
            validate_tool_call_shape(call)
        assert exc_info.value.code == "invalid_concept_label"

    def test_invalid_rel_type_raises(self):
        call = {
            "name": "upsert_relation_edge",
            "arguments": {
                "from_label": "Trigger",
                "from_canonical": "work",
                "rel_type": "HACKS",
                "to_label": "Emotion",
                "to_canonical": "stress",
                "message_id": "msg_1",
                "evidence_quote": "work stresses me",
            },
        }
        with pytest.raises(AppError) as exc_info:
            validate_tool_call_shape(call)
        assert exc_info.value.code == "invalid_relationship_type"

    def test_valid_relation_edge(self):
        call = {
            "name": "upsert_relation_edge",
            "arguments": {
                "from_label": "Trigger",
                "from_canonical": "work deadline",
                "rel_type": "EVOKES",
                "to_label": "Emotion",
                "to_canonical": "stress",
                "message_id": "msg_1",
                "evidence_quote": "deadline stresses me out",
            },
        }
        validate_tool_call_shape(call)  # should not raise
