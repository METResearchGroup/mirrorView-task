"""Training constants for the larger modal-label Qwen LoRA experiment.

Reuses hyperparams from the prior experiment and overrides only the W&B project.

Run from root: PYTHONPATH=. uv run python -c "from experiments.larger_finetune_qwen_model_2026_08_08.src.train_config import WANDB_PROJECT; print(WANDB_PROJECT)"
"""

from __future__ import annotations

from dataclasses import replace

from experiments.finetune_qwen_model_2026_08_08.src.train_config import (
    MODEL_ID,
    TRAIN_SEED,
    TrainHyperparams,
    default_hyperparams as _prior_default_hyperparams,
)

WANDB_PROJECT = "mirrorview-larger-finetune-qwen-2026-08-08"

__all__ = [
    "MODEL_ID",
    "TRAIN_SEED",
    "WANDB_PROJECT",
    "TrainHyperparams",
    "default_hyperparams",
]


def default_hyperparams() -> TrainHyperparams:
    """Return prior hyperparams with this experiment's W&B project."""
    return replace(_prior_default_hyperparams(), wandb_project=WANDB_PROJECT)
