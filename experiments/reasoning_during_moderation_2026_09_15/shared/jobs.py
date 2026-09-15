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

HF_JOB_IMAGE = "ghcr.io/astral-sh/uv:python3.12-bookworm-slim"
REPO_CLONE_URL = (
    "https://x-access-token:${METRESEARCHGROUP_GITHUB_PAT_TOKEN}"
    "@github.com/METResearchGroup/mirrorView-task.git"
)


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
        f"git clone {REPO_CLONE_URL} repo && cd repo && git checkout {commit} "
        f"&& uv sync --frozen && PYTHONPATH=. uv run python {script} {joined_args}"
    )
