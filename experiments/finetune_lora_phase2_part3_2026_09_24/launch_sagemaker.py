"""Launch SageMaker jobs for Part 3 LoRA fine-tuning experiments.

Wraps ``experiments.finetune_qwen_model_2026_08_08.launch_sagemaker`` with
per-experiment S3 layout and Qwen3.5 thinking-disabled template kwargs.

Run from root::

    PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \\
      experiments/finetune_lora_phase2_part3_2026_09_24/launch_sagemaker.py \\
      --mode train --experiment experiment1_unanimous --run-id <RUN_ID> \\
      [--smoke] [--dry-run] [--wait]
"""

from __future__ import annotations

import argparse
import os
import sys

from experiments.finetune_lora_phase2_part3_2026_09_24.shared.run_config import (
    AWS_REGION,
    CHAT_TEMPLATE_KWARGS,
    ECR_REPO_NAME,
    EXPERIMENT_NAMES,
    INSTANCE_TYPE,
    MODEL_ID,
    S3_BUCKET,
    S3_PREFIX,
    WANDB_PROJECT,
    chat_template_kwargs_json,
    default_hyperparams,
)
from experiments.finetune_qwen_model_2026_08_08 import launch_sagemaker as prior

LaunchMode = prior.LaunchMode
JobConfig = prior.JobConfig

DEFAULT_SAGEMAKER_ROLE_ARN = (
    "arn:aws:iam::517478598677:role/mirrorview-qwen-finetune-sm-exec"
)
CONTAINER_ENTRY_POINT = (
    "/app/experiments/finetune_lora_phase2_part3_2026_09_24/entrypoint.sh",
)


def _load_sagemaker_role_arn() -> str:
    """Return SAGEMAKER_ROLE_ARN, with a known-role fallback if redacted."""
    raise NotImplementedError


def _validate_mode_experiment(mode: LaunchMode, experiment: str) -> None:
    """Reject invalid mode and experiment pairings."""
    raise NotImplementedError


def resolve_image_uri(region: str, account_id: str | None = None) -> str:
    """Build ECR image URI for this experiment repository."""
    raise NotImplementedError


def build_job_config(
    mode: LaunchMode,
    experiment: str,
    run_id: str,
    role_arn: str,
    hf_token: str,
    wandb_api_key: str | None,
    image_uri: str,
    smoke: bool = False,
    region: str = AWS_REGION,
    instance_type: str = INSTANCE_TYPE,
) -> JobConfig:
    """Construct frozen job config for a mode and experiment.

    S3 layout
    ---------
    train
        data: ``{prefix}/{experiment}/data/``
        output: ``{prefix}/{experiment}/adapters/{run_id}/``
    infer_baseline (experiment4 only)
        data: ``{prefix}/data/``
        output: ``{prefix}/{experiment}/preds/``
    infer_adapter
        data: ``{prefix}/data/``
        adapter: ``{prefix}/{experiment}/adapters/{run_id}/``
        output: ``{prefix}/{experiment}/preds/``
    """
    raise NotImplementedError


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Launch Part 3 Qwen LoRA SageMaker train/infer jobs."
    )
    parser.add_argument(
        "--mode",
        choices=[m.value for m in LaunchMode],
        required=True,
        help="train | infer_baseline | infer_adapter",
    )
    parser.add_argument(
        "--experiment",
        choices=list(EXPERIMENT_NAMES),
        required=True,
        help="Part 3 experiment directory name.",
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="Run id for adapter and prediction paths.",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Set SMOKE=1 (train max_steps=2, infer limit=5).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print config without calling fit().",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Block until the SageMaker job completes.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint."""
    raise NotImplementedError


if __name__ == "__main__":
    main(sys.argv[1:])
