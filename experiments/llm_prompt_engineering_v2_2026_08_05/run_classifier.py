"""Dual-arm keep/remove classifier for v2 (Qwen 3.6 defaults).

Imports prompt/writer/item helpers from
``experiments.llm_prompt_engineering_2026_08_05.run_classifier`` and overrides
only model, subset path, and output roots.

Run from repo root::

    PYTHONPATH=. uv run python experiments/llm_prompt_engineering_v2_2026_08_05/run_classifier.py \\
      --arm both --limit 5 --model qwen/qwen3.6-plus

    PYTHONPATH=. uv run python experiments/llm_prompt_engineering_v2_2026_08_05/run_classifier.py \\
      --arm both --model qwen/qwen3.6-plus
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from tqdm import tqdm

from experiments.llm_prompt_engineering_2026_08_05.run_classifier import (
    Arm,
    load_subset,
    prompt_fn,
    resolve_arms,
    rows_to_items,
    writer_map_fn,
    _wrap_writer_with_progress,
)
from research_tools.llm.runner import run
from shared.schemas import IsRemoveResult

EXPERIMENT_ROOT = Path(__file__).resolve().parent
DEFAULT_SUBSET_PATH = EXPERIMENT_ROOT / "subset_labels.csv"
DEFAULT_MODEL = "qwen/qwen3.6-plus"
SUBSET_SEED = 42
EXPERIMENT_ID = "llm_prompt_engineering_v2_2026_08_05"
OUTPUTS_ROOT = EXPERIMENT_ROOT / "outputs"


def arm_output_base(arm: Arm) -> Path:
    """Return the v2 output base path for one concrete arm."""
    if arm is Arm.BOTH:
        raise ValueError("arm_output_base requires control or tuned, not both")
    return OUTPUTS_ROOT / arm.value


def run_arm(
    items: list[dict[str, Any]],
    arm: Arm,
    model: str,
    subset_path: Path,
    limit: int | None,
) -> Path:
    """Classify all items for one arm and return the timestamped output dir.

    Parameters
    ----------
    items
        Runner items for this arm.
    arm
        ``control`` or ``tuned``.
    model
        research_tools model id (default ``qwen/qwen3.6-plus``).
    subset_path
        Subset CSV path recorded in metadata.
    limit
        Optional row limit recorded in metadata (``None`` = full subset).

    Returns
    -------
    Path
        Timestamped runner output directory.

    Raises
    ------
    ValueError
        When ``items`` is empty or ``arm`` is ``both``.
    """
    if arm is Arm.BOTH:
        raise ValueError("run_arm requires control or tuned, not both")
    if not items:
        raise ValueError("run_arm requires at least one item")

    progress_bar = tqdm(total=len(items), desc=f"Classify ({arm.value})")
    try:
        return run(
            items,
            prompt_fn=prompt_fn,
            response_model=IsRemoveResult,
            model=model,
            output_base_path=arm_output_base(arm),
            writer_map_fn=_wrap_writer_with_progress(writer_map_fn, progress_bar),
            run_metadata={
                "arm": arm.value,
                "model": model,
                "n_items": len(items),
                "subset_path": str(subset_path),
                "limit": limit,
                "subset_seed": SUBSET_SEED,
                "experiment": EXPERIMENT_ID,
            },
        )
    finally:
        progress_bar.close()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for the v2 dual-arm classifier."""
    parser = argparse.ArgumentParser(
        description=(
            "Classify frozen v2 subset rows with control and/or feature-tuned "
            "prompts using Qwen 3.6."
        )
    )
    parser.add_argument(
        "--arm",
        required=True,
        choices=[a.value for a in Arm],
        help="Prompt arm: control, tuned, or both.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional positive row limit for smoke runs (default: all rows).",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"research_tools model id (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--subset",
        type=Path,
        default=DEFAULT_SUBSET_PATH,
        help=f"Frozen subset CSV (default: {DEFAULT_SUBSET_PATH}).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entry: load subset, run requested arm(s), print output dirs."""
    args = parse_args(argv)
    arm = Arm(args.arm)
    frame = load_subset(args.subset, args.limit)
    for concrete_arm in resolve_arms(arm):
        items = rows_to_items(frame, concrete_arm)
        output_dir = run_arm(
            items,
            concrete_arm,
            args.model,
            args.subset,
            args.limit,
        )
        print(
            f"arm={concrete_arm.value} wrote {len(items)} predictions to {output_dir}"
        )


if __name__ == "__main__":
    main()
