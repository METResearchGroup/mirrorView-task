"""Tests for outcome helper functions."""

from __future__ import annotations

import pandas as pd

from experiments.bertopic_original_mirror_part3_2026_09_24.src.outcomes import (
    benjamini_hochberg_topic_tests,
    build_facet_outcome_table,
    cluster_bootstrap_keep_rate_by_topic,
    summarize_outcomes_by_topic,
)


class TestClusterBootstrapKeepRate:
    """Tests for cluster_bootstrap_keep_rate_by_topic."""

    def test_cluster_bootstrap_keep_rate_ci_bounds(self) -> None:
        """Topic 0 has point estimate 0.5 and a CI inside [0, 1]."""
        frame = pd.DataFrame(
            {
                "post_id": ["a", "b", "c", "d"],
                "topic": [0, 0, 1, 1],
                "keep_rate": [1.0, 0.0, 1.0, 0.0],
            }
        )

        first = cluster_bootstrap_keep_rate_by_topic(frame, n_bootstrap=500, seed=42)
        second = cluster_bootstrap_keep_rate_by_topic(frame, n_bootstrap=500, seed=42)
        topic0 = first.loc[first["topic"] == 0].iloc[0]

        assert topic0["keep_rate"] == 0.5
        assert 0.0 <= topic0["ci_low"] <= topic0["ci_high"] <= 1.0
        assert first.equals(second)


class TestBenjaminiHochbergTopicTests:
    """Tests for benjamini_hochberg_topic_tests."""

    def test_bh_fdr_flags_high_deviation(self) -> None:
        """Extreme topics are significant and the balanced topic is not."""
        result = benjamini_hochberg_topic_tests(
            successes=[40, 5, 20],
            trials=[40, 40, 40],
            corpus_keep_rate=0.5,
            topics=[0, 1, 2],
        )

        assert float(result.loc[result.topic == 0, "q_value"].iloc[0]) < 0.05
        assert float(result.loc[result.topic == 1, "q_value"].iloc[0]) < 0.05
        assert float(result.loc[result.topic == 2, "q_value"].iloc[0]) >= 0.05


class TestFacetCells:
    """Tests for build_facet_outcome_table."""

    def test_facet_cell_suppressed_below_30(self) -> None:
        """A topic-facet cell with 29 posts is omitted."""
        frame = pd.DataFrame(
            {
                "post_id": [f"p{index}" for index in range(29)],
                "topic": [3] * 29,
                "sampled_stance": ["left"] * 29,
                "keep_rate": [1.0] * 29,
            }
        )

        result = build_facet_outcome_table(frame, "sampled_stance", facet_min_posts=30)

        assert result.empty


class TestSummarizeOutcomes:
    """Tests for summarize_outcomes_by_topic."""

    def test_noise_topic_included(self) -> None:
        """Topic -1 stays in the summary."""
        frame = pd.DataFrame(
            {
                "post_id": ["a", "b", "c"],
                "topic": [-1, -1, 2],
                "keep_rate": [1.0, 0.0, 1.0],
            }
        )

        result = summarize_outcomes_by_topic(frame)

        assert -1 in set(result["topic"])
