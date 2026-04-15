"""Tests for Gemini prompt builders."""
import pytest

from services.gemini.prompts import (
    build_kg_system_prompt,
    build_kg_user_prompt,
    summarize_prosody_for_prompt,
)


class TestBuildKgSystemPrompt:
    def test_returns_string(self):
        prompt = build_kg_system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_contains_allowed_labels(self):
        prompt = build_kg_system_prompt()
        for label in ("Person", "Trigger", "Emotion", "Belief", "Need", "Goal"):
            assert label in prompt

    def test_contains_evidence_requirement(self):
        prompt = build_kg_system_prompt()
        assert "evidence_quote" in prompt
        assert "message_id" in prompt

    def test_mentions_per_utterance_limits(self):
        prompt = build_kg_system_prompt()
        assert "4" in prompt  # node limit
        assert "6" in prompt  # edge limit


class TestBuildKgUserPrompt:
    def test_includes_utterance_text(self):
        prompt = build_kg_user_prompt(
            session_id="sess_1",
            utterance_text="I feel anxious at work",
            message_id="msg_1",
            prosody_scores=None,
            graph_context={},
        )
        assert "I feel anxious at work" in prompt

    def test_includes_message_id(self):
        prompt = build_kg_user_prompt(
            session_id="sess_1",
            utterance_text="text",
            message_id="msg_abc",
            prosody_scores=None,
            graph_context={},
        )
        assert "msg_abc" in prompt

    def test_includes_session_id(self):
        prompt = build_kg_user_prompt(
            session_id="sess_xyz",
            utterance_text="text",
            message_id="msg_1",
            prosody_scores=None,
            graph_context={},
        )
        assert "sess_xyz" in prompt

    def test_includes_prosody_summary(self):
        prompt = build_kg_user_prompt(
            session_id="s",
            utterance_text="t",
            message_id="m",
            prosody_scores={"joy": 0.8, "sadness": 0.2},
            graph_context={},
        )
        assert "joy" in prompt

    def test_no_prosody_sentinel(self):
        prompt = build_kg_user_prompt(
            session_id="s",
            utterance_text="t",
            message_id="m",
            prosody_scores=None,
            graph_context={},
        )
        assert "none available" in prompt

    def test_includes_graph_context(self):
        context = {
            "top_concepts": [{"label": "Emotion", "canonical": "anxiety"}],
            "recent_edges": [{"from": "Trigger:work", "rel": "EVOKES", "to": "Emotion:anxiety"}],
        }
        prompt = build_kg_user_prompt(
            session_id="s",
            utterance_text="t",
            message_id="m",
            prosody_scores=None,
            graph_context=context,
        )
        assert "anxiety" in prompt
        assert "EVOKES" in prompt

    def test_empty_graph_context(self):
        prompt = build_kg_user_prompt(
            session_id="s",
            utterance_text="t",
            message_id="m",
            prosody_scores=None,
            graph_context={"top_concepts": [], "recent_edges": []},
        )
        assert "(none yet)" in prompt


class TestSummarizeProsodyForPrompt:
    def test_none_input(self):
        result = summarize_prosody_for_prompt(None)
        assert result == "none available"

    def test_empty_dict(self):
        result = summarize_prosody_for_prompt({})
        assert result == "none available"

    def test_top_k_selection(self):
        scores = {"joy": 0.9, "sadness": 0.6, "anger": 0.3, "fear": 0.2, "disgust": 0.1, "surprise": 0.05}
        result = summarize_prosody_for_prompt(scores, top_k=3)
        # Only top 3 should appear
        assert "joy" in result
        assert "sadness" in result
        assert "anger" in result
        assert "disgust" not in result
        assert "surprise" not in result

    def test_scores_are_rounded(self):
        result = summarize_prosody_for_prompt({"joy": 0.123456})
        assert "0.12" in result

    def test_ordered_by_score_desc(self):
        scores = {"a": 0.1, "b": 0.9, "c": 0.5}
        result = summarize_prosody_for_prompt(scores, top_k=3)
        # b should come first
        assert result.index("b") < result.index("a")

    def test_single_score(self):
        result = summarize_prosody_for_prompt({"calm": 0.75})
        assert "calm=0.75" in result
