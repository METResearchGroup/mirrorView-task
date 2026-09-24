"""Packaged smoke runner for Step 3 discovery LLM calls.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/llm_feature_generation_phase_2_part_3_2026_09_24/smoke_tests/run_smoke_discovery.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
TEXT_ARMS = ("original_only", "mirror_only", "paired")


def main() -> None:
    """Run LiteLLM probe and one mixed batch per text arm."""
    _run_probe()
    for arm in TEXT_ARMS:
        _run_smoke_batch(arm)
    raise SystemExit(0)


def _run_probe() -> None:
    command = [
        "uv",
        "run",
        "python",
        "-m",
        "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.llm_client",
        "--probe",
    ]
    subprocess.run(command, cwd=REPO_ROOT, check=True, env=_python_env())


def _run_smoke_batch(arm: str) -> None:
    command = [
        "uv",
        "run",
        "python",
        "-m",
        "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.generate_features",
        "--arm",
        arm,
        "--batch-design",
        "mixed",
        "--smoke",
        "--seed",
        "42",
    ]
    subprocess.run(command, cwd=REPO_ROOT, check=True, env=_python_env())


def _python_env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = "."
    return env


if __name__ == "__main__":
    main()
