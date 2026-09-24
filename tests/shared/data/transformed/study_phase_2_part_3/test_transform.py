"""Tests for Part 3 keep/remove label transform."""

from __future__ import annotations

import pandas as pd
import pytest

from shared.data.transformed.study_phase_2_part_3.transform import (
    OUTPUT_COLUMNS,
    _aggregate_modal_labels_with_counts,
    _build_unanimous_flags,
    _join_stimuli_metadata,
    _load_slim_trial_frame,
    build_keep_remove_labels,
)


def _trial_row(
    post_id: str,
    decision: str,
    evaluation_mode: str = "linked_fate",
    original_text: str = "original",
    mirror_text: str = "mirror",
) -> dict[str, str]:
    return {
        "post_id": post_id,
        "decision": decision,
        "evaluation_mode": evaluation_mode,
        "original_text": original_text,
        "mirror_text": mirror_text,
    }


class TestLoadSlimTrialFrame:
    """Tests for _load_slim_trial_frame."""

    def test_load_slim_trial_frame_filters_linked_fate_keep_remove(self) -> None:
        """Keeps only linked-fate keep/remove rows with a real post id."""
        raw = pd.DataFrame(
            [
                _trial_row("reddit_a", "keep"),
                _trial_row("reddit_a", "REMOVE", "LINKED_FATE"),
                _trial_row("reddit_b", "skip"),
                _trial_row("reddit_c", "keep", "solo"),
                _trial_row("", "keep"),
                _trial_row("nan", "keep"),
            ]
        )

        result = _load_slim_trial_frame(raw)

        assert list(result["post_id"]) == ["reddit_a", "reddit_a"]
        assert set(result["decision"]) == {"keep", "remove"}


class TestAggregateModalLabelsWithCounts:
    """Tests for _aggregate_modal_labels_with_counts."""

    def test_modal_tie_becomes_remove(self) -> None:
        """A 2-2 vote is labeled remove."""
        trials = pd.DataFrame(
            [
                _trial_row("reddit_a", "keep"),
                _trial_row("reddit_a", "keep"),
                _trial_row("reddit_a", "remove"),
                _trial_row("reddit_a", "remove"),
            ]
        )

        result = _aggregate_modal_labels_with_counts(trials)

        assert result.loc[0, "decision"] == "remove"
        assert int(result.loc[0, "keep_remove_label"]) == 1

    def test_modal_keep_majority(self) -> None:
        """A 3-1 keep majority stores the keep rate and rater count."""
        trials = pd.DataFrame(
            [
                _trial_row("reddit_a", "keep"),
                _trial_row("reddit_a", "keep"),
                _trial_row("reddit_a", "keep"),
                _trial_row("reddit_a", "remove"),
            ]
        )

        result = _aggregate_modal_labels_with_counts(trials)
        row = result.iloc[0]

        assert row["decision"] == "keep"
        assert row["keep_rate"] == 0.75
        assert int(row["n_raters"]) == 4


class TestBuildUnanimousFlags:
    """Tests for _build_unanimous_flags."""

    def test_unanimous_true_when_all_raters_agree(self) -> None:
        """Four keep votes are unanimous."""
        trials = pd.DataFrame([_trial_row("reddit_a", "keep") for _ in range(4)])

        result = _build_unanimous_flags(trials)

        assert bool(result.loc[0, "is_unanimous"]) is True

    def test_unanimous_false_when_raters_split(self) -> None:
        """A split vote is not unanimous."""
        trials = pd.DataFrame(
            [
                _trial_row("reddit_a", "keep"),
                _trial_row("reddit_a", "keep"),
                _trial_row("reddit_a", "remove"),
                _trial_row("reddit_a", "remove"),
            ]
        )

        result = _build_unanimous_flags(trials)

        assert bool(result.loc[0, "is_unanimous"]) is False

    def test_unanimous_null_when_single_rater(self) -> None:
        """A single rater leaves is_unanimous null."""
        trials = pd.DataFrame([_trial_row("reddit_a", "keep")])

        result = _build_unanimous_flags(trials)

        assert pd.isna(result.loc[0, "is_unanimous"])


class TestJoinStimuliMetadata:
    """Tests for _join_stimuli_metadata."""

    def test_join_stimuli_adds_platform_and_mirror_text(self) -> None:
        """Stimulus mirrored_text becomes mirror_text and platform comes from the id."""
        modal = pd.DataFrame(
            [
                {
                    "post_id": "reddit_abc",
                    "decision": "keep",
                    "keep_remove_label": 0,
                    "n_raters": 2,
                    "keep_rate": 1.0,
                    "n_keep": 2,
                    "n_remove": 0,
                    "is_unanimous": True,
                }
            ]
        )
        stimuli = pd.DataFrame(
            [
                {
                    "post_primary_key": "reddit_abc",
                    "original_text": "orig",
                    "mirrored_text": "flipped",
                    "sampled_stance": "left",
                    "sample_toxicity_type": "low",
                }
            ]
        )

        result = _join_stimuli_metadata(modal, stimuli)

        assert result.loc[0, "mirror_text"] == "flipped"
        assert result.loc[0, "platform"] == "reddit"

    def test_build_raises_when_stimuli_missing_post(self) -> None:
        """A rated post with no stimulus row raises ValueError."""
        raw = pd.DataFrame(
            [
                _trial_row("reddit_missing", "keep"),
                _trial_row("reddit_missing", "keep"),
            ]
        )
        stimuli = pd.DataFrame(
            columns=[
                "post_primary_key",
                "original_text",
                "mirrored_text",
                "sampled_stance",
                "sample_toxicity_type",
            ]
        )

        with pytest.raises(ValueError):
            build_keep_remove_labels(raw, stimuli)


class TestBuildKeepRemoveLabels:
    """Tests for build_keep_remove_labels."""

    def test_output_columns_exact_order(self) -> None:
        """The end-to-end frame uses the registered column order."""
        raw = pd.DataFrame(
            [
                _trial_row("bluesky_1", "keep"),
                _trial_row("bluesky_1", "remove"),
                _trial_row("twitter_2", "remove"),
            ]
        )
        stimuli = pd.DataFrame(
            [
                {
                    "post_primary_key": "bluesky_1",
                    "original_text": "o1",
                    "mirrored_text": "m1",
                    "sampled_stance": "left",
                    "sample_toxicity_type": "middle",
                },
                {
                    "post_primary_key": "twitter_2",
                    "original_text": "o2",
                    "mirrored_text": "m2",
                    "sampled_stance": "right",
                    "sample_toxicity_type": "high",
                },
            ]
        )

        result = build_keep_remove_labels(raw, stimuli)

        assert list(result.columns) == OUTPUT_COLUMNS


@pytest.mark.integration
class TestLiveKeepRemoveLabels:
    """Tests for the materialized Part 3 label table."""

    def test_live_row_count_and_join_coverage(self) -> None:
        """The live table covers every rated post with text and platform."""
        result = build_keep_remove_labels()

        assert len(result) == 18866
        assert result["post_id"].notna().all()
        assert result["original_text"].notna().all()
        assert result["mirror_text"].notna().all()
        assert result["platform"].notna().all()
