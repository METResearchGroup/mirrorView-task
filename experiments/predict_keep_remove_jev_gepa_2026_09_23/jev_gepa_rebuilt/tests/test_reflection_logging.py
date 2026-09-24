"""Tests for reflection LM usage logging wrapper."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.reflection_logging import (
    make_reflection_lm_with_usage_log,
)


class TestReflectionLmWrapper:
    """Tests for make_reflection_lm_with_usage_log."""

    def test_logs_usage_jsonl_after_one_call(self, tmp_path: Path) -> None:
        """One LM call appends usage line with positive input tokens and cumulative USD."""
        usage_path = tmp_path / "reflection_usage.jsonl"
        fake_completion = MagicMock()
        fake_completion.choices = [MagicMock(message=MagicMock(content="ok"), finish_reason="stop")]
        fake_completion.usage = MagicMock(prompt_tokens=100, completion_tokens=50)

        with patch("litellm.completion", return_value=fake_completion):
            with patch("litellm.completion_cost", return_value=0.01):
                lm = make_reflection_lm_with_usage_log(
                    "openai/gpt-6-luna",
                    usage_jsonl_path=usage_path,
                    wandb_run=None,
                )
                lm("hello")

        lines = usage_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["input_tokens"] > 0
        assert record["cumulative_usd"] >= 0
