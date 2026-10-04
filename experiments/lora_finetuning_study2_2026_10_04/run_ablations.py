"""Start the three Study 2 LoRA ablations on Hugging Face Jobs.

Builds and pushes the image once, then submits one job per ablation.
The jobs run at the same time. Each job runs ``train.py`` on a different
label set and writes to its own Weights & Biases project.

Run from the repo root:

    HF_JOB_IMAGE=docker.io/<namespace>/lora-finetuning-study2-2026-10-04:latest \\
        PYTHONPATH=. uv run python experiments/lora_finetuning_study2_2026_10_04/run_ablations.py
"""

from __future__ import annotations

from dataclasses import dataclass

from huggingface_hub import JobInfo

from shared.data.registry import (
    UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS,
    UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS,
    UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS,
)
from shared.models.llm.infra.upload_to_hf_jobs import upload_to_hf_jobs

from experiments.lora_finetuning_study2_2026_10_04.run_job import (
    TRAIN_COMMAND,
    build_image,
    resolve_image,
    training_job_config,
)

PROJECT_PREFIX = "lora_finetuning_study2_2026_10_04"


@dataclass(frozen=True)
class Ablation:
    """One training set and the Weights & Biases project that records it."""

    name: str
    dataset_name: str
    project: str


ABLATIONS = (
    Ablation(
        name="unanimous",
        dataset_name=UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS,
        project=f"{PROJECT_PREFIX}_unanimous",
    ),
    Ablation(
        name="split",
        dataset_name=UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS,
        project=f"{PROJECT_PREFIX}_split",
    ),
    Ablation(
        name="all",
        dataset_name=UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS,
        project=f"{PROJECT_PREFIX}_all",
    ),
)


def train_command(ablation: Ablation) -> tuple[str, ...]:
    """Return the ``train.py`` command for one ablation."""
    return (
        *TRAIN_COMMAND,
        "--dataset",
        ablation.dataset_name,
        "--project",
        ablation.project,
        "--group",
        ablation.name,
    )


def launch_ablations(image: str) -> list[JobInfo]:
    """Build ``image`` once and submit one job per ablation."""
    build_image(image)
    jobs: list[JobInfo] = []
    for index, ablation in enumerate(ABLATIONS):
        job = upload_to_hf_jobs(
            image,
            training_job_config(train_command(ablation), ablation=ablation.name),
            push=index == 0,
        )
        # Print before the next submission. A later failure must not hide a job
        # that is already running.
        print(f"{ablation.project} {job.url}", flush=True)
        jobs.append(job)
    return jobs


def main() -> None:
    """Build the image and start the unanimous, split, and all-label jobs."""
    launch_ablations(resolve_image())


if __name__ == "__main__":
    main()
