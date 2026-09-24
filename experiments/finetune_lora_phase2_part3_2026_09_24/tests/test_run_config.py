"""Tests for Part 3 run configuration."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from experiments.finetune_lora_phase2_part3_2026_09_24.shared.run_config import (
    CHAT_TEMPLATE_KWARGS,
    MODEL_ID,
    RANDOM_SEED,
    assert_no_thinking_body,
    default_hyperparams,
    render_infer_prompt,
)
from experiments.finetune_qwen_model_2026_08_08.src.train_config import (
    default_hyperparams as prior_default_hyperparams,
)

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
CHAT_FIXTURE = EXPERIMENT_ROOT / "data" / "chat_test_unanimous.jsonl"
_THINKING_BODY_PATTERN = re.compile(r"<think>\s*\S")


class TestRunConfig:
    """Tests for default_hyperparams()."""

    def test_experiment1_defaults(self) -> None:
        """Verifies Part 3 hyperparams override August defaults for experiment1."""
        # Arrange
        prior = prior_default_hyperparams()
        expected_model_id = "Qwen/Qwen3.5-4B"
        expected_seed = 1
        expected_lora_r = 16
        expected_epochs = 3

        # Act
        result = default_hyperparams("experiment1_unanimous")

        # Assert
        assert result.model_id == expected_model_id
        assert result.seed == expected_seed
        assert result.lora_r == expected_lora_r == prior.lora_r
        assert result.num_train_epochs == expected_epochs

    def test_experiment2_epochs(self) -> None:
        """Verifies experiment2_modal uses one training epoch."""
        # Act
        result = default_hyperparams("experiment2_modal")

        # Assert
        assert result.num_train_epochs == 1


class TestTemplateParity:
    """Tests for inference prompt rendering with thinking disabled."""

    @pytest.fixture(scope="class")
    def tokenizer(self):
        """Load tokenizer only (no model weights)."""
        from transformers import AutoTokenizer

        return AutoTokenizer.from_pretrained(
            MODEL_ID,
            trust_remote_code=True,
        )

    @pytest.fixture(scope="class")
    def sample_messages(self) -> list[dict]:
        """Load one rubric chat record from the Part 3 fixture."""
        line = CHAT_FIXTURE.read_text(encoding="utf-8").splitlines()[0]
        payload = json.loads(line)
        return payload["messages"]

    def test_infer_prompt_has_no_thinking_body(
        self,
        tokenizer,
        sample_messages: list[dict],
    ) -> None:
        """Verifies infer-rendered prompt has no non-empty thinking body."""
        # Arrange
        chat_template_kwargs = CHAT_TEMPLATE_KWARGS

        # Act
        prompt = render_infer_prompt(
            tokenizer,
            sample_messages,
            chat_template_kwargs,
        )

        # Assert
        assert_no_thinking_body(prompt)
        assert _THINKING_BODY_PATTERN.search(prompt) is None
