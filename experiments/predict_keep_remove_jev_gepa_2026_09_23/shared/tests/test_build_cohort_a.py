"""Tests for aggregate_post_labels and build_cohort_a."""

from __future__ import annotations

import pandas as pd

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.cohort import (
    aggregate_post_labels,
    build_cohort_a,
    dedupe_participant_post,
    filter_scored_trials,
)


class TestAggregatePostLabels:
    """Tests for aggregate_post_labels."""

    def test_counts_and_unanimous_flags(self, mixed_trials: pd.DataFrame) -> None:
        """P1 and P2 are present with expected rater counts and unanimous flags."""
        trials = dedupe_participant_post(filter_scored_trials(mixed_trials))
        result = aggregate_post_labels(trials)
        p1 = result.loc[result["post_id"] == "P1"].iloc[0]
        p2 = result.loc[result["post_id"] == "P2"].iloc[0]
        assert int(p1["n_raters"]) == 4
        assert bool(p1["is_unanimous"]) is True
        assert int(p2["n_raters"]) == 4
        assert bool(p2["is_unanimous"]) is False


class TestBuildCohortA:
    """Tests for build_cohort_a."""

    def test_keeps_majority_posts_and_drops_ties_and_low_rater_posts(
        self,
        mixed_trials: pd.DataFrame,
    ) -> None:
        """P1 and P2 remain; P3 and P4 are excluded from cohort A."""
        trials = dedupe_participant_post(filter_scored_trials(mixed_trials))
        agg = aggregate_post_labels(trials)
        result = build_cohort_a(agg)
        post_ids = set(result["post_id"])
        assert post_ids == {"P1", "P2"}

    def test_label_and_remove_share_for_majority_keep_post(self) -> None:
        """Majority keep posts receive label 0 and the expected remove_share."""
        frame = pd.DataFrame(
            [
                {
                    "post_id": "P2",
                    "n_raters": 4,
                    "n_keep": 3,
                    "n_remove": 1,
                    "remove_share": 0.25,
                    "majority_decision": "keep",
                    "is_unanimous": False,
                    "original_text": "o",
                    "mirror_text": "m",
                    "sampled_stance": "left",
                    "sample_toxicity_type": "low",
                }
            ]
        )
        result = build_cohort_a(frame)
        row = result.iloc[0]
        assert int(row["label"]) == 0
        assert float(row["remove_share"]) == 0.25
