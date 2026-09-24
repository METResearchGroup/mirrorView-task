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
import sys

from experiments.finetune_qwen_model_2026_08_08 import launch_sagemaker as prior

LaunchMode = prior.LaunchMode
JobConfig = prior.JobConfig


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
) -> JobConfig:
    """Construct frozen job config for a mode and experiment."""
    raise NotImplementedError


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    raise NotImplementedError


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint."""
    raise NotImplementedError


if __name__ == "__main__":
    main(sys.argv[1:])
