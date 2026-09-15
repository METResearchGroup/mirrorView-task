"""Build Hugging Face Jobs commands for GPU completions.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment1/run.py --smoke --limit 3
"""

from __future__ import annotations


def hf_job_command(script: str, extra_args: list[str]) -> list[str]:
    raise NotImplementedError
