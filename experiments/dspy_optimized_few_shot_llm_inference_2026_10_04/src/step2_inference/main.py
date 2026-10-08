"""Optimized few-shot Study 2 inference command.

Run from repo root::

    PYTHONPATH=. uv run python -m experiments.dspy_optimized_few_shot_llm_inference_2026_10_04.src.step2_inference.main --help
"""

from __future__ import annotations

from experiments.dspy_optimized_few_shot_llm_inference_2026_10_04.shared.config import (
    OPTIMIZED_FEW_SHOT_VARIANT,
)
from experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run import (
    run_inference_cli,
)
from shared.models.llm.prompt import format_optimized_study_prompt


def main() -> None:
    """Run one optimized few-shot model folder through the shared inference runner."""
    run_inference_cli(OPTIMIZED_FEW_SHOT_VARIANT, format_optimized_study_prompt)


if __name__ == "__main__":
    main()
