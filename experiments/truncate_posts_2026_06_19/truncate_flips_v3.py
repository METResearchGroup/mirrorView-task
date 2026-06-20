from __future__ import annotations

"""
Truncate original and mirrored posts with sentence-first v3 logic.

Run from repo root:

PYTHONPATH=. uv run python experiments/truncate_posts_2026_06_19/truncate_flips_v3.py
"""

from pathlib import Path

import pandas as pd
import typer

from experiments.truncate_posts_2026_06_19.truncation_v3 import (
    MAX_CHARS,
    SENTENCE_OVERFLOW,
    is_complete_sentence,
    truncate_pair,
)
from experiments.truncate_posts_2026_06_19.truncate_flips import (
    INPUT_CSV,
    STANCE_ORDER,
    _char_lengths,
    _print_metrics,
    _print_metrics_by_stance,
    _write_output,
)
from experiments.truncate_posts_2026_06_19.truncate_flips_v2 import (
    _catastrophic_truncation_count,
)
from experiments.truncate_posts_2026_06_19.paths import (
    TruncationVersion,
    ensure_version_dir,
    flips_csv,
    flips_with_flag_csv,
)

TRUNCATION_VERSION = TruncationVersion.v3
OUTPUT_CSV = flips_csv(TRUNCATION_VERSION)
OUTPUT_WITH_FLAG_CSV = flips_with_flag_csv(TRUNCATION_VERSION)

app = typer.Typer(add_completion=False)


def _complete_sentence_counts(
    original_after: pd.Series, mirrored_after: pd.Series
) -> tuple[int, int]:
    orig_complete = int(
        original_after.fillna("").astype(str).map(is_complete_sentence).sum()
    )
    mirr_complete = int(
        mirrored_after.fillna("").astype(str).map(is_complete_sentence).sum()
    )
    return orig_complete, mirr_complete


def build_truncated_df_v3(
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
    truncated_pairs = [
        truncate_pair(original, mirror, MAX_CHARS, sentence_overflow=SENTENCE_OVERFLOW)
        for original, mirror in zip(original_before, mirrored_before, strict=True)
    ]
    truncated["original_text"] = [pair[0] for pair in truncated_pairs]
    truncated["mirrored_text"] = [pair[1] for pair in truncated_pairs]

    is_truncated = (truncated["original_text"] != original_before) | (
        truncated["mirrored_text"] != mirrored_before
    )
    return (
        truncated,
        is_truncated,
        _char_lengths(original_before),
        _char_lengths(mirrored_before),
    )


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
        build_truncated_df_v3()
    )

    original_lengths_after = _char_lengths(truncated["original_text"])
    mirrored_lengths_after = _char_lengths(truncated["mirrored_text"])
    n_truncated = int(is_truncated.sum())
    n_posts = len(truncated)

    if output is not None:
        output_paths = [(output, include_truncated_flag)]
    else:
        ensure_version_dir(TRUNCATION_VERSION)
        output_paths = [
            (OUTPUT_CSV, False),
            (OUTPUT_WITH_FLAG_CSV, True),
        ]

    print(f"Input CSV: {INPUT_CSV}")
    print(
        f"Truncation strategy: v3 sentence-first "
        f"(max_chars={MAX_CHARS}, sentence_overflow={SENTENCE_OVERFLOW}, independent sides)"
    )
    print(f"Rows truncated (is_truncated=True): {n_truncated:,} ({n_truncated / n_posts:.1%})")

    orig_catastrophic, mirr_catastrophic = _catastrophic_truncation_count(
        original_lengths_before,
        mirrored_lengths_before,
        original_lengths_after,
        mirrored_lengths_after,
        max_chars=MAX_CHARS,
    )
    orig_complete, mirr_complete = _complete_sentence_counts(
        truncated["original_text"], truncated["mirrored_text"]
    )
    exact_length_matches = int((original_lengths_after == mirrored_lengths_after).sum())
    print(
        f"Complete sentences: original={orig_complete:,} ({orig_complete / n_posts:.1%}), "
        f"mirrored={mirr_complete:,} ({mirr_complete / n_posts:.1%})"
    )
    print(
        f"Catastrophic truncations (<30% of cap): "
        f"original={orig_catastrophic:,}, mirrored={mirr_catastrophic:,}"
    )
    print(
        f"Exact char-length matches (original == mirrored): "
        f"{exact_length_matches:,} ({exact_length_matches / n_posts:.1%})"
    )
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

    all_posts_mask = pd.Series(True, index=truncated.index)
    _print_metrics_by_stance(
        label="All posts by political lean (sampled_stance):",
        stance=truncated["sampled_stance"],
        mask=all_posts_mask,
        original_lengths_before=original_lengths_before,
        mirrored_lengths_before=mirrored_lengths_before,
        original_lengths_after=original_lengths_after,
        mirrored_lengths_after=mirrored_lengths_after,
    )

    _print_metrics_by_stance(
        label="Truncated posts only by political lean (sampled_stance):",
        stance=truncated["sampled_stance"],
        mask=is_truncated,
        original_lengths_before=original_lengths_before,
        mirrored_lengths_before=mirrored_lengths_before,
        original_lengths_after=original_lengths_after,
        mirrored_lengths_after=mirrored_lengths_after,
    )


if __name__ == "__main__":
    app()
