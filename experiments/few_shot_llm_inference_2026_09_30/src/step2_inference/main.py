"""Few-shot Study 2 inference command.

Run from repo root::

    PYTHONPATH=. uv run python -m experiments.few_shot_llm_inference_2026_09_30.src.step2_inference.main --help
"""

from __future__ import annotations

from experiments.few_shot_llm_inference_2026_09_30.shared.config import FEW_SHOT_VARIANT
from experiments.few_shot_llm_inference_2026_09_30.shared.prompts import (
    format_baseline_few_shot_keep_remove_prompt,
)
from experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run import (
    run_inference_cli,
)


def main() -> None:
    """Run one few-shot model folder through the shared inference runner."""
    run_inference_cli(FEW_SHOT_VARIANT, format_baseline_few_shot_keep_remove_prompt)


if __name__ == "__main__":
    main()
