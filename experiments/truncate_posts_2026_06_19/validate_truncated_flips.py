from __future__ import annotations

"""
Validate length parity on truncated flips.

Run from repo root:

PYTHONPATH=. uv run python experiments/truncate_posts_2026_06_19/validate_truncated_flips.py
"""

from pathlib import Path

import pandas as pd

from experiments.truncate_posts_2026_06_19.truncate_flips import (
    LENGTH_DIFF_THRESHOLD,
    OUTPUT_CSV,
)

EXPERIMENT_DIR = Path(__file__).resolve().parent
FLIPS_CSV = OUTPUT_CSV


def main() -> None:
    df = pd.read_csv(FLIPS_CSV)
    if "original_text" not in df.columns or "mirrored_text" not in df.columns:
        raise ValueError(
            f"Expected `original_text` and `mirrored_text` columns in {FLIPS_CSV}"
        )

    original_lengths = df["original_text"].fillna("").astype(str).str.len()
    mirrored_lengths = df["mirrored_text"].fillna("").astype(str).str.len()

    nonzero_original = original_lengths > 0
    rel_diff = (mirrored_lengths - original_lengths).abs() / original_lengths
    length_diff_mask = nonzero_original & (rel_diff >= LENGTH_DIFF_THRESHOLD)
    empty_original = original_lengths == 0

    n_posts = len(df)
    n_length_diff = int(length_diff_mask.sum())
    n_empty_original = int(empty_original.sum())

    print(f"Flips CSV: {FLIPS_CSV}")
    print(f"Total posts: {n_posts:,}")
    print()
    print(f"Average original length (chars): {original_lengths.mean():.1f}")
    print(f"Average mirrored length (chars): {mirrored_lengths.mean():.1f}")
    print()
    print(
        f"Posts with mirrored length differing from original by "
        f">={LENGTH_DIFF_THRESHOLD:.0%}: {n_length_diff:,} "
        f"({n_length_diff / n_posts:.1%})"
    )
    if n_empty_original:
        print(
            f"Posts with empty original text (excluded from >=10% check): "
            f"{n_empty_original:,}"
        )


if __name__ == "__main__":
    main()
