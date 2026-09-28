"""Tests for filter_keep_remove_trials and aggregate_modal_labels."""

from __future__ import annotations

import pandas as pd
import pytest

from shared.data.transformed.keep_remove_aggregation import (
    aggregate_modal_labels,
    filter_keep_remove_trials,
)


class TestFilterKeepRemoveTrials:
    """Tests for filter_keep_remove_trials."""

    def test_keeps_linked_fate_keep_remove_with_usable_post_id(
        self, filter_input_frame: pd.DataFrame
    ) -> None:
        """Only linked_fate keep/remove rows with usable post_id remain."""
        result = filter_keep_remove_trials(
            filter_input_frame, dedupe_worker_post=False
        )

        assert len(result) == 3
        assert set(result["post_id"]) == {"X1", "X2", "X3"}
        assert all(result["evaluation_mode"] == "linked_fate")
        assert all(result["decision"].isin(["keep", "remove"]))

    def test_dedupe_drops_conflicting_worker_post_pair(
        self, dedupe_conflict_frame: pd.DataFrame
    ) -> None:
        """Conflicting (prolific_id, post_id) pair drops all rows when deduping."""
        result = filter_keep_remove_trials(
            dedupe_conflict_frame, dedupe_worker_post=True
        )

        assert len(result) == 0

    def test_dedupe_keeps_earliest_non_conflicting_duplicate(
        self, dedupe_duplicate_frame: pd.DataFrame
    ) -> None:
        """Non-conflicting duplicate keeps earliest row by original order."""
        result = filter_keep_remove_trials(
            dedupe_duplicate_frame, dedupe_worker_post=True
        )

        assert len(result) == 1
        assert result.iloc[0]["decision"] == "keep"

    def test_no_dedupe_keeps_both_non_conflicting_duplicates(
        self, dedupe_duplicate_frame: pd.DataFrame
    ) -> None:
        """Without dedupe, non-conflicting duplicate worker-post rows are kept."""
        result = filter_keep_remove_trials(
            dedupe_duplicate_frame, dedupe_worker_post=False
        )

        assert len(result) == 2


class TestAggregateModalLabels:
    """Tests for aggregate_modal_labels."""

    def test_modal_majority_keep_and_tie_remove(
        self, modal_trials_frame: pd.DataFrame
    ) -> None:
        """Post A (2 keep, 1 remove) is keep; post B (1 keep, 1 remove) is remove."""
        result = aggregate_modal_labels(modal_trials_frame)

        decisions = dict(zip(result["message_id"], result["decision"]))
        assert decisions["A"] == "keep"
        assert decisions["B"] == "remove"

    def test_modal_tie_becomes_remove(self, modal_tie_frame: pd.DataFrame) -> None:
        """Tied keep and remove counts become remove."""
        result = aggregate_modal_labels(modal_tie_frame)

        assert len(result) == 1
        assert result.iloc[0]["decision"] == "remove"
        assert result.iloc[0]["keep_remove_label"] == 1

    def test_modal_n_raters_is_unique_prolific_id_count(
        self, modal_n_raters_frame: pd.DataFrame
    ) -> None:
        """n_raters counts unique prolific_id; majority keep wins."""
        result = aggregate_modal_labels(modal_n_raters_frame)

        assert len(result) == 1
        row = result.iloc[0]
        assert row["n_raters"] == 3
        assert row["decision"] == "keep"
        assert row["keep_remove_label"] == 0

    def test_modal_raises_on_text_conflict(
        self, modal_text_conflict_frame: pd.DataFrame
    ) -> None:
        """Conflicting original_text per post_id raises ValueError."""
        with pytest.raises(ValueError, match="conflicts"):
            aggregate_modal_labels(modal_text_conflict_frame)
