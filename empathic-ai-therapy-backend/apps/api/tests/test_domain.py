"""Tests for domain models and enums."""
import pytest

from domain.enums import ConceptLabel, GraphRelationshipType
from domain.models import (
    GraphSnapshot,
    KgDiff,
    KgEdge,
    KgNode,
    ProsodyFrameRecord,
    Receipt,
    SessionRecord,
    SessionSummary,
    TopConceptSummary,
    UtteranceRecord,
)


class TestConceptLabel:
    def test_all_expected_labels_present(self):
        values = {e.value for e in ConceptLabel}
        expected = {"Person", "Trigger", "Emotion", "Belief", "Need", "Goal", "Action", "Event"}
        assert values == expected

    def test_is_string_enum(self):
        assert isinstance(ConceptLabel.EMOTION, str)
        assert ConceptLabel.EMOTION == "Emotion"


class TestGraphRelationshipType:
    def test_all_expected_relationships_present(self):
        values = {e.value for e in GraphRelationshipType}
        assert "MENTIONS" in values
        assert "EVOKES" in values
        assert "DRIVES" in values
        assert "LEADS_TO" in values
        assert "AFFECTS" in values
        assert "SUPPORTS" in values
        assert "CONFLICTS_WITH" in values


class TestSessionRecord:
    def test_required_fields(self):
        rec = SessionRecord(session_id="sess_1", created_at_ms=1000)
        assert rec.session_id == "sess_1"
        assert rec.created_at_ms == 1000
        assert rec.ended_at_ms is None
        assert rec.status == "active"

    def test_ended_state(self):
        rec = SessionRecord(session_id="s", created_at_ms=1, ended_at_ms=2, status="ended")
        assert rec.ended_at_ms == 2
        assert rec.status == "ended"

    def test_model_dump(self):
        rec = SessionRecord(session_id="s", created_at_ms=1)
        d = rec.model_dump()
        assert "session_id" in d


class TestUtteranceRecord:
    def test_required_fields(self):
        rec = UtteranceRecord(
            utterance_id="utt_1",
            session_id="sess_1",
            role="user",
            text="Hello",
        )
        assert rec.utterance_id == "utt_1"
        assert rec.role == "user"
        assert rec.message_id is None
        assert rec.timestamp_ms is None

    def test_optional_fields(self):
        rec = UtteranceRecord(
            utterance_id="u", session_id="s", role="assistant",
            text="Hi", message_id="msg_1", timestamp_ms=9999,
        )
        assert rec.message_id == "msg_1"
        assert rec.timestamp_ms == 9999


class TestProsodyFrameRecord:
    def test_construction(self):
        rec = ProsodyFrameRecord(
            frame_id="pf_1",
            session_id="sess_1",
            message_id="msg_1",
            top_scores={"joy": 0.9, "sadness": 0.1},
            created_at_ms=12345,
        )
        assert rec.frame_id == "pf_1"
        assert rec.top_scores["joy"] == pytest.approx(0.9)


class TestKgNode:
    def test_construction(self):
        node = KgNode(id="Emotion:sess:anxiety", label="Emotion", canonical="anxiety")
        assert node.id == "Emotion:sess:anxiety"
        assert node.properties == {}

    def test_with_properties(self):
        node = KgNode(
            id="n1", label="Trigger", canonical="work",
            properties={"createdAt": 1000},
        )
        assert node.properties["createdAt"] == 1000


class TestKgEdge:
    def test_construction(self):
        edge = KgEdge(
            id="e1", type="EVOKES",
            source="Trigger:sess:work", target="Emotion:sess:anxiety",
        )
        assert edge.type == "EVOKES"
        assert edge.properties == {}


class TestReceipt:
    def test_construction(self):
        r = Receipt(
            receipt_id="rct_1",
            message_id="msg_1",
            tool_name="upsert_concept_node",
            evidence_quote="I feel anxious",
        )
        assert r.verified is True
        assert r.warnings == []
        assert r.applied_node_ids == []

    def test_with_warnings(self):
        r = Receipt(
            receipt_id="r", message_id="m",
            tool_name="t", evidence_quote="q",
            verified=False, warnings=["not found"],
        )
        assert r.verified is False
        assert "not found" in r.warnings


class TestKgDiff:
    def test_empty_defaults(self):
        diff = KgDiff()
        assert diff.nodes_upsert == []
        assert diff.edges_upsert == []
        assert diff.receipts == []

    def test_with_data(self):
        node = KgNode(id="n", label="Emotion", canonical="joy")
        diff = KgDiff(nodes_upsert=[node])
        assert len(diff.nodes_upsert) == 1


class TestGraphSnapshot:
    def test_empty(self):
        snap = GraphSnapshot()
        assert snap.nodes == []
        assert snap.edges == []


class TestSessionSummary:
    def test_construction(self):
        summary = SessionSummary(
            summary="Session done.",
            top_concepts=[
                TopConceptSummary(label="Emotion", canonical="anxiety", mention_count=3, score=3.0)
            ],
        )
        assert summary.summary == "Session done."
        assert len(summary.top_concepts) == 1
        assert summary.top_concepts[0].canonical == "anxiety"
