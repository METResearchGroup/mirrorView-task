"""Tests for cohort builder helpers."""

from __future__ import annotations

import pandas as pd
import pytest

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.cohort import (
    assign_group,
    build_cohort_frame,
    dedupe_worker_post,
    drop_conflicting_worker_posts,
    filter_by_participant,
    modal_decision,
    slim_trials,
    three_group_label,
)
from shared.data.dataloader import load_dataset
from shared.data.registry import (
    STUDY_PHASE_2_PART_2_STIMULI,
    STUDY_PHASE_2_PART_3_STIMULI,
)


def _moderation_row(**overrides: object) -> dict[str, object]:
    base = {
        "phase": 1,
        "trial_type": "moderation-trial",
        "evaluation_mode": "linked_fate",
        "decision": "keep",
        "post_id": "post_a",
        "prolific_id": "worker_1",
        "time_elapsed": 10,
        "trial_index": 1,
        "attention_check_passed": 1,
    }
    base.update(overrides)
    return base


class TestSlimTrials:
    """Tests for slim_trials."""

    def test_slim_trials_filters_phase_one_moderation(self) -> None:
        """Only phase-one linked-fate moderation keep/remove trials remain."""
        frame = pd.DataFrame(
            [
                _moderation_row(),
                _moderation_row(phase=2, post_id="post_b"),
                _moderation_row(decision="maybe", post_id="post_c"),
                _moderation_row(evaluation_mode="solo", post_id="post_d"),
            ]
        )
        result = slim_trials(frame)
        assert len(result) == 1
        assert result.iloc[0]["post_id"] == "post_a"


class TestDropConflictingWorkerPosts:
    """Tests for drop_conflicting_worker_posts."""

    def test_drop_conflicting_worker_posts(self) -> None:
        """Workers with both keep and remove on one post are removed."""
        frame = pd.DataFrame(
            [
                _moderation_row(decision="keep"),
                _moderation_row(decision="remove"),
                _moderation_row(prolific_id="worker_2", post_id="post_b"),
            ]
        )
        result = drop_conflicting_worker_posts(frame)
        assert len(result) == 1
        assert result.iloc[0]["post_id"] == "post_b"


class TestDedupeWorkerPost:
    """Tests for dedupe_worker_post."""

    def test_dedupe_worker_post_keeps_earliest(self) -> None:
        """The earliest time_elapsed row is kept per worker and post."""
        frame = pd.DataFrame(
            [
                _moderation_row(time_elapsed=20, trial_index=2),
                _moderation_row(time_elapsed=5, trial_index=1),
            ]
        )
        result = dedupe_worker_post(frame)
        assert len(result) == 1
        assert int(result.iloc[0]["time_elapsed"]) == 5


class TestAssignGroup:
    """Tests for assign_group."""

    @pytest.mark.parametrize(
        "keep_count,remove_count",
        [(2, 2), (3, 2), (2, 3)],
    )
    def test_assign_group_split_patterns(
        self, keep_count: int, remove_count: int
    ) -> None:
        """Split vote patterns map to the split group label."""
        result = assign_group(keep_count, remove_count)
        assert result == constants.GROUP_SPLIT

    def test_assign_group_unanimous_requires_min_raters(self) -> None:
        """Four keeps map to unanimous_keep; three keeps return None."""
        assert assign_group(4, 0) == constants.GROUP_UNANIMOUS_KEEP
        assert assign_group(3, 0) is None


class TestModalDecision:
    """Tests for modal_decision."""

    def test_modal_decision_is_majority_vote(self) -> None:
        """Three keeps and one remove yield keep."""
        assert modal_decision(3, 1) == constants.DECISION_KEEP

    def test_modal_decision_tie_raises(self) -> None:
        """A tied vote raises ValueError."""
        with pytest.raises(ValueError):
            modal_decision(2, 2)


class TestThreeGroupLabel:
    """Tests for three_group_label."""

    def test_three_group_null_when_fewer_than_four_raters(self) -> None:
        """Three raters yield a null three-group label."""
        assert three_group_label(2, 1) is None


class TestInPart2Catalog:
    """Tests for in_part2_catalog membership."""

    def test_in_part2_catalog_uses_part2_stimuli(self) -> None:
        """Part 2 overlap is True only for shared post IDs."""
        part2_ids = set(load_dataset(STUDY_PHASE_2_PART_2_STIMULI)["post_primary_key"])
        part3 = load_dataset(STUDY_PHASE_2_PART_3_STIMULI)
        overlap_id = part3.loc[
            part3["post_primary_key"].isin(part2_ids), "post_primary_key"
        ].iloc[0]
        only_part3_id = part3.loc[
            ~part3["post_primary_key"].isin(part2_ids), "post_primary_key"
        ].iloc[0]
        cohort = build_cohort_frame("all")
        overlap_row = cohort.loc[cohort["post_id"] == overlap_id].iloc[0]
        only_row = cohort.loc[cohort["post_id"] == only_part3_id].iloc[0]
        assert bool(overlap_row["in_part2_catalog"]) is True
        assert bool(only_row["in_part2_catalog"]) is False


class TestAttentionPassFilter:
    """Tests for filter_by_participant."""

    def test_attention_pass_filter_excludes_failed_participants(self) -> None:
        """Failed attention-check participants are dropped."""
        frame = pd.DataFrame(
            [
                _moderation_row(prolific_id="pass_worker", attention_check_passed=1),
                _moderation_row(
                    prolific_id="fail_worker",
                    post_id="post_b",
                    attention_check_passed=0,
                ),
            ]
        )
        result = filter_by_participant(frame, "attention_pass")
        assert set(result["prolific_id"]) == {"pass_worker"}


@pytest.mark.integration
class TestBuildCohortIntegration:
    """Integration tests on real registry data."""

    def test_build_cohort_row_count(self) -> None:
        """The cohort has exactly 18,899 rows on real data."""
        cohort = build_cohort_frame("all")
        assert len(cohort) == constants.EXPECTED_POST_COUNT

    def test_label_count_distribution(self) -> None:
        """Label-count histogram matches the plan contract."""
        cohort = build_cohort_frame("all")
        labeled = cohort[cohort["n_raters"] > 0]
        assert len(labeled) == constants.EXPECTED_LABELED_COUNT
        counts = labeled["n_raters"].value_counts()
        assert int(counts.get(1, 0)) == constants.EXPECTED_LABEL_COUNT_ONE
        assert int(counts.get(2, 0)) == constants.EXPECTED_LABEL_COUNT_TWO
        three_plus = int((labeled["n_raters"] >= 3).sum())
        assert three_plus == constants.EXPECTED_LABEL_COUNT_THREE_PLUS

    def test_in_part2_catalog_count(self) -> None:
        """Exactly 8,899 rows overlap the Part 2 catalog."""
        cohort = build_cohort_frame("all")
        overlap_count = int(cohort["in_part2_catalog"].sum())
        assert overlap_count == constants.EXPECTED_PART2_OVERLAP
