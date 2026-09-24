"""Tests for filter_scored_trials."""

from __future__ import annotations

import pandas as pd

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.cohort import filter_scored_trials


class TestFilterScoredTrials:
    """Tests for filter_scored_trials."""

    def test_drops_practice_and_empty_post_id_rows(self, mixed_trials: pd.DataFrame) -> None:
        """Practice and empty post_id rows are removed; only keep/remove remain."""
        result = filter_scored_trials(mixed_trials)
        assert not (result["trial_type"] == "moderation-practice").any()
        assert (result["post_id"].astype(str).str.strip() != "").all()
        assert set(result["decision"].unique()).issubset({"keep", "remove"})
