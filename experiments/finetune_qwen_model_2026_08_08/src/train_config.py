"""Frozen training constants for Qwen3-4B LoRA fine-tuning.

Run from root: PYTHONPATH=. uv run python -c "from experiments.finetune_qwen_model_2026_08_08.src.train_config import MODEL_ID; print(MODEL_ID)"
"""

from __future__ import annotations

from dataclasses import dataclass, field

MODEL_ID = "Qwen/Qwen3-4B-Instruct-2507"
WANDB_PROJECT = "mirrorview-finetune-qwen-2026-08-08"
TRAIN_SEED = 1

LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
LORA_BIAS = "none"
LORA_TASK_TYPE = "CAUSAL_LM"
LORA_TARGET_MODULES = (
    "q_proj",
    "k_proj",
    "v_proj",
    "o_proj",
    "gate_proj",
    "up_proj",
    "down_proj",
)

NUM_TRAIN_EPOCHS = 3
LEARNING_RATE = 2e-4
LR_SCHEDULER_TYPE = "cosine"
WARMUP_RATIO = 0.04  # within [0.03, 0.05]
PER_DEVICE_TRAIN_BATCH_SIZE = 1
GRADIENT_ACCUMULATION_STEPS = 8
MAX_SEQ_LENGTH = 2048
# Explicit TRL flag: loss only on assistant turns (conversational datasets).
ASSISTANT_ONLY_LOSS = True


@dataclass(frozen=True)
class TrainHyperparams:
    """Locked SFT + LoRA hyperparameter bundle."""

    model_id: str = MODEL_ID
    seed: int = TRAIN_SEED
    num_train_epochs: int = NUM_TRAIN_EPOCHS
    learning_rate: float = LEARNING_RATE
    lr_scheduler_type: str = LR_SCHEDULER_TYPE
    warmup_ratio: float = WARMUP_RATIO
    per_device_train_batch_size: int = PER_DEVICE_TRAIN_BATCH_SIZE
    gradient_accumulation_steps: int = GRADIENT_ACCUMULATION_STEPS
    max_seq_length: int = MAX_SEQ_LENGTH
    assistant_only_loss: bool = ASSISTANT_ONLY_LOSS
    lora_r: int = LORA_R
    lora_alpha: int = LORA_ALPHA
    lora_dropout: float = LORA_DROPOUT
    lora_bias: str = LORA_BIAS
    lora_task_type: str = LORA_TASK_TYPE
    lora_target_modules: tuple[str, ...] = field(
        default_factory=lambda: LORA_TARGET_MODULES
    )
    wandb_project: str = WANDB_PROJECT


def default_hyperparams() -> TrainHyperparams:
    """Return the frozen training hyperparameter bundle."""
    return TrainHyperparams()
