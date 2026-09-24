"""Tests for the Part 2 topic comparison."""

from __future__ import annotations

import numpy as np
import pandas as pd

from experiments.bertopic_original_mirror_part3_2026_09_24.src.compare_part2 import (
    PART2_RUN_ID,
    _outlier_rate,
    assign_part2_topics,
    catalog_overlap_post_ids,
    centroid_assign_part2_topic,
    compute_topic_agreement,
    part2_catalog_post_ids,
    part2_run_post_ids,
    part3_only_post_ids,
)


class TestPart2CatalogPostIds:
    """Tests for part2_catalog_post_ids."""

    def test_catalog_ids_from_stimuli(self) -> None:
        """Catalog ids come from post_primary_key."""
        part2 = pd.DataFrame({"post_primary_key": ["a", "b"]})

        result = part2_catalog_post_ids(part2)

        assert result == {"a", "b"}


class TestCatalogOverlapPostIds:
    """Tests for catalog_overlap_post_ids."""

    def test_overlap_intersection_ids(self) -> None:
        """Overlap is the intersection of the two catalogs."""
        part2 = pd.DataFrame({"post_primary_key": ["a", "b", "c"]})
        part3 = pd.DataFrame({"post_id": ["b", "c", "d"]})

        result = catalog_overlap_post_ids(part2, part3)

        assert result == {"b", "c"}


class TestPart3OnlyPostIds:
    """Tests for part3_only_post_ids."""

    def test_part3_only_excludes_part2_catalog(self) -> None:
        """Part-3-only ids are union posts outside the Part 2 catalog."""
        union = {"p2-a", "p3-only-1", "p3-only-2"}
        part2_catalog = {"p2-a", "p2-b"}

        result = part3_only_post_ids(union, part2_catalog)

        assert result == {"p3-only-1", "p3-only-2"}


class TestPart2RunPostIds:
    """Tests for part2_run_post_ids."""

    def test_run_ids_from_assignments(self) -> None:
        """Run ids come from message_id."""
        assignments = pd.DataFrame({"message_id": ["x", "y"], "topic": [0, 1]})

        result = part2_run_post_ids(assignments)

        assert result == {"x", "y"}


class TestAssignPart2Topics:
    """Tests for assign_part2_topics."""

    def test_direct_join_marks_assigned_source(self) -> None:
        """A Part 2 assignment row is marked assigned."""
        scope = {"b"}
        assignments = pd.DataFrame({"message_id": ["b"], "topic": [4]})

        result = assign_part2_topics(scope, assignments)

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


class TestOutlierRate:
    """Tests for _outlier_rate."""

    def test_outlier_rate_counts_noise_topic(self) -> None:
        """Noise topic -1 contributes to the rate."""
        topics = pd.Series([-1, 0, -1, 2])

        assert _outlier_rate(topics) == 0.5


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


class TestPart2RunIdConstant:
    """Tests for the committed Part 2 run id."""

    def test_part2_run_id_is_pinned(self) -> None:
        """Part 2 run id matches the committed modeling run."""
        assert PART2_RUN_ID == "20260805T135853Z"
