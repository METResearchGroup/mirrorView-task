"""Freeze a 500-post evaluation subset from Study Phase 2 Part 2 keep/remove labels.

Run from repo root::

    PYTHONPATH=. uv run python experiments/llm_prompt_engineering_2026_08_05/build_subset.py
    PYTHONPATH=. uv run python experiments/llm_prompt_engineering_2026_08_05/build_subset.py --force
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS

EXPERIMENT_ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_PATH = EXPERIMENT_ROOT / "subset_labels.csv"
DEFAULT_SAMPLE_SIZE = 500
DEFAULT_SEED = 42
REQUIRED_COLUMNS = (
    "message_id",
    "original_text",
    "mirror_text",
    "decision",
    "keep_remove_label",
)
VALID_DECISIONS = frozenset({"keep", "remove"})


def _assert_required_columns(frame: pd.DataFrame) -> None:
    """Raise KeyError when required columns are missing."""
    missing = set(REQUIRED_COLUMNS) - set(frame.columns)
    if missing:
        raise KeyError(f"Keep/remove labels missing columns: {sorted(missing)}")


def _normalize_decision_column(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with lowercase stripped decision values."""
    out = frame.copy()
    out["decision"] = out["decision"].astype(str).str.strip().str.lower()
    return out


def _assert_valid_decisions(frame: pd.DataFrame) -> None:
    """Raise ValueError when decision values are outside keep/remove."""
    observed = set(frame["decision"].unique())
    if not observed <= VALID_DECISIONS:
        raise ValueError(
            f"decision values must be subset of {sorted(VALID_DECISIONS)}, "
            f"got {sorted(observed)}"
        )


def load_keep_remove_labels() -> pd.DataFrame:
    """Load Study Phase 2 Part 2 keep/remove labels with required columns.

    Returns
    -------
    pd.DataFrame
        Full label frame with normalized decision values.

    Raises
    ------
    KeyError
        When required columns are missing.
    ValueError
        When decision values are not keep/remove.
    """
    frame = load_dataset(STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS, low_memory=False)
    _assert_required_columns(frame)
    normalized = _normalize_decision_column(frame)
    _assert_valid_decisions(normalized)
    return normalized.reset_index(drop=True)


def sample_subset(
    frame: pd.DataFrame,
    sample_size: int,
    seed: int,
) -> pd.DataFrame:
    """Draw a simple random sample of ``sample_size`` rows.

    Parameters
    ----------
    frame
        Full keep/remove label frame.
    sample_size
        Number of rows to sample.
    seed
        RNG seed for deterministic sampling.

    Returns
    -------
    pd.DataFrame
        Sampled rows with a reset index.

    Raises
    ------
    ValueError
        When ``sample_size`` is non-positive or exceeds the frame length.
    """
    if sample_size <= 0:
        raise ValueError(f"sample_size must be positive, got {sample_size}")
    if len(frame) < sample_size:
        raise ValueError(
            f"Need at least {sample_size} rows, got {len(frame)}"
        )
    return frame.sample(n=sample_size, random_state=seed).reset_index(drop=True)


def write_subset(
    subset: pd.DataFrame,
    output_path: Path,
    force: bool,
) -> Path:
    """Write the subset CSV, refusing to clobber unless ``force`` is set.

    Parameters
    ----------
    subset
        Sampled evaluation rows.
    output_path
        Destination CSV path.
    force
        When False, raise if the destination already exists.

    Returns
    -------
    Path
        Path written.

    Raises
    ------
    ValueError
        When the file exists and ``force`` is False.
    """
    if output_path.exists() and not force:
        raise ValueError(
            f"Output already exists: {output_path}. Pass --force to overwrite."
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subset.to_csv(output_path, index=False)
    return output_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for subset freezing."""
    parser = argparse.ArgumentParser(
        description=(
            "Freeze a random evaluation subset from "
            "STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS."
        )
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=DEFAULT_SAMPLE_SIZE,
        help=f"Number of rows to sample (default: {DEFAULT_SAMPLE_SIZE}).",
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
    """CLI entry: load labels, sample, and write the frozen subset CSV."""
    args = parse_args(argv)
    frame = load_keep_remove_labels()
    subset = sample_subset(frame, args.sample_size, args.seed)
    path = write_subset(subset, args.output, args.force)
    print(f"Wrote {len(subset)} rows to {path}")


if __name__ == "__main__":
    main()
