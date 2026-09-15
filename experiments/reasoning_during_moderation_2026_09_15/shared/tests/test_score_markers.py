"""Tests for score_trace() and paired_arm_comparison()."""

from __future__ import annotations

import pandas as pd

from experiments.reasoning_during_moderation_2026_09_15.experiment4.markers import (
    score_trace,
)
from experiments.reasoning_during_moderation_2026_09_15.experiment4.summarize import (
    paired_arm_comparison,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    GROUP_SPLIT,
    PROMPT_ARM_CRITERIA,
    PROMPT_ARM_STUDY,
    QWEN_MODEL_ID,
    STATUS_VALID,
)

MARKED_TEXT = "I am not sure. wait, the posts conflict."
CLEAN_TEXT = "Allow both."
MAYBE_ORIGINAL_TEXT = "maybe the original is fine"
EXP1_COUNT = 10
EXP2_COUNT = 8
EXPECTED_TOKEN_DIFF = -2.0


class TestScoreTrace:
    """Tests for score_trace function."""

    def test_flags_uncertainty_revision_and_tension(self) -> None:
        """Verifies all three families fire on the confirmed mixed sentence."""
        result = score_trace(MARKED_TEXT)

        assert result.uncertainty is True
        assert result.revision is True
        assert result.tension is True

    def test_clean_text_has_no_flags(self) -> None:
        """Verifies a short allow sentence scores false on every family."""
        result = score_trace(CLEAN_TEXT)

        assert result.uncertainty is False
        assert result.revision is False
        assert result.tension is False

    def test_maybe_token_and_dropped_original(self) -> None:
        """Verifies maybe is an uncertainty token and original is not tension."""
        result = score_trace(MAYBE_ORIGINAL_TEXT)

        assert result.uncertainty is True
        assert result.tension is False


class TestPairedArmComparison:
    """Tests for paired_arm_comparison function."""

    def test_mean_thinking_token_difference(self) -> None:
        """Verifies experiment 2 minus experiment 1 mean token difference."""
        exp1 = _trace_row(PROMPT_ARM_STUDY, EXP1_COUNT)
        exp2 = _trace_row(PROMPT_ARM_CRITERIA, EXP2_COUNT)

        result = paired_arm_comparison(exp1, exp2)
        row = result.iloc[0]

        assert float(row["mean_thinking_token_diff"]) == EXPECTED_TOKEN_DIFF


def _trace_row(prompt_arm: str, count: int) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "post_id": "p1",
                "model_id": QWEN_MODEL_ID,
                "group": GROUP_SPLIT,
                "status": STATUS_VALID,
                "prompt_arm": prompt_arm,
                "thinking_token_count": count,
                "thinking_text": CLEAN_TEXT,
            }
        ]
    )
