"""Tests for slim_trials()."""

from __future__ import annotations

import pandas as pd
import pytest

from experiments.reasoning_during_moderation_2026_09_15.shared.cohort import (
    assert_stable_pair_text,
    slim_trials,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    DECISION_KEEP,
    EVALUATION_MODE_LINKED_FATE,
    TRIAL_TYPE_MODERATION,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.tests.conftest import (
    EVALUATION_MODE_SINGLE,
    TRIAL_TYPE_PRACTICE,
    trial_row,
)


class TestSlimTrials:
    """Tests for slim_trials function."""

    def test_keeps_linked_fate_moderation_trials(
        self, mixed_trials: pd.DataFrame
    ) -> None:
        """Verifies practice and single-mode rows are dropped."""
        result = slim_trials(mixed_trials)
        expected_types = {TRIAL_TYPE_MODERATION}
        expected_modes = {EVALUATION_MODE_LINKED_FATE}

        assert set(result["trial_type"]) == expected_types
        assert set(result["evaluation_mode"]) == expected_modes
        assert TRIAL_TYPE_PRACTICE not in set(result["trial_type"])
        assert EVALUATION_MODE_SINGLE not in set(result["evaluation_mode"])
        assert "P" not in set(result["post_id"].astype(str))
        assert "S" not in set(result["post_id"].astype(str))

    def test_drops_empty_post_ids(self) -> None:
        """Verifies empty and nan post ids are dropped."""
        frame = pd.DataFrame(
            [
                trial_row("A", "w1", DECISION_KEEP),
                trial_row("", "w2", DECISION_KEEP),
                trial_row("nan", "w3", DECISION_KEEP),
            ]
        )

        result = slim_trials(frame)
        expected = ["A"]

        assert list(result["post_id"]) == expected


class TestAssertStablePairText:
    """Tests for assert_stable_pair_text function."""

    def test_raises_on_conflicting_original_text(self) -> None:
        """Verifies conflicting original text raises ValueError."""
        trials = pd.DataFrame(
            [
                trial_row("A", "w1", DECISION_KEEP, original_text="o1"),
                trial_row("A", "w2", DECISION_KEEP, original_text="o2"),
            ]
        )

        with pytest.raises(ValueError):
            assert_stable_pair_text(trials)
