"""Copy the verified baseline few-shot input into the optimized experiment prefix.

Run from repo root::

    PYTHONPATH=. uv run python -m experiments.dspy_optimized_few_shot_llm_inference_2026_10_04.src.step1_setup.main
"""

from __future__ import annotations

from experiments.dspy_optimized_few_shot_llm_inference_2026_10_04.shared.config import (
    OPTIMIZED_FEW_SHOT_VARIANT,
)
from experiments.few_shot_llm_inference_2026_09_30.shared.config import FEW_SHOT_VARIANT
from experiments.zero_shot_llm_inference_2026_09_30.shared.storage import (
    apply_lab_aws_credentials_when_unset,
)
from experiments.zero_shot_llm_inference_2026_09_30.src.step1_setup.prepare import (
    copy_prepared_input,
    print_prepared_input_summary,
)


def main() -> None:
    """Copy the baseline few-shot input package into the optimized prefix."""
    apply_lab_aws_credentials_when_unset()
    summary = copy_prepared_input(FEW_SHOT_VARIANT, OPTIMIZED_FEW_SHOT_VARIANT)
    print_prepared_input_summary(summary)


if __name__ == "__main__":
    main()
