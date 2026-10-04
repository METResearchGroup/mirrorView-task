"""Analyze one complete few-shot Jev Study 2 run.

Run from repo root::

    PYTHONPATH=. uv run python -m experiments.few_shot_jev_inference_2026_10_01.src.step3_analysis.main --help
"""

from __future__ import annotations

from experiments.few_shot_jev_inference_2026_10_01.shared.config import FEW_SHOT_VARIANT
from experiments.zero_shot_jev_inference_2026_10_01.src.step3_analysis.analyze import (
    run_analysis_cli,
)


def main() -> None:
    """Analyze one complete few-shot Jev run."""
    run_analysis_cli(FEW_SHOT_VARIANT)


if __name__ == "__main__":
    main()
