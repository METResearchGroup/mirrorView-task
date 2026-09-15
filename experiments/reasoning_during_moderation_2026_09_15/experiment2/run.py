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
    PROMPT_ARM_CRITERIA,
    QWEN_MODEL_ID,
    SMOKE_LIMIT,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.runner import (
    generation_seed,
)

ADD_CRITERIA = True


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
    if exp1_trace is not None:
        return _from_exp1_trace(exp1_trace)
    return _from_cohort_row(cohort_row)


def _from_exp1_trace(exp1_trace: Mapping[str, object]) -> PlannedCompletion:
    """Copy identity, pair order, and seed from an experiment 1 trace row."""
    return PlannedCompletion(
        str(exp1_trace["post_id"]),
        str(exp1_trace["model_id"]),
        str(exp1_trace["post_1_role"]),
        str(exp1_trace["post_2_role"]),
        int(exp1_trace["generation_seed"]),
        ADD_CRITERIA,
        PROMPT_ARM_CRITERIA,
    )


def _from_cohort_row(cohort_row: Mapping[str, object]) -> PlannedCompletion:
    """Fall back to the cohort pair order and generation_seed(post_id)."""
    post_id = str(cohort_row["post_id"])
    return PlannedCompletion(
        post_id,
        str(cohort_row["model_id"]),
        str(cohort_row["post_1_role"]),
        str(cohort_row["post_2_role"]),
        generation_seed(post_id),
        ADD_CRITERIA,
        PROMPT_ARM_CRITERIA,
    )


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
