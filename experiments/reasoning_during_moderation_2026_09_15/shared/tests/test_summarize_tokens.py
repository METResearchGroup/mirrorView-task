"""Tests for summarize_tokens()."""

from __future__ import annotations

import pandas as pd

from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    DEEPSEEK_MODEL_ID,
    GROUP_SPLIT,
    GROUP_UNANIMOUS_KEEP,
    GROUP_UNANIMOUS_REMOVE,
    QWEN_MODEL_ID,
    STATUS_TRUNCATED,
    STATUS_VALID,
)
from experiments.reasoning_during_moderation_2026_09_15.experiment1.summarize import (
    summarize_tokens,
)


def _row(model_id: str, group: str, count: int, status: str = STATUS_VALID) -> dict[str, object]:
    return {
        "model_id": model_id,
        "group": group,
        "thinking_token_count": count,
        "status": status,
        "post_id": f"{model_id}-{group}-{count}-{status}",
    }


class TestSummarizeTokens:
    """Tests for summarize_tokens function."""

    def test_six_rows_without_accuracy_columns(self) -> None:
        """Verifies six rows and the Qwen split mean."""
        traces = pd.DataFrame(
            [
                _row(QWEN_MODEL_ID, GROUP_SPLIT, 10),
                _row(QWEN_MODEL_ID, GROUP_UNANIMOUS_KEEP, 20),
                _row(QWEN_MODEL_ID, GROUP_UNANIMOUS_REMOVE, 30),
                _row(DEEPSEEK_MODEL_ID, GROUP_SPLIT, 11),
                _row(DEEPSEEK_MODEL_ID, GROUP_UNANIMOUS_KEEP, 21),
                _row(DEEPSEEK_MODEL_ID, GROUP_UNANIMOUS_REMOVE, 31),
            ]
        )
        expected = 10.0

        result = summarize_tokens(traces)
        qwen_split = result[
            (result["model_id"] == QWEN_MODEL_ID) & (result["group"] == GROUP_SPLIT)
        ]

        assert len(result) == 6
        assert float(qwen_split.iloc[0]["mean"]) == expected
        assert "f1" not in result.columns
        assert "accuracy" not in result.columns

    def test_truncated_rate_and_valid_count(self) -> None:
        """Verifies truncated_rate is half when one of two posts is truncated."""
        traces = pd.DataFrame(
            [
                _row(QWEN_MODEL_ID, GROUP_SPLIT, 10, STATUS_VALID),
                _row(QWEN_MODEL_ID, GROUP_SPLIT, 0, STATUS_TRUNCATED),
            ]
        )
        expected_rate = 0.5
        expected_valid = 1

        result = summarize_tokens(traces)
        row = result.iloc[0]

        assert float(row["truncated_rate"]) == expected_rate
        assert int(row["n_valid"]) == expected_valid
