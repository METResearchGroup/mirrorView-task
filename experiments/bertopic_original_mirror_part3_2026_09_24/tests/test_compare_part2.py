"""Tests for the Part 2 topic comparison."""

from __future__ import annotations

import numpy as np
import pandas as pd

from experiments.bertopic_original_mirror_part3_2026_09_24.src.compare_part2 import (
    assign_part2_topics,
    centroid_assign_part2_topic,
    compute_topic_agreement,
    find_carryover_post_ids,
)


class TestFindCarryoverPostIds:
    """Tests for find_carryover_post_ids."""

    def test_carryover_intersection_ids(self) -> None:
        """Carryover is the intersection of the two catalogs."""
        part2 = pd.DataFrame({"post_primary_key": ["a", "b", "c"]})
        part3 = pd.DataFrame({"post_id": ["b", "c", "d"]})

        result = find_carryover_post_ids(part2, part3)

        assert result == {"b", "c"}


class TestAssignPart2Topics:
    """Tests for assign_part2_topics."""

    def test_direct_join_marks_assigned_source(self) -> None:
        """A Part 2 assignment row is marked assigned."""
        carryover = {"b"}
        assignments = pd.DataFrame({"message_id": ["b"], "topic": [4]})

        result = assign_part2_topics(carryover, assignments)

        assert result.loc[0, "part2_topic_source"] == "assigned"
        assert int(result.loc[0, "part2_topic"]) == 4


class TestCentroidAssign:
    """Tests for centroid_assign_part2_topic."""

    def test_centroid_assign_picks_highest_cosine_topic(self) -> None:
        """The closer centroid wins."""
        post = np.array([1.0, 0.0])
        centroids = {0: np.array([0.0, 1.0]), 1: np.array([0.9, 0.1])}

        result = centroid_assign_part2_topic(post, centroids)

        assert result["part2_topic"] == 1
        assert result["part2_topic_source"] == "centroid"


class TestComputeTopicAgreement:
    """Tests for compute_topic_agreement."""

    def test_agreement_metrics_primary_subset_excludes_centroid(self) -> None:
        """Primary metrics ignore centroid-assigned rows."""
        paired = pd.DataFrame(
            {
                "part2_topic": [0, 1, 0],
                "part3_topic": [0, 1, 9],
                "part2_topic_source": ["assigned", "assigned", "centroid"],
            }
        )

        result = compute_topic_agreement(paired, primary_only=True)

        assert result["n_posts"] == 2
        assert result["ari"] == 1.0

    def test_agreement_metrics_perfect_match(self) -> None:
        """Identical topic sequences have ARI 1."""
        paired = pd.DataFrame(
            {
                "part2_topic": [0, 1, 0],
                "part3_topic": [0, 1, 0],
                "part2_topic_source": ["assigned", "assigned", "assigned"],
            }
        )

        result = compute_topic_agreement(paired, primary_only=False)

        assert result["ari"] == 1.0
        assert result["nmi"] == 1.0
