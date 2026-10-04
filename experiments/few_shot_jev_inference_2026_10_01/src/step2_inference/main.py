"""Run resumable few-shot Jev inference for one Study 2 run.

Run from repo root::

    PYTHONPATH=. uv run python -m experiments.few_shot_jev_inference_2026_10_01.src.step2_inference.main --help
"""

from __future__ import annotations

from experiments.few_shot_jev_inference_2026_10_01.shared.config import FEW_SHOT_VARIANT
from experiments.few_shot_jev_inference_2026_10_01.shared.jev import (
    build_few_shot_remove_request,
)
from experiments.zero_shot_jev_inference_2026_10_01.src.step2_inference.run import (
    run_inference_cli,
)


def main() -> None:
    """Score prepared pairs with the few-shot Jev request."""
    run_inference_cli(
        FEW_SHOT_VARIANT,
        build_few_shot_remove_request,
        description="Run resumable few-shot Jev inference.",
    )


if __name__ == "__main__":
    main()
