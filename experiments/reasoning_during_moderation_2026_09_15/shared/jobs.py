"""Build Hugging Face Jobs commands for GPU completions.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment1/run.py --smoke --limit 3
"""

from __future__ import annotations

import subprocess

from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    HF_JOB_FLAVOR,
    HF_JOB_TIMEOUT,
)

HF_JOB_IMAGE = "pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel"
REPO_CLONE_URL = (
    "https://x-access-token:${METRESEARCHGROUP_GITHUB_PAT_TOKEN}"
    "@github.com/METResearchGroup/mirrorView-task.git"
)
UV_INSTALL_SCRIPT = "https://astral.sh/uv/install.sh"


def hf_job_command(script: str, extra_args: list[str]) -> list[str]:
    """Return an ``hf jobs run`` command that clones this commit and runs ``script``."""
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    return [
        "hf",
        "jobs",
        "run",
        HF_JOB_IMAGE,
        "--flavor",
        HF_JOB_FLAVOR,
        "--timeout",
        HF_JOB_TIMEOUT,
        *_secret_flags(),
        "--",
        "bash",
        "-lc",
        _remote_shell(commit, script, extra_args),
    ]


def _secret_flags() -> list[str]:
    names = (
        "HF_TOKEN",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "METRESEARCHGROUP_GITHUB_PAT_TOKEN",
    )
    flags: list[str] = []
    for name in names:
        flags.extend(["--secrets", name])
    return flags


def _remote_shell(commit: str, script: str, extra_args: list[str]) -> str:
    joined_args = " ".join(extra_args)
    return (
        "apt-get update && apt-get install -y --no-install-recommends git curl "
        f"&& curl -LsSf {UV_INSTALL_SCRIPT} | sh && export PATH=\"$HOME/.local/bin:$PATH\" "
        f"&& git clone {REPO_CLONE_URL} repo && cd repo && git checkout {commit} "
        "&& uv sync --frozen --no-install-package torch "
        f"&& PYTHONPATH=. uv run --no-sync python {script} {joined_args}"
    )
