"""Tests for Hungarian topic matching."""

from __future__ import annotations

import numpy as np

from experiments.bertopic_original_mirror_part3_2026_09_24.src.analyze_cross_role import (
    ari_after_mapping,
    match_topics_hungarian,
)


class TestMatchTopicsHungarian:
    """Tests for match_topics_hungarian."""

    def test_maps_high_cosine_topic_pairs(self) -> None:
        """Each original topic maps to its highest-cosine mirror topic."""
        sim_matrix = np.array([[0.1, 0.9], [0.8, 0.2]])

        mapping = match_topics_hungarian(sim_matrix, orig_ids=[0, 1], mirror_ids=[0, 1])

        assert mapping[0] == 1
        assert mapping[1] == 0


class TestAriAfterMapping:
    """Tests for ari_after_mapping."""

    def test_ari_perfect_when_mapped_labels_match(self) -> None:
        """Remapped mirror labels that equal the original labels have ARI 1."""
        mapping = {10: 0, 11: 1}

        result = ari_after_mapping([0, 1, 0, 1], [10, 11, 10, 11], mapping)

        assert result == 1.0
