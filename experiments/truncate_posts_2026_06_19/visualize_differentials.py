from __future__ import annotations

"""
Plot histogram of mirrored-minus-original char length differentials.

Run from repo root:

PYTHONPATH=. uv run python experiments/truncate_posts_2026_06_19/visualize_differentials.py --version v2
PYTHONPATH=. uv run python experiments/truncate_posts_2026_06_19/visualize_differentials.py --version v1
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import typer

from experiments.truncate_posts_2026_06_19.paths import (
    TruncationVersion,
    differentials_png,
    ensure_version_dir,
    flips_csv,
    parse_version,
)

app = typer.Typer(add_completion=False)


def plot_differentials(
    input_csv: Path,
    output_png: Path,
    *,
    version_label: str,
) -> float:
    df = pd.read_csv(input_csv)
    if "original_text" not in df.columns or "mirrored_text" not in df.columns:
        raise ValueError(
            f"Expected `original_text` and `mirrored_text` columns in {input_csv}"
        )

    original_lengths = df["original_text"].fillna("").astype(str).str.len()
    mirrored_lengths = df["mirrored_text"].fillna("").astype(str).str.len()
    differentials = mirrored_lengths - original_lengths
    mean_differential = differentials.mean()

    ensure_version_dir(TruncationVersion(version_label))
    plt.figure(figsize=(9, 6))
    plt.hist(differentials, bins=50, color="steelblue", edgecolor="white", alpha=0.85)
    plt.axvline(
        mean_differential,
        color="red",
        linestyle="--",
        linewidth=2,
        label=f"Mean differential ({mean_differential:.1f} chars)",
    )
    plt.axvline(0, color="black", linestyle="-", linewidth=1, alpha=0.4)
    plt.xlabel("Mirrored length − original length (chars)")
    plt.ylabel("Number of posts")
    plt.title(f"Char length differential: mirrored vs original ({version_label})")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_png, dpi=160)
    plt.close()
    return float(mean_differential)


@app.command()
def main(
    version: str = typer.Option(
        "v3",
        "--version",
        "-v",
        help="Truncation version: v1, v2, truncation_v1, or truncation_v2.",
    ),
) -> None:
    parsed = parse_version(version)
    input_csv = flips_csv(parsed)
    output_png = differentials_png(parsed)
    mean_differential = plot_differentials(
        input_csv,
        output_png,
        version_label=parsed.value,
    )

    print(f"Version: {parsed.value}")
    print(f"Input CSV: {input_csv}")
    print(f"Wrote {output_png}")
    print(f"Mean differential: {mean_differential:.1f} chars")


if __name__ == "__main__":
    app()
