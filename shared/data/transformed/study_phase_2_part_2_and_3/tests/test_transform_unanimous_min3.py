"""Tests for aggregate_unanimous_labels."""

from __future__ import annotations

import pandas as pd

from shared.data.transformed.keep_remove_aggregation import aggregate_unanimous_labels


class TestAggregateUnanimousLabels:
    """Tests for aggregate_unanimous_labels."""

    def test_unanimous_min3_keeps_post_with_three_raters(
        self, unanimous_posts_frame: pd.DataFrame
    ) -> None:
        """Post D (3 keep) included; post E (2 keep) absent."""
        result = aggregate_unanimous_labels(unanimous_posts_frame, min_raters=3)

        message_ids = set(result["message_id"])
        assert "D" in message_ids
        assert "E" not in message_ids
        d_row = result[result["message_id"] == "D"].iloc[0]
        assert d_row["n_raters"] == 3
        assert d_row["decision"] == "keep"

    def test_unanimous_excludes_split_decisions(
        self, unanimous_split_frame: pd.DataFrame
    ) -> None:
        """Post F with split decisions is absent."""
        result = aggregate_unanimous_labels(unanimous_split_frame, min_raters=3)

        assert len(result) == 0

    def test_unanimous_remove_with_four_raters(
        self, unanimous_remove_frame: pd.DataFrame
    ) -> None:
        """Post G with 4 remove ratings has decision remove and label 1."""
        result = aggregate_unanimous_labels(unanimous_remove_frame, min_raters=3)

        assert len(result) == 1
        row = result.iloc[0]
        assert row["decision"] == "remove"
        assert row["keep_remove_label"] == 1
        assert row["n_raters"] == 4
