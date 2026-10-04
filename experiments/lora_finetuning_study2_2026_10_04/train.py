"""Fine-tune Qwen3.5-4B with LoRA on Study 2 unanimous keep/remove labels.

Uses the full upsampled unanimous table as the training set. There is no
held-out eval split.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/lora_finetuning_study2_2026_10_04/train.py
"""

from __future__ import annotations

from pathlib import Path

from lib.timestamp_utils import get_current_timestamp
from shared.data.registry import UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS
from shared.models.llm.training.lora_training import LoraTrainer

from experiments.lora_finetuning_study2_2026_10_04.dataloader import (
    load_training_dataset,
)

MODEL_NAME = "Qwen/Qwen3.5-4B"
# Rank 256 and a learning rate above the full fine-tuning default, from the
# TRL SFT LoRA guide.
LORA_RANK = 256
LORA_ALPHA = 32 # see https://thinkingmachines.ai/blog/lora/
# Qwen3.5 alternates full attention and Gated DeltaNet linear attention, then
# an MLP. `all-linear` only wraps nn.Linear, so it skips the depthwise conv
# inside linear attention. List both attention families and the MLP.
LORA_TARGET_MODULES = [
    "q_proj",
    "k_proj",
    "v_proj",
    "o_proj",
    "in_proj_qkv",
    "in_proj_z",
    "in_proj_b",
    "in_proj_a",
    "out_proj",
    "conv1d",
    "gate_proj",
    "up_proj",
    "down_proj",
]
LEARNING_RATE = 2e-4
# The study prompt is about 1k tokens before the two posts. 4096 leaves room
# for the posts and keeps the completion inside the trained sequence.
MAX_LENGTH = 4096
WANDB_PROJECT = "lora_finetuning_study2_2026_10_04"
WANDB_GROUP = "trl_lora_training" # TODO: edit to distinguish between the unanimous, split, and all label versions.


def build_config(run_name: str) -> dict:
    """Return the ``LoraTrainer`` config for one run."""
    return {
        "lora": {
            "rank": LORA_RANK,
            "alpha": LORA_ALPHA,
            "target_modules": LORA_TARGET_MODULES,
        },
        "lr": LEARNING_RATE,
        "max_length": MAX_LENGTH,
        "model_name": MODEL_NAME,
        "dataset_name": UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS,
        "output_dir": str(Path("/tmp") / run_name),
        "wandb": {
            "project": WANDB_PROJECT,
            "group": WANDB_GROUP,
            "run_name": run_name,
        },
    }


def main() -> None:
    """Train on the full upsampled unanimous keep/remove set."""
    run_name = f"{MODEL_NAME.rsplit('/', 1)[-1]}_lora_{get_current_timestamp()}"
    trainer = LoraTrainer(build_config(run_name))
    trainer.load_dataset(load_training_dataset())
    trainer.run()


if __name__ == "__main__":
    main()
