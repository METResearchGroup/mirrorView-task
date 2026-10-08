"""Fine-tune Qwen3.5-4B with LoRA on one Study 2 keep/remove label set.

The dataset and Weights & Biases project come from the command line.
``run_ablations.py`` starts one job per ablation. There is no held-out
eval split.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/lora_finetuning_study2_2026_10_04/train.py \\
        --dataset UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS \\
        --project lora_finetuning_study2_2026_10_04_unanimous \\
        --group unanimous
"""

from __future__ import annotations

import argparse
from pathlib import Path

from lib.timestamp_utils import get_current_timestamp
from shared.models.llm.training.lora_training import LoraTrainer

from experiments.lora_finetuning_study2_2026_10_04.constants import (
    ADAPTER_S3_PREFIX,
    ARTIFACTS_BUCKET,
    LORA_RANK,
    LORA_TARGET_MODULES,
    MAX_LENGTH,
    MODEL_NAME,
    build_adapter_s3_uri,
)
from experiments.lora_finetuning_study2_2026_10_04.dataloader import (
    load_training_dataset,
)

# Rank 128 and a learning rate above the full fine-tuning default, from the
# TRL SFT LoRA guide.
LORA_ALPHA = 32 # see https://thinkingmachines.ai/blog/lora/
LEARNING_RATE = 2e-4
NUM_TRAIN_EPOCHS = 1


def build_parser() -> argparse.ArgumentParser:
    """Return the parser for one ablation run."""
    parser = argparse.ArgumentParser(
        description="Fine-tune Qwen3.5-4B with LoRA on one Study 2 label set."
    )
    parser.add_argument("--dataset", required=True, help="Registry name of the training table.")
    parser.add_argument("--project", required=True, help="Weights & Biases project name.")
    parser.add_argument("--group", required=True, help="Weights & Biases group name.")
    return parser


def build_config(run_name: str, dataset_name: str, project: str, group: str) -> dict:
    """Return the ``LoraTrainer`` config for one run."""
    return {
        "lora": {
            "rank": LORA_RANK,
            "alpha": LORA_ALPHA,
            "target_modules": LORA_TARGET_MODULES,
        },
        "lr": LEARNING_RATE,
        "epochs": NUM_TRAIN_EPOCHS,
        "max_length": MAX_LENGTH,
        "model_name": MODEL_NAME,
        "dataset_name": dataset_name,
        "output_dir": str(Path("/tmp") / run_name),
        "adapter_s3_uri": build_adapter_s3_uri(group, run_name),
        "wandb": {
            "project": project,
            "group": group,
            "run_name": run_name,
        },
    }


def main() -> None:
    """Train on the label set named by ``--dataset``."""
    args = build_parser().parse_args()
    run_name = (
        f"{MODEL_NAME.rsplit('/', 1)[-1]}_lora_{args.group}_{get_current_timestamp()}"
    )
    trainer = LoraTrainer(
        build_config(run_name, args.dataset, args.project, args.group)
    )
    trainer.load_dataset(load_training_dataset(args.dataset))
    trainer.run()


if __name__ == "__main__":
    main()
