"""Tests for vote cleaning and per-post aggregation."""

from __future__ import annotations

import pandas as pd
import pytest

from experiments.phase_2_part_3_keep_remove_descriptive_stats_2026_09_24.votes import (
    aggregate_votes_per_post,
    build_per_post_votes,
    dedupe_worker_votes,
    filter_linked_fate_trials,
)


def _trial_row(
    *,
    evaluation_mode: str = "linked_fate",
    decision: str,
    post_id: str,
    prolific_id: str = "worker_a",
    trial_index: int = 0,
    time_elapsed: float = 1.0,
    original_text: str = "orig",
    mirror_text: str = "mirror",
) -> dict[str, object]:
    return {
        "evaluation_mode": evaluation_mode,
        "decision": decision,
        "post_id": post_id,
        "prolific_id": prolific_id,
        "trial_index": trial_index,
        "time_elapsed": time_elapsed,
        "original_text": original_text,
        "mirror_text": mirror_text,
    }


class TestFilterLinkedFateTrials:
    """Tests for filter_linked_fate_trials()."""

    def test_keeps_linked_fate_keep_and_remove_only(self):
        """Keep only linked-fate keep/remove rows with usable post ids."""
        raw = pd.DataFrame(
            [
                _trial_row(
                    evaluation_mode="linked_fate",
                    decision="keep",
                    post_id="post_a",
                ),
                _trial_row(
                    evaluation_mode="linked_fate",
                    decision="remove",
                    post_id="post_b",
                ),
                _trial_row(
                    evaluation_mode="practice",
                    decision="keep",
                    post_id="post_c",
                ),
                _trial_row(
                    evaluation_mode="linked_fate",
                    decision="keep",
                    post_id="",
                ),
            ]
        )

        result = filter_linked_fate_trials(raw)

        assert len(result) == 2
        assert set(result["post_id"]) == {"post_a", "post_b"}
        assert set(result["decision"]) == {"keep", "remove"}


class TestDedupeWorkerVotes:
    """Tests for dedupe_worker_votes()."""

    def test_drops_conflicting_worker_post_pair(self):
        """Drop worker-post pairs with both keep and remove decisions."""
        trials = pd.DataFrame(
            [
                _trial_row(
                    post_id="post_x",
                    prolific_id="conflict_worker",
                    decision="keep",
                    trial_index=0,
                ),
                _trial_row(
                    post_id="post_x",
                    prolific_id="conflict_worker",
                    decision="remove",
                    trial_index=1,
                ),
                _trial_row(
                    post_id="post_x",
                    prolific_id="clean_worker",
                    decision="keep",
                    trial_index=2,
                ),
            ]
        )

        result = dedupe_worker_votes(trials)

        assert len(result) == 1
        assert result.iloc[0]["prolific_id"] == "clean_worker"
        assert result.iloc[0]["decision"] == "keep"

    def test_keeps_earliest_trial_index_for_duplicate_keep(self):
        """Keep the earliest trial_index when a worker votes keep twice."""
        trials = pd.DataFrame(
            [
                _trial_row(
                    post_id="post_y",
                    prolific_id="repeat_worker",
                    decision="keep",
                    trial_index=9,
                    time_elapsed=20.0,
                ),
                _trial_row(
                    post_id="post_y",
                    prolific_id="repeat_worker",
                    decision="keep",
                    trial_index=0,
                    time_elapsed=10.0,
                ),
            ]
        )

        result = dedupe_worker_votes(trials)

        assert len(result) == 1
        assert int(result.iloc[0]["trial_index"]) == 0


class TestBuildPerPostVotes:
    """Tests for build_per_post_votes()."""

    def test_aggregates_counts_after_full_pipeline(self):
        """Aggregate split and unanimous posts after filter and dedupe."""
        raw = pd.DataFrame(
            [
                _trial_row(
                    post_id="twitter_x",
                    prolific_id="w1",
                    decision="keep",
                    trial_index=0,
                ),
                _trial_row(
                    post_id="twitter_x",
                    prolific_id="w2",
                    decision="keep",
                    trial_index=1,
                ),
                _trial_row(
                    post_id="twitter_x",
                    prolific_id="w3",
                    decision="remove",
                    trial_index=2,
                ),
                _trial_row(
                    post_id="reddit_y",
                    prolific_id="w4",
                    decision="keep",
                    trial_index=0,
                ),
                _trial_row(
                    post_id="reddit_y",
                    prolific_id="w5",
                    decision="keep",
                    trial_index=1,
                ),
                _trial_row(
                    post_id="reddit_y",
                    prolific_id="w6",
                    decision="keep",
                    trial_index=2,
                ),
            ]
        )

        result = build_per_post_votes(raw=raw)
        twitter = result.loc[result["post_id"] == "twitter_x"].iloc[0]
        reddit = result.loc[result["post_id"] == "reddit_y"].iloc[0]

        assert int(twitter["n_raters"]) == 3
        assert int(twitter["keep_count"]) == 2
        assert int(twitter["remove_count"]) == 1
        assert bool(twitter["is_unanimous"]) is False
        assert int(reddit["n_raters"]) == 3
        assert int(reddit["keep_count"]) == 3
        assert int(reddit["remove_count"]) == 0
        assert bool(reddit["is_unanimous"]) is True


class TestAggregateVotesPerPost:
    """Tests for aggregate_votes_per_post()."""

    def test_raises_when_original_text_is_unstable(self):
        """Raise ValueError when one post has conflicting original text."""
        trials = pd.DataFrame(
            [
                _trial_row(
                    post_id="post_z",
                    prolific_id="w1",
                    decision="keep",
                    original_text="text_a",
                ),
                _trial_row(
                    post_id="post_z",
                    prolific_id="w2",
                    decision="remove",
                    original_text="text_b",
                ),
            ]
        )

        with pytest.raises(ValueError, match="stable original/mirror text"):
            aggregate_votes_per_post(trials)
