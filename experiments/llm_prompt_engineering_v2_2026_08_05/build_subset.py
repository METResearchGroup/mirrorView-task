"""Freeze a balanced 1000-post evaluation subset (500 keep + 500 remove).

Imports load/write helpers from
``experiments.llm_prompt_engineering_2026_08_05.build_subset`` and replaces only
the sampling policy.

Run from repo root::

    PYTHONPATH=. uv run python experiments/llm_prompt_engineering_v2_2026_08_05/build_subset.py
    PYTHONPATH=. uv run python experiments/llm_prompt_engineering_v2_2026_08_05/build_subset.py --force
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from experiments.llm_prompt_engineering_2026_08_05.build_subset import (
    load_keep_remove_labels,
    write_subset,
)

EXPERIMENT_ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_PATH = EXPERIMENT_ROOT / "subset_labels.csv"
KEEP_SAMPLE_SIZE = 500
REMOVE_SAMPLE_SIZE = 500
DEFAULT_SEED = 42
TOTAL_SAMPLE_SIZE = KEEP_SAMPLE_SIZE + REMOVE_SAMPLE_SIZE


def sample_balanced_subset(
    frame: pd.DataFrame,
    keep_size: int,
    remove_size: int,
    seed: int,
) -> pd.DataFrame:
    """Sample ``keep_size`` keep and ``remove_size`` remove rows.

    Parameters
    ----------
    frame
        Full keep/remove label frame with normalized ``decision`` values.
    keep_size
        Number of keep rows to sample.
    remove_size
        Number of remove rows to sample.
    seed
        RNG seed for deterministic per-class sampling.

    Returns
    -------
    pd.DataFrame
        Concatenated sample with a reset index (keep rows then remove rows).

    Raises
    ------
    ValueError
        When sample sizes are non-positive or a class has too few rows.
    """
    if keep_size <= 0:
        raise ValueError(f"keep_size must be positive, got {keep_size}")
    if remove_size <= 0:
        raise ValueError(f"remove_size must be positive, got {remove_size}")

    keep_df = frame[frame["decision"] == "keep"]
    remove_df = frame[frame["decision"] == "remove"]
    if len(keep_df) < keep_size:
        raise ValueError(f"Need at least {keep_size} keep rows, got {len(keep_df)}")
    if len(remove_df) < remove_size:
        raise ValueError(
            f"Need at least {remove_size} remove rows, got {len(remove_df)}"
        )

    keep_sample = keep_df.sample(n=keep_size, random_state=seed)
    remove_sample = remove_df.sample(n=remove_size, random_state=seed)
    return pd.concat([keep_sample, remove_sample], ignore_index=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for balanced subset freezing."""
    parser = argparse.ArgumentParser(
        description=(
            "Freeze a balanced evaluation subset (500 keep + 500 remove) from "
            "STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS."
        )
    )
    parser.add_argument(
        "--keep-size",
        type=int,
        default=KEEP_SAMPLE_SIZE,
        help=f"Number of keep rows (default: {KEEP_SAMPLE_SIZE}).",
    )
    parser.add_argument(
        "--remove-size",
        type=int,
        default=REMOVE_SAMPLE_SIZE,
        help=f"Number of remove rows (default: {REMOVE_SAMPLE_SIZE}).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Random seed (default: {DEFAULT_SEED}).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Output CSV path (default: {DEFAULT_OUTPUT_PATH}).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing subset CSV.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entry: load labels, sample balanced subset, write CSV."""
    args = parse_args(argv)
    frame = load_keep_remove_labels()
    subset = sample_balanced_subset(
        frame,
        args.keep_size,
        args.remove_size,
        args.seed,
    )
    keep_count = int((subset["decision"] == "keep").sum())
    remove_count = int((subset["decision"] == "remove").sum())
    if keep_count != args.keep_size or remove_count != args.remove_size:
        raise ValueError(
            f"Expected {args.keep_size} keep / {args.remove_size} remove, "
            f"got {keep_count} keep / {remove_count} remove"
        )
    path = write_subset(subset, args.output, args.force)
    print(
        f"Wrote {len(subset)} rows to {path} "
        f"(keep={keep_count}, remove={remove_count})"
    )


if __name__ == "__main__":
    main()
