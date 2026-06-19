from __future__ import annotations

"""
Export posts with the largest absolute mirrored-minus-original char length gaps.

Useful for inspecting truncation and mirror-generation cases where original and
mirrored text lengths diverge most, even after sentence-aware truncation.

Run from repo root:

PYTHONPATH=. uv run python experiments/truncate_posts_2026_06_19/highest_absolute_differentials_posts.py --version v2
PYTHONPATH=. uv run python experiments/truncate_posts_2026_06_19/highest_absolute_differentials_posts.py --version v2 --top-n 50
"""

from pathlib import Path

import pandas as pd
import typer

from experiments.truncate_posts_2026_06_19.paths import (
    ensure_version_dir,
    flips_csv,
    highest_absolute_differential_csv,
    parse_version,
)

app = typer.Typer(add_completion=False)


def export_highest_absolute_differentials(
    input_csv: Path,
    output_csv: Path,
    *,
    top_n: int,
) -> pd.DataFrame:
    df = pd.read_csv(input_csv)
    if "original_text" not in df.columns or "mirrored_text" not in df.columns:
        raise ValueError(
            f"Expected `original_text` and `mirrored_text` columns in {input_csv}"
        )

    original_lengths = df["original_text"].fillna("").astype(str).str.len()
    mirrored_lengths = df["mirrored_text"].fillna("").astype(str).str.len()
    char_differential = mirrored_lengths - original_lengths

    ranked = df.copy()
    ranked["original_char_count"] = original_lengths
    ranked["mirrored_char_count"] = mirrored_lengths
    ranked["char_differential"] = char_differential
    ranked["absolute_char_differential"] = char_differential.abs()
    ranked = ranked.sort_values(
        "absolute_char_differential", ascending=False
    ).head(top_n)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    ranked.to_csv(output_csv, index=False)
    return ranked


@app.command()
def main(
    version: str = typer.Option(
        "v3",
        "--version",
        "-v",
        help="Truncation version: v1, v2, truncation_v1, or truncation_v2.",
    ),
    top_n: int = typer.Option(
        20,
        "--top-n",
        "-n",
        min=1,
        help="Number of posts with the largest absolute char differential to export.",
    ),
) -> None:
    parsed = parse_version(version)
    ensure_version_dir(parsed)
    input_csv = flips_csv(parsed)
    output_csv = highest_absolute_differential_csv(parsed)

    ranked = export_highest_absolute_differentials(
        input_csv,
        output_csv,
        top_n=top_n,
    )

    print(f"Version: {parsed.value}")
    print(f"Input CSV: {input_csv}")
    print(f"Wrote {len(ranked)} posts to {output_csv}")
    print(
        "Absolute char differential range: "
        f"{ranked['absolute_char_differential'].max():.0f} "
        f"(max) to {ranked['absolute_char_differential'].min():.0f} (min in export)"
    )


if __name__ == "__main__":
    app()
