"""Few-shot Study 2 analysis command.

Run from repo root::

    PYTHONPATH=. uv run python -m experiments.few_shot_llm_inference_2026_09_30.src.step3_analysis.main --help
"""

from __future__ import annotations

from experiments.few_shot_llm_inference_2026_09_30.shared.config import FEW_SHOT_VARIANT
from experiments.zero_shot_llm_inference_2026_09_30.src.step3_analysis.analyze import (
    run_analysis_cli,
)


def main() -> None:
    """Analyze one few-shot run through the shared analysis runner."""
    run_analysis_cli(FEW_SHOT_VARIANT)


if __name__ == "__main__":
    main()
