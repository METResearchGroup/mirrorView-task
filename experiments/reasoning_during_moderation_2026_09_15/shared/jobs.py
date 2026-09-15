"""Build Hugging Face Jobs commands for GPU completions.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment1/run.py --smoke --limit 3
"""

from __future__ import annotations

import shlex
import subprocess

from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    HF_JOB_FLAVOR,
    HF_JOB_TIMEOUT,
)

HF_JOB_IMAGE = "vllm/vllm-openai:v0.17.0"
REPO_CLONE_URL = (
    "https://x-access-token:${METRESEARCHGROUP_GITHUB_PAT_TOKEN}"
    "@github.com/METResearchGroup/mirrorView-task.git"
)


def hf_job_command(
    script: str,
    extra_args: list[str],
    *,
    label: str | None = None,
    detach: bool = True,
    timeout: str | None = None,
) -> list[str]:
    """Return an ``hf jobs run`` command that clones this commit and runs ``script``."""
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    branch = subprocess.check_output(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True
    ).strip()
    command = [
        "hf",
        "jobs",
        "run",
        "--flavor",
        HF_JOB_FLAVOR,
        "--timeout",
        timeout if timeout is not None else HF_JOB_TIMEOUT,
    ]
    if detach:
        command.append("--detach")
    if label is not None:
        command.extend(["--label", label])
    command.extend(_secret_flags())
    command.extend(
        [HF_JOB_IMAGE, "bash", "-c", _remote_shell(commit, branch, script, extra_args)]
    )
    return command


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


def _remote_shell(
    commit: str, branch: str, script: str, extra_args: list[str]
) -> str:
    joined_args = " ".join(shlex.quote(argument) for argument in extra_args)
    quoted_branch = shlex.quote(branch)
    quoted_commit = shlex.quote(commit)
    return (
        "apt-get update && apt-get install -y --no-install-recommends git curl "
        f"&& git clone --branch {quoted_branch} --single-branch {REPO_CLONE_URL} repo "
        f"&& cd repo && git checkout {quoted_commit} "
        "&& python3 -m pip install --quiet boto3 pandas pyarrow "
        "&& python3 -c 'import torch, vllm; print(torch.cuda.is_available(), vllm.__version__)' "
        f"&& PYTHONPATH=. python3 {script} {joined_args}"
    )
