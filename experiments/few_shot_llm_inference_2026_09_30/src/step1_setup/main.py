"""Copy the verified Study 2 input into the few-shot experiment prefix.

Run from repo root::

    PYTHONPATH=. uv run python -m experiments.few_shot_llm_inference_2026_09_30.src.step1_setup.main
"""

from __future__ import annotations

from experiments.few_shot_llm_inference_2026_09_30.shared.config import FEW_SHOT_VARIANT
from experiments.zero_shot_llm_inference_2026_09_30.shared.config import ZERO_SHOT_VARIANT
from experiments.zero_shot_llm_inference_2026_09_30.shared.storage import (
    apply_lab_aws_credentials_when_unset,
)
from experiments.zero_shot_llm_inference_2026_09_30.src.step1_setup.prepare import (
    copy_prepared_input,
    print_prepared_input_summary,
)


def main() -> None:
    """Copy the zero-shot input package into the few-shot prefix."""
    apply_lab_aws_credentials_when_unset()
    summary = copy_prepared_input(ZERO_SHOT_VARIANT, FEW_SHOT_VARIANT)
    print_prepared_input_summary(summary)


if __name__ == "__main__":
    main()
