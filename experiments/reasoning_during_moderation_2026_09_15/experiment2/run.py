"""Run experiment 2 study-plus-criteria completions.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment2/run.py --summarize
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass

from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    DEEPSEEK_MODEL_ID,
    QWEN_MODEL_ID,
    SMOKE_LIMIT,
)


@dataclass(frozen=True)
class PlannedCompletion:
    """Matched experiment 2 fields for one post and model."""

    post_id: str
    model_id: str
    post_1_role: str
    post_2_role: str
    generation_seed: int
    add_criteria: bool
    prompt_arm: str


def planned_completion_fields(
    cohort_row: Mapping[str, object],
    exp1_trace: Mapping[str, object] | None,
) -> PlannedCompletion:
    """Return pair order and seed matched to experiment 1 when a trace exists."""
    raise NotImplementedError


def main() -> None:
    args = _parse_args()
    if args.summarize:
        _summarize()
        return
    _run_full(args)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=("qwen", "deepseek", "both"), default="both")
    parser.add_argument("--summarize", action="store_true")
    parser.add_argument("--limit", type=int, default=SMOKE_LIMIT)
    return parser.parse_args()


def _run_full(args: argparse.Namespace) -> None:
    raise NotImplementedError


def _summarize() -> None:
    raise NotImplementedError


def _selected_models(choice: str) -> tuple[str, ...]:
    if choice == "both":
        return (QWEN_MODEL_ID, DEEPSEEK_MODEL_ID)
    return ({"qwen": QWEN_MODEL_ID, "deepseek": DEEPSEEK_MODEL_ID}[choice],)


if __name__ == "__main__":
    main()
