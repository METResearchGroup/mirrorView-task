"""Tests for reflection LM usage logging wrapper."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.reflection_logging import (
    make_reflection_lm_with_usage_log,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.pricing import estimate_reflection_cost_usd


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

    def test_total_cost_uses_pinned_table_when_litellm_cost_is_zero(
        self, tmp_path: Path
    ) -> None:
        """GEPA total_cost must track pinned Luna/Terra rates, not litellm's zero."""
        usage_path = tmp_path / "reflection_usage.jsonl"
        model = "openai/gpt-6-luna"
        prompt_tokens = 100
        completion_tokens = 50

        def fake_completion() -> MagicMock:
            fake = MagicMock()
            fake.choices = [
                MagicMock(message=MagicMock(content="ok"), finish_reason="stop")
            ]
            fake.usage = MagicMock(
                prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
            )
            return fake

        expected_one_call = estimate_reflection_cost_usd(
            model, prompt_tokens, completion_tokens
        )

        with patch("litellm.completion", side_effect=lambda **_: fake_completion()):
            with patch("litellm.completion_cost", return_value=0.0):
                lm = make_reflection_lm_with_usage_log(
                    model,
                    usage_jsonl_path=usage_path,
                    wandb_run=None,
                )
                lm("first")
                assert lm.total_cost == expected_one_call

                lm("second")
                expected_two_calls = expected_one_call * 2
                assert lm.total_cost == expected_two_calls
