"""Dual-arm keep/remove classifier via research_tools LLM runner.

Control arm uses the study prompt only. Tuned arm appends keep/remove feature
criteria from ``generate_prompt``.

Run from repo root::

    PYTHONPATH=. uv run python experiments/llm_prompt_engineering_2026_08_05/run_classifier.py \\
      --arm both --limit 5 --model gpt-5.4-nano

    PYTHONPATH=. uv run python experiments/llm_prompt_engineering_2026_08_05/run_classifier.py \\
      --arm both --model gpt-5.4-nano
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from enum import Enum
from pathlib import Path
from typing import Any

import pandas as pd
from tqdm import tqdm

from experiments.llm_prompt_engineering_2026_08_05.generate_prompt import (
    generate_prompt,
)
from research_tools.llm.runner import run
from shared.schemas import IsRemoveResult

EXPERIMENT_ROOT = Path(__file__).resolve().parent
DEFAULT_SUBSET_PATH = EXPERIMENT_ROOT / "subset_labels.csv"
DEFAULT_MODEL = "gpt-5.4-nano"
SUBSET_SEED = 42
OUTPUTS_ROOT = EXPERIMENT_ROOT / "outputs"


class Arm(str, Enum):
    """Classifier prompt arm."""

    CONTROL = "control"
    TUNED = "tuned"
    BOTH = "both"


ARM_ADDENDUM: dict[Arm, bool] = {
    Arm.CONTROL: False,
    Arm.TUNED: True,
}


def prompt_fn(item: dict[str, Any]) -> list[dict[str, str]]:
    """Build a single user message for one subset row.

    Parameters
    ----------
    item
        Runner item with ``original_text``, ``mirror_text``, and ``arm``.

    Returns
    -------
    list[dict[str, str]]
        Chat messages accepted by ``research_tools.llm.runner.run``.
    """
    arm = Arm(item["arm"])
    content = generate_prompt(
        post_1_text=str(item["original_text"]),
        post_2_text=str(item["mirror_text"]),
        add_keep_remove_features_addendum=ARM_ADDENDUM[arm],
    )
    return [{"role": "user", "content": content}]


def writer_map_fn(item: dict[str, Any], result: IsRemoveResult) -> dict[str, Any]:
    """Map one item and structured result to a JSON-serializable output row.

    Parameters
    ----------
    item
        Runner item with gold labels and arm.
    result
        Structured ``IsRemoveResult`` from the model.

    Returns
    -------
    dict[str, Any]
        Prediction row written under the arm output directory.
    """
    predicted_is_remove = bool(result.is_remove)
    return {
        "message_id": item["message_id"],
        "arm": item["arm"],
        "keep_remove_label": int(item["keep_remove_label"]),
        "decision": item["decision"],
        "predicted_is_remove": predicted_is_remove,
        "predicted_label": int(predicted_is_remove),
        "result": result.model_dump(),
    }


def _wrap_writer_with_progress(
    base_writer: Callable[[dict[str, Any], IsRemoveResult], dict[str, Any]],
    progress_bar: tqdm,
) -> Callable[[dict[str, Any], IsRemoveResult], dict[str, Any]]:
    """Advance the progress bar after each completed runner item."""

    def wrapped(item: dict[str, Any], result: IsRemoveResult) -> dict[str, Any]:
        row = base_writer(item, result)
        progress_bar.update(1)
        return row

    return wrapped


def load_subset(subset_path: Path, limit: int | None) -> pd.DataFrame:
    """Load the frozen subset CSV, optionally truncating to the first ``limit`` rows.

    Parameters
    ----------
    subset_path
        Path to ``subset_labels.csv``.
    limit
        When set, keep only the first ``limit`` rows.

    Returns
    -------
    pd.DataFrame
        Rows to classify.

    Raises
    ------
    FileNotFoundError
        When ``subset_path`` does not exist.
    ValueError
        When ``limit`` is set and is not positive.
    """
    if not subset_path.is_file():
        raise FileNotFoundError(subset_path)
    if limit is not None and limit <= 0:
        raise ValueError(f"--limit must be positive, got {limit}")
    frame = pd.read_csv(subset_path)
    if limit is not None:
        return frame.iloc[:limit].reset_index(drop=True)
    return frame.reset_index(drop=True)


def rows_to_items(frame: pd.DataFrame, arm: Arm) -> list[dict[str, Any]]:
    """Convert subset rows into runner items for one arm.

    Parameters
    ----------
    frame
        Subset rows.
    arm
        ``control`` or ``tuned`` (not ``both``).

    Returns
    -------
    list[dict[str, Any]]
        One runner item per row.

    Raises
    ------
    ValueError
        When ``arm`` is ``both``.
    """
    if arm is Arm.BOTH:
        raise ValueError("rows_to_items requires control or tuned, not both")
    items: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        items.append(
            {
                "message_id": str(row["message_id"]),
                "original_text": str(row["original_text"]),
                "mirror_text": str(row["mirror_text"]),
                "decision": str(row["decision"]).strip().lower(),
                "keep_remove_label": int(row["keep_remove_label"]),
                "arm": arm.value,
            }
        )
    return items


def arm_output_base(arm: Arm) -> Path:
    """Return the output base path for one concrete arm."""
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
        OpenAI model id.
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
            },
        )
    finally:
        progress_bar.close()


def resolve_arms(arm: Arm) -> list[Arm]:
    """Expand ``both`` into sequential concrete arms."""
    if arm is Arm.BOTH:
        return [Arm.CONTROL, Arm.TUNED]
    return [arm]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for the dual-arm classifier."""
    parser = argparse.ArgumentParser(
        description=(
            "Classify frozen subset rows with control and/or feature-tuned prompts."
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
        help=f"OpenAI model id (default: {DEFAULT_MODEL}).",
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
        print(f"arm={concrete_arm.value} wrote {len(items)} predictions to {output_dir}")


if __name__ == "__main__":
    main()
