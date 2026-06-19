from __future__ import annotations

"""
Truncate original and mirrored posts to sentence-aware char limits.

Run from repo root:

PYTHONPATH=. uv run python experiments/truncate_posts_2026_06_19/truncate_flips.py
PYTHONPATH=. uv run python experiments/truncate_posts_2026_06_19/truncate_flips.py --output out.csv --include-truncated-flag
"""

from pathlib import Path

import pandas as pd
import typer

from experiments.match_lengths_original_mirrors_2026_06_19.training_sample import (
    truncate_at_last_sentence,
)

MAX_ORIGINAL_CHARS = 300
MAX_MIRRORED_CHARS = 325
LENGTH_DIFF_THRESHOLD = 0.10

EXPERIMENT_DIR = Path(__file__).resolve().parent
INPUT_CSV = (
    Path(__file__).resolve().parents[1]
    / "scaled_mirrors_generation_2026_06_02"
    / "generated_flips"
    / "combined_flips"
    / "flips.csv"
)
OUTPUT_CSV = EXPERIMENT_DIR / "truncated_flips.csv"
OUTPUT_WITH_FLAG_CSV = EXPERIMENT_DIR / "truncated_flips_with_flag.csv"

app = typer.Typer(add_completion=False)


def _char_lengths(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.len()


def _length_diff_stats(
    original_lengths: pd.Series, mirrored_lengths: pd.Series
) -> tuple[int, int]:
    nonzero_original = original_lengths > 0
    rel_diff = (mirrored_lengths - original_lengths).abs() / original_lengths
    length_diff_mask = nonzero_original & (rel_diff >= LENGTH_DIFF_THRESHOLD)
    empty_original = original_lengths == 0
    return int(length_diff_mask.sum()), int(empty_original.sum())


def _print_metrics(
    *,
    label: str,
    n_posts: int,
    original_lengths_before: pd.Series,
    mirrored_lengths_before: pd.Series,
    original_lengths_after: pd.Series,
    mirrored_lengths_after: pd.Series,
) -> None:
    n_length_diff_before, n_empty_original_before = _length_diff_stats(
        original_lengths_before, mirrored_lengths_before
    )
    n_length_diff_after, n_empty_original_after = _length_diff_stats(
        original_lengths_after, mirrored_lengths_after
    )

    print(label)
    print(f"  Total posts: {n_posts:,}")
    print()
    print("  Before truncation:")
    print(f"    Average original length (chars): {original_lengths_before.mean():.1f}")
    print(f"    Average mirrored length (chars): {mirrored_lengths_before.mean():.1f}")
    print()
    print("  After truncation:")
    print(f"    Average original length (chars): {original_lengths_after.mean():.1f}")
    print(f"    Average mirrored length (chars): {mirrored_lengths_after.mean():.1f}")
    print()
    print(
        f"  Before: posts with mirrored length differing from original by "
        f">={LENGTH_DIFF_THRESHOLD:.0%}: {n_length_diff_before:,} "
        f"({n_length_diff_before / n_posts:.1%})"
    )
    print(
        f"  After: posts with mirrored length differing from original by "
        f">={LENGTH_DIFF_THRESHOLD:.0%}: {n_length_diff_after:,} "
        f"({n_length_diff_after / n_posts:.1%})"
    )
    if n_empty_original_before or n_empty_original_after:
        print(
            f"  Posts with empty original text (excluded from >=10% check): "
            f"before={n_empty_original_before:,}, after={n_empty_original_after:,}"
        )
    print()


def build_truncated_df(
    source_csv: Path = INPUT_CSV,
) -> tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    df = pd.read_csv(source_csv)
    if "original_text" not in df.columns or "mirrored_text" not in df.columns:
        raise ValueError(
            f"Expected `original_text` and `mirrored_text` columns in {source_csv}"
        )

    original_before = df["original_text"].fillna("").astype(str)
    mirrored_before = df["mirrored_text"].fillna("").astype(str)

    truncated = df.copy()
    truncated["original_text"] = original_before.map(
        lambda text: truncate_at_last_sentence(text, MAX_ORIGINAL_CHARS)
    )
    truncated["mirrored_text"] = mirrored_before.map(
        lambda text: truncate_at_last_sentence(text, MAX_MIRRORED_CHARS)
    )

    is_truncated = (truncated["original_text"] != original_before) | (
        truncated["mirrored_text"] != mirrored_before
    )
    return (
        truncated,
        is_truncated,
        _char_lengths(original_before),
        _char_lengths(mirrored_before),
    )


def _write_output(
    truncated: pd.DataFrame,
    is_truncated: pd.Series,
    output_path: Path,
    *,
    include_truncated_flag: bool,
) -> None:
    output = truncated.copy()
    if include_truncated_flag:
        output["is_truncated"] = is_truncated
    output.to_csv(output_path, index=False)


@app.command()
def main(
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Write a single output CSV instead of the default pair of files.",
    ),
    include_truncated_flag: bool = typer.Option(
        False,
        "--include-truncated-flag",
        help="Include the is_truncated column in written CSV(s).",
    ),
) -> None:
    truncated, is_truncated, original_lengths_before, mirrored_lengths_before = (
        build_truncated_df()
    )

    original_lengths_after = _char_lengths(truncated["original_text"])
    mirrored_lengths_after = _char_lengths(truncated["mirrored_text"])
    n_truncated = int(is_truncated.sum())
    n_posts = len(truncated)

    if output is not None:
        output_paths = [(output, include_truncated_flag)]
    else:
        output_paths = [
            (OUTPUT_CSV, False),
            (OUTPUT_WITH_FLAG_CSV, True),
        ]

    print(f"Input CSV: {INPUT_CSV}")
    print(f"Truncation limits: original={MAX_ORIGINAL_CHARS}, mirrored={MAX_MIRRORED_CHARS}")
    print(f"Rows truncated (is_truncated=True): {n_truncated:,} ({n_truncated / n_posts:.1%})")
    print()
    for output_path, with_flag in output_paths:
        _write_output(
            truncated,
            is_truncated,
            output_path,
            include_truncated_flag=with_flag,
        )
        flag_note = "with is_truncated" if with_flag else "without is_truncated"
        print(f"Wrote {output_path} ({flag_note})")
    print()

    _print_metrics(
        label="All posts:",
        n_posts=n_posts,
        original_lengths_before=original_lengths_before,
        mirrored_lengths_before=mirrored_lengths_before,
        original_lengths_after=original_lengths_after,
        mirrored_lengths_after=mirrored_lengths_after,
    )

    truncated_mask = is_truncated
    _print_metrics(
        label="Truncated posts only (is_truncated=True):",
        n_posts=n_truncated,
        original_lengths_before=original_lengths_before[truncated_mask],
        mirrored_lengths_before=mirrored_lengths_before[truncated_mask],
        original_lengths_after=original_lengths_after[truncated_mask],
        mirrored_lengths_after=mirrored_lengths_after[truncated_mask],
    )


if __name__ == "__main__":
    app()
