"""Tests for study_part tagging on moderation trials."""

from __future__ import annotations

import pandas as pd

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.cohort import (
    STUDY_PART_PART2,
    STUDY_PART_PART3,
    attach_study_part,
)


class TestAttachStudyPart:
    """Tests for attach_study_part."""

    def test_marks_part3_when_attention_check_present(self) -> None:
        """Rows with non-empty attention_check_passed are Part 3."""
        frame = pd.DataFrame(
            {
                "attention_check_passed": ["True", ""],
                "post_id": ["P1", "P2"],
            }
        )
        result = attach_study_part(frame)
        assert result.iloc[0]["study_part"] == STUDY_PART_PART3
        assert result.iloc[1]["study_part"] == STUDY_PART_PART2

    def test_defaults_to_part3_when_marker_column_missing(self) -> None:
        """Part-3-only loads without the marker column are all Part 3."""
        frame = pd.DataFrame({"post_id": ["P1"]})
        result = attach_study_part(frame)
        assert result.iloc[0]["study_part"] == STUDY_PART_PART3
