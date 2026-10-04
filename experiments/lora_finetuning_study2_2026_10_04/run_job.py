"""Build this experiment's image and submit one training job.

``run_ablations.py`` is the entry point. It builds and pushes the image
once, then calls ``training_job_config`` and ``upload_to_hf_jobs`` for
each ablation. Jobs pulls the tag in ``HF_JOB_IMAGE``.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Sequence
from pathlib import Path

from lib.aws.s3 import DEFAULT_REGION_NAME
from lib.load_env_vars import EnvVarsContainer
from shared.models.llm.infra.upload_to_hf_jobs import (
    HuggingFaceJobConfig,
    upload_to_hf_jobs,
)

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parents[1]
DOCKERFILE = EXPERIMENT_DIR / "Dockerfile"
TRAIN_COMMAND = (
    "python",
    "experiments/lora_finetuning_study2_2026_10_04/train.py",
)
FLAVOR = "a100-large"
TIMEOUT = "24h"


def resolve_image() -> str:
    """Return the registry tag from ``HF_JOB_IMAGE``."""
    image = os.environ.get("HF_JOB_IMAGE", "").strip()
    if not image:
        raise ValueError(
            "Set HF_JOB_IMAGE to the registry tag to build, push, and run. "
            "Example: docker.io/<namespace>/lora-finetuning-study2-2026-10-04:latest"
        )
    return image


def docker_build_command(image: str) -> list[str]:
    """Return the ``docker build`` command for this experiment."""
    return [
        "docker",
        "build",
        "-f",
        str(DOCKERFILE),
        "-t",
        image,
        str(REPO_ROOT),
    ]


def build_image(image: str) -> None:
    """Build ``image`` from this experiment's Dockerfile."""
    subprocess.run(docker_build_command(image), check=True)


def training_job_config(
    command: Sequence[str] | None = None,
    *,
    ablation: str | None = None,
) -> HuggingFaceJobConfig:
    """Return the Jobs settings for one LoRA training run."""
    labels = {"experiment": "lora_finetuning_study2_2026_10_04"}
    if ablation is not None:
        labels["ablation"] = ablation
    return HuggingFaceJobConfig(
        command=TRAIN_COMMAND if command is None else command,
        flavor=FLAVOR,
        timeout=TIMEOUT,
        env={
            "PYTHONPATH": "/app",
            "PYTHONUNBUFFERED": "1",
            "AWS_DEFAULT_REGION": DEFAULT_REGION_NAME,
            "AWS_REGION": DEFAULT_REGION_NAME,
        },
        secrets={
            "HF_TOKEN": EnvVarsContainer.get_env_var("HF_TOKEN", required=True),
            "WANDB_API_KEY": EnvVarsContainer.get_env_var(
                "WANDB_API_KEY", required=True
            ),
            "AWS_ACCESS_KEY_ID": EnvVarsContainer.get_env_var(
                "AWS_ACCESS_KEY", required=True
            ),
            "AWS_SECRET_ACCESS_KEY": EnvVarsContainer.get_env_var(
                "AWS_ACCESS_KEY_SECRET", required=True
            ),
        },
        labels=labels,
    )


def main() -> None:
    """The three ablations start from ``run_ablations.py``."""
    raise SystemExit(
        "Run experiments/lora_finetuning_study2_2026_10_04/run_ablations.py "
        "to build the image and start the three ablation jobs."
    )


if __name__ == "__main__":
    main()
