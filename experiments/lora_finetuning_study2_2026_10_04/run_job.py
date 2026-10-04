"""Build this experiment's image and submit it to Hugging Face Jobs.

Set ``HF_JOB_IMAGE`` to the registry tag to build, push, and run. Jobs
pulls that same tag. Log in to its registry before starting.

Run from the repo root:

    HF_JOB_IMAGE=docker.io/<namespace>/lora-finetuning-study2-2026-10-04:latest \\
        PYTHONPATH=. uv run python experiments/lora_finetuning_study2_2026_10_04/run_job.py
"""

from __future__ import annotations

import os
import subprocess
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
FLAVOR = "a10g-large"
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


def training_job_config() -> HuggingFaceJobConfig:
    """Return the Jobs settings for one LoRA training run."""
    return HuggingFaceJobConfig(
        command=TRAIN_COMMAND,
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
        labels={"experiment": "lora_finetuning_study2_2026_10_04"},
    )


def main() -> None:
    """Build the image, push it, and start the training job."""
    image = resolve_image()
    build_image(image)
    job = upload_to_hf_jobs(image, training_job_config(), push=True)
    print(job.url)


if __name__ == "__main__":
    main()
