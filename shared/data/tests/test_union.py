"""Tests for stacking registered study tables."""

from __future__ import annotations

import pandas as pd
import pytest

from shared.data.union import concat_frames, union_stimuli_frames


class TestConcatFrames:
    """Tests for concat_frames()."""

    def test_stacks_rows_and_aligns_columns(self) -> None:
        """Source rows stay in order, and extra columns are filled with NA."""
        first = pd.DataFrame({"post_id": ["a"], "decision": ["keep"]})
        second = pd.DataFrame(
            {"post_id": ["b"], "decision": ["remove"], "attention_check_passed": [1]}
        )

        result = concat_frames([first, second])

        assert result["post_id"].tolist() == ["a", "b"]
        assert result["decision"].tolist() == ["keep", "remove"]
        assert pd.isna(result.loc[0, "attention_check_passed"])
        assert result.loc[1, "attention_check_passed"] == 1

    def test_raises_when_frames_are_empty(self) -> None:
        """An empty source list cannot be stacked."""
        with pytest.raises(ValueError, match="empty list of frames"):
            concat_frames([])


class TestUnionStimuliFrames:
    """Tests for union_stimuli_frames()."""

    def test_keeps_first_row_for_duplicate_keys(self) -> None:
        """Overlapping post_primary_key values keep the earlier source row."""
        first = pd.DataFrame(
            {
                "post_primary_key": ["shared", "only_first"],
                "original_text": ["june", "june-only"],
            }
        )
        second = pd.DataFrame(
            {
                "post_primary_key": ["shared", "only_second"],
                "original_text": ["september", "september-only"],
            }
        )

        result = union_stimuli_frames([first, second])

        assert result["post_primary_key"].tolist() == [
            "shared",
            "only_first",
            "only_second",
        ]
        assert result["original_text"].tolist() == [
            "june",
            "june-only",
            "september-only",
        ]

    def test_raises_when_id_column_missing(self) -> None:
        """Stimuli tables must include post_primary_key."""
        frames = [pd.DataFrame({"other": ["a"]})]

        with pytest.raises(KeyError, match="post_primary_key"):
            union_stimuli_frames(frames)
