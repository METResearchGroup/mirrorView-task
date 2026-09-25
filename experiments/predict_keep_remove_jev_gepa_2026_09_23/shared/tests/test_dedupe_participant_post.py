"""Tests for dedupe_participant_post."""

from __future__ import annotations

import pandas as pd

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.cohort import (
    dedupe_participant_post,
    filter_scored_trials,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.tests.conftest import trial_row


class TestDedupeParticipantPost:
    """Tests for dedupe_participant_post."""

    def test_keeps_earliest_trial_index_for_duplicate_participant_post(
        self,
        mixed_trials: pd.DataFrame,
    ) -> None:
        """One row remains for duplicate prolific/post pairs with the lowest trial_index."""
        filtered = filter_scored_trials(mixed_trials)
        result = dedupe_participant_post(filtered)
        p5_rows = result.loc[result["post_id"] == "P5"]
        assert len(p5_rows) == 1
        assert int(p5_rows.iloc[0]["trial_index"]) == 1

    def test_duplicate_rows_with_different_time_elapsed(self) -> None:
        """Earlier time_elapsed wins when trial_index matches."""
        frame = pd.DataFrame(
            [
                trial_row(
                    post_id="PX",
                    prolific_id="W",
                    trial_index=1,
                    time_elapsed=20.0,
                ),
                trial_row(
                    post_id="PX",
                    prolific_id="W",
                    trial_index=1,
                    time_elapsed=5.0,
                ),
            ]
        )
        result = dedupe_participant_post(filter_scored_trials(frame))
        assert len(result) == 1
        assert float(result.iloc[0]["time_elapsed"]) == 5.0
