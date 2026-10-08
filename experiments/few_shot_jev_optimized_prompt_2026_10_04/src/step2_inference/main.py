"""Run resumable optimized-prompt Jev inference for one Study 2 run.

Run from repo root::

    PYTHONPATH=. uv run python -m experiments.few_shot_jev_optimized_prompt_2026_10_04.src.step2_inference.main --help
"""

from __future__ import annotations

from experiments.few_shot_jev_optimized_prompt_2026_10_04.shared.config import OPTIMIZED_VARIANT
from experiments.few_shot_jev_optimized_prompt_2026_10_04.shared.jev import (
    build_optimized_remove_request,
)
from experiments.zero_shot_jev_inference_2026_10_01.src.step2_inference.run import (
    run_inference_cli,
)


def main() -> None:
    """Score prepared pairs with the optimized-prompt Jev request."""
    run_inference_cli(
        OPTIMIZED_VARIANT,
        build_optimized_remove_request,
        description="Run resumable optimized-prompt Jev inference.",
    )


if __name__ == "__main__":
    main()
