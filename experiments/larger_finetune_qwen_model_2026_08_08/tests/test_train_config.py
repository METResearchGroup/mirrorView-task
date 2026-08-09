"""Tests for larger-experiment train config overrides."""

from __future__ import annotations

from experiments.finetune_qwen_model_2026_08_08.src import train_config as prior_cfg
from experiments.larger_finetune_qwen_model_2026_08_08.src.train_config import (
    MODEL_ID,
    NUM_TRAIN_EPOCHS,
    WANDB_PROJECT,
    default_hyperparams,
)


class TestDefaultHyperparams:
    """Tests for default_hyperparams()."""

    def test_overrides_wandb_and_epochs(self):
        """Keeps shared knobs; overrides W&B project and epoch count."""
        result = default_hyperparams()
        prior = prior_cfg.default_hyperparams()

        assert result.model_id == MODEL_ID == prior.model_id
        assert result.lora_r == prior.lora_r
        assert result.learning_rate == prior.learning_rate
        assert result.assistant_only_loss is True
        assert result.wandb_project == WANDB_PROJECT
        assert prior.wandb_project == "mirrorview-finetune-qwen-2026-08-08"
        assert WANDB_PROJECT == "mirrorview-larger-finetune-qwen-2026-08-08"
        assert NUM_TRAIN_EPOCHS == 1
        assert result.num_train_epochs == 1
        assert prior.num_train_epochs == 3
