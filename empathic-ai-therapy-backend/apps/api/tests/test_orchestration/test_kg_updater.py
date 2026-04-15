"""Tests for KG updater orchestration."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from orchestration.kg_updater import (
    apply_tool_calls_to_graph,
    build_graph_context_for_event,
    process_utterance_event,
)


class TestBuildGraphContextForEvent:
    def test_returns_dict(self):
        mock_context = {"top_concepts": [], "recent_edges": []}
        with patch("orchestration.kg_updater.repo_graph.get_graph_context_for_llm", return_value=mock_context):
            result = build_graph_context_for_event(
                session_id="sess_1", utterance_text="hello"
            )
        assert isinstance(result, dict)

    def test_returns_empty_on_error(self):
        with patch(
            "orchestration.kg_updater.repo_graph.get_graph_context_for_llm",
            side_effect=Exception("Neo4j down"),
        ):
            result = build_graph_context_for_event(
                session_id="sess_1", utterance_text="hello"
            )
        assert result == {"top_concepts": [], "recent_edges": []}

    def test_passes_session_id(self):
        mock_fn = MagicMock(return_value={"top_concepts": [], "recent_edges": []})
        with patch("orchestration.kg_updater.repo_graph.get_graph_context_for_llm", mock_fn):
            build_graph_context_for_event(session_id="sess_xyz", utterance_text="t")
        mock_fn.assert_called_once()
        assert mock_fn.call_args.kwargs["session_id"] == "sess_xyz"


class TestApplyToolCallsToGraph:
    def test_empty_tool_calls(self):
        utterance_record = {"utterance_id": "utt_1", "message_id": "msg_1"}
        result = apply_tool_calls_to_graph(
            session_id="sess_1",
            tool_calls=[],
            utterance_record=utterance_record,
        )
        assert result["nodes_upsert"] == []
        assert result["edges_upsert"] == []
        assert result["tool_call_results"] == []

    def test_upsert_concept_node(self):
        mock_node = {"id": "Emotion:sess:anxiety", "label": "Emotion", "canonical": "anxiety", "properties": {}}
        utterance_record = {"utterance_id": "utt_1", "message_id": "msg_1"}
        calls = [
            {
                "name": "upsert_concept_node",
                "arguments": {
                    "label": "Emotion",
                    "canonical": "anxiety",
                    "message_id": "msg_1",
                    "evidence_quote": "I feel anxious",
                },
            }
        ]
        with patch("orchestration.kg_updater.repo_graph.upsert_concept_node", return_value=mock_node):
            result = apply_tool_calls_to_graph(
                session_id="sess_1",
                tool_calls=calls,
                utterance_record=utterance_record,
            )
        assert len(result["nodes_upsert"]) == 1
        assert result["nodes_upsert"][0]["canonical"] == "anxiety"

    def test_upsert_relation_edge(self):
        mock_edge = {
            "id": "e1", "type": "EVOKES",
            "source": "Trigger:s:work", "target": "Emotion:s:stress",
            "properties": {},
        }
        utterance_record = {"utterance_id": "utt_1", "message_id": "msg_1"}
        calls = [
            {
                "name": "upsert_relation_edge",
                "arguments": {
                    "from_label": "Trigger",
                    "from_canonical": "work",
                    "rel_type": "EVOKES",
                    "to_label": "Emotion",
                    "to_canonical": "stress",
                    "message_id": "msg_1",
                    "evidence_quote": "work stresses me",
                },
            }
        ]
        with patch("orchestration.kg_updater.repo_graph.upsert_relation_edge", return_value=mock_edge):
            result = apply_tool_calls_to_graph(
                session_id="sess_1",
                tool_calls=calls,
                utterance_record=utterance_record,
            )
        assert len(result["edges_upsert"]) == 1

    def test_failed_tool_call_recorded(self):
        utterance_record = {"utterance_id": "utt_1", "message_id": "msg_1"}
        calls = [
            {
                "name": "upsert_concept_node",
                "arguments": {
                    "label": "Emotion",
                    "canonical": "x",
                    "message_id": "msg_1",
                    "evidence_quote": "e",
                },
            }
        ]
        with patch("orchestration.kg_updater.repo_graph.upsert_concept_node", side_effect=Exception("DB error")):
            result = apply_tool_calls_to_graph(
                session_id="sess_1",
                tool_calls=calls,
                utterance_record=utterance_record,
            )
        assert result["tool_call_results"][0]["status"] == "failed"
        assert len(result["nodes_upsert"]) == 0

    def test_set_session_goal(self):
        mock_node = {"id": "Goal:s:reduce stress", "label": "Goal", "canonical": "reduce stress", "properties": {}}
        utterance_record = {"utterance_id": "utt_1", "message_id": "msg_1"}
        calls = [
            {
                "name": "set_session_goal",
                "arguments": {
                    "canonical": "reduce stress",
                    "message_id": "msg_1",
                    "evidence_quote": "I want to reduce stress",
                },
            }
        ]
        with patch("orchestration.kg_updater.repo_graph.set_session_goal", return_value=mock_node):
            result = apply_tool_calls_to_graph(
                session_id="sess_1",
                tool_calls=calls,
                utterance_record=utterance_record,
            )
        assert len(result["nodes_upsert"]) == 1
        assert result["nodes_upsert"][0]["label"] == "Goal"


class TestProcessUtteranceEvent:
    @pytest.mark.asyncio
    async def test_skips_interim_messages(self):
        event = {
            "message_id": "m", "content": "partial text",
            "role": "user", "interim": True,
        }
        result = await process_utterance_event(session_id="sess_1", evi_user_message=event)
        assert "skipped" in result["warnings"][0]
        assert result["kg_diff"]["nodes_upsert"] == []

    @pytest.mark.asyncio
    async def test_processes_final_messages(self):
        event = {
            "message_id": "msg_1",
            "content": "I feel very anxious about my upcoming presentation",
            "role": "user",
            "interim": False,
            "prosody_scores": {"anxiety": 0.8},
        }
        mock_utterance = {
            "utterance_id": "utt_1",
            "session_id": "sess_1",
            "role": "user",
            "text": "I feel very anxious",
            "message_id": "msg_1",
        }
        mock_gemini_output = {
            "tool_calls": [
                {
                    "name": "upsert_concept_node",
                    "arguments": {
                        "label": "Emotion",
                        "canonical": "anxiety",
                        "message_id": "msg_1",
                        "evidence_quote": "anxious about my upcoming presentation",
                    },
                }
            ]
        }
        mock_node = {
            "id": "Emotion:sess_1:anxiety",
            "label": "Emotion",
            "canonical": "anxiety",
            "properties": {},
        }

        with patch("orchestration.kg_updater.repo_utterances.upsert_utterance", return_value=mock_utterance), \
             patch("orchestration.kg_updater.repo_utterances.insert_prosody_frame", return_value={}), \
             patch("orchestration.kg_updater.repo_graph.get_graph_context_for_llm", return_value={"top_concepts": [], "recent_edges": []}), \
             patch("orchestration.kg_updater.gemini_client_module.generate_kg_tool_calls", new_callable=AsyncMock, return_value=mock_gemini_output), \
             patch("orchestration.kg_updater.repo_graph.upsert_concept_node", return_value=mock_node):

            result = await process_utterance_event(
                session_id="sess_1", evi_user_message=event
            )

        assert "kg_diff" in result
        assert "tool_calls_applied" in result

    @pytest.mark.asyncio
    async def test_result_structure(self):
        event = {"message_id": "m", "content": "text", "role": "user", "interim": True}
        result = await process_utterance_event(session_id="s", evi_user_message=event)
        assert "kg_diff" in result
        assert "tool_calls_applied" in result
        assert "nodes_upsert" in result["kg_diff"]
        assert "edges_upsert" in result["kg_diff"]
        assert "receipts" in result["kg_diff"]
