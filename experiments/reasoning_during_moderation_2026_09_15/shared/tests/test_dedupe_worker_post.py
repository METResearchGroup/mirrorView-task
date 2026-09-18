"""Tests for drop_conflicting_worker_posts() and dedupe_worker_post()."""

from __future__ import annotations

import pandas as pd

from experiments.reasoning_during_moderation_2026_09_15.shared.cohort import (
    dedupe_worker_post,
    drop_conflicting_worker_posts,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    DECISION_KEEP,
    DECISION_REMOVE,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.tests.conftest import (
    trial_row,
)


class TestDropConflictingWorkerPosts:
    """Tests for drop_conflicting_worker_posts function."""

    def test_drops_keep_and_remove_pair(self) -> None:
        """Verifies a worker with both decisions on one post is removed."""
        trials = pd.DataFrame(
            [
                trial_row("C", "w20", DECISION_KEEP, trial_index=0, time_elapsed=0),
                trial_row("C", "w20", DECISION_REMOVE, trial_index=1, time_elapsed=1),
                trial_row("C", "w21", DECISION_KEEP, trial_index=2, time_elapsed=2),
            ]
        )
        expected = ["w21"]

        result = drop_conflicting_worker_posts(trials)

        assert list(result["prolific_id"]) == expected


class TestDedupeWorkerPost:
    """Tests for dedupe_worker_post function."""

    def test_keeps_earlier_identical_keep(self) -> None:
        """Verifies the earlier trial_index remains for duplicate keep rows."""
        trials = pd.DataFrame(
            [
                trial_row("B", "w10", DECISION_KEEP, trial_index=0, time_elapsed=0),
                trial_row("B", "w10", DECISION_KEEP, trial_index=9, time_elapsed=9),
            ]
        )
        expected = 0

        result = dedupe_worker_post(trials)

        assert len(result) == 1
        assert int(result.iloc[0]["trial_index"]) == expected
