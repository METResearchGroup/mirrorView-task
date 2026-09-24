"""Tests for combined Part 2 + Part 3 keep/remove label transform."""

from __future__ import annotations

import pandas as pd
import pytest

from shared.data.transformed.study_phase_2_part_2_and_3.transform import (
    build_keep_remove_labels,
)
from shared.data.transformed.study_phase_2_part_3.transform import OUTPUT_COLUMNS


@pytest.mark.integration
class TestLiveUnionKeepRemoveLabels:
    """Integration checks for the combined cohort label table."""

    def test_union_row_counts_and_min_raters(self) -> None:
        """Union table matches expected scale and every post has at least 3 raters."""
        result = build_keep_remove_labels()

        assert len(result) == 20000
        assert (result["n_raters"] >= 3).all()
        keep = int((result["decision"] == "keep").sum())
        remove = int((result["decision"] == "remove").sum())
        assert keep == 15140
        assert remove == 4860
        assert int(result["n_raters"].sum()) == 103060
        assert list(result.columns) == OUTPUT_COLUMNS
