"""Tests for union post-level stance and toxicity exclusion."""

from __future__ import annotations

import pandas as pd

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.cohort import (
    STUDY_PART_PART2,
    STUDY_PART_PART3,
    aggregate_post_labels,
    apply_union_strata_exclusion,
    attach_study_part,
    build_cohort_a,
    dedupe_participant_post,
    filter_scored_trials,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.tests.conftest import trial_row


class TestApplyUnionStrataExclusion:
    """Tests for apply_union_strata_exclusion."""

    def test_excludes_posts_with_no_non_empty_stance_or_toxicity(self) -> None:
        """Posts missing both stance and toxicity values are dropped."""
        rows = [
            trial_row(
                post_id="P1",
                prolific_id="W1",
                sampled_stance="",
                sample_toxicity_type="",
                decision="keep",
            ),
            trial_row(
                post_id="P1",
                prolific_id="W2",
                sampled_stance="",
                sample_toxicity_type="",
                decision="keep",
            ),
            trial_row(
                post_id="P1",
                prolific_id="W3",
                sampled_stance="",
                sample_toxicity_type="",
                decision="remove",
            ),
            trial_row(
                post_id="P2",
                prolific_id="W1",
                sampled_stance="left",
                sample_toxicity_type="low",
                decision="keep",
            ),
            trial_row(
                post_id="P2",
                prolific_id="W2",
                sampled_stance="left",
                sample_toxicity_type="low",
                decision="keep",
            ),
            trial_row(
                post_id="P2",
                prolific_id="W3",
                sampled_stance="left",
                sample_toxicity_type="low",
                decision="remove",
            ),
        ]
        trials = attach_study_part(dedupe_participant_post(filter_scored_trials(pd.DataFrame(rows))))
        agg = aggregate_post_labels(trials)
        cohort = build_cohort_a(agg)
        kept, report = apply_union_strata_exclusion(cohort, trials)
        assert set(kept["post_id"]) == {"P2"}
        assert report.n_excluded == 1
        assert report.excluded_keep == 1

    def test_uses_part3_value_when_stance_disagrees(self) -> None:
        """Conflicting stance values resolve to the Part 3 rating."""
        rows = [
            trial_row(
                post_id="P1",
                prolific_id="W1",
                sampled_stance="left",
                sample_toxicity_type="low",
                decision="keep",
            ),
            trial_row(
                post_id="P1",
                prolific_id="W2",
                sampled_stance="right",
                sample_toxicity_type="low",
                decision="keep",
            ),
            trial_row(
                post_id="P1",
                prolific_id="W3",
                sampled_stance="center",
                sample_toxicity_type="low",
                decision="remove",
            ),
        ]
        frame = pd.DataFrame(rows)
        frame.loc[frame["prolific_id"] == "W1", "attention_check_passed"] = ""
        frame.loc[frame["prolific_id"].isin(["W2", "W3"]), "attention_check_passed"] = "True"
        trials = attach_study_part(dedupe_participant_post(filter_scored_trials(frame)))
        agg = aggregate_post_labels(trials)
        cohort = build_cohort_a(agg)
        kept, report = apply_union_strata_exclusion(cohort, trials)
        row = kept.loc[kept["post_id"] == "P1"].iloc[0]
        assert row["sampled_stance"] == "right"
        assert report.n_stance_disagreements == 1
        assert int(row["n_raters_part2"]) == 1
        assert int(row["n_raters_part3"]) == 2
