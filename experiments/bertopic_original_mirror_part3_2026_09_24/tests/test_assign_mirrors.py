"""Tests for mirror assignment rows."""

from __future__ import annotations

from experiments.bertopic_original_mirror_part3_2026_09_24.src.assign_mirrors import (
    assign_mirror_topics,
    make_pair_row,
)


class TestMakePairRow:
    """Tests for make_pair_row."""

    def test_topics_agree_true_when_same_topic_id(self) -> None:
        """Matching topic ids set topics_agree."""
        row = make_pair_row("p1", 3, 3, 0.8, 0.7)

        assert row["topics_agree"] is True
        assert row["pair_post_id"] == "p1"


class _FakeModel:
    """Stand-in that records transform calls."""

    def __init__(self) -> None:
        self.calls: list[tuple[list[str], object]] = []

    def transform(self, docs, embeddings):
        self.calls.append((docs, embeddings))
        return [1, 2], [0.4, 0.6]


class TestAssignMirrorTopics:
    """Tests for assign_mirror_topics."""

    def test_transform_called_with_mirror_embeddings_only(self) -> None:
        """Assignment uses transform on the mirror matrix and does not fit."""
        model = _FakeModel()
        embeddings = [[0.1, 0.2], [0.3, 0.4]]

        topics, probabilities = assign_mirror_topics(model, ["flip-a", "flip-b"], embeddings)

        assert topics == [1, 2]
        assert probabilities == [0.4, 0.6]
        assert model.calls[0][0] == ["flip-a", "flip-b"]
        assert model.calls[0][1] is embeddings
        assert not hasattr(model, "fit_transform") or "fit_transform" not in model.calls
