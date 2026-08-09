"""Tests for frozen train hyperparameter contracts."""

from __future__ import annotations

from experiments.finetune_qwen_model_2026_08_08.src.train_config import (
    ASSISTANT_ONLY_LOSS,
    LORA_ALPHA,
    LORA_R,
    LORA_TARGET_MODULES,
    MODEL_ID,
    WANDB_PROJECT,
    default_hyperparams,
)


class TestDefaultHyperparams:
    """Tests for default_hyperparams()."""

    def test_locked_model_and_lora(self):
        """Verifies model id and LoRA knobs match the plan freeze."""
        # Arrange / Act
        result = default_hyperparams()

        # Assert
        assert result.model_id == MODEL_ID
        assert result.model_id == "Qwen/Qwen3-4B-Instruct-2507"
        assert result.lora_r == LORA_R == 16
        assert result.lora_alpha == LORA_ALPHA == 32
        assert result.lora_dropout == 0.05
        assert tuple(result.lora_target_modules) == LORA_TARGET_MODULES

    def test_assistant_only_loss_enabled(self):
        """Verifies TRL assistant-only loss flag is explicitly True."""
        # Arrange / Act
        result = default_hyperparams()

        # Assert
        assert ASSISTANT_ONLY_LOSS is True
        assert result.assistant_only_loss is True

    def test_trainer_schedule_knobs(self):
        """Verifies epoch/lr/batch/seq contracts."""
        result = default_hyperparams()
        assert result.num_train_epochs == 3
        assert result.learning_rate == 2e-4
        assert result.lr_scheduler_type == "cosine"
        assert 0.03 <= result.warmup_ratio <= 0.05
        assert result.per_device_train_batch_size == 1
        assert result.gradient_accumulation_steps == 8
        assert result.max_seq_length == 2048
        assert result.seed == 1
        assert result.wandb_project == WANDB_PROJECT
