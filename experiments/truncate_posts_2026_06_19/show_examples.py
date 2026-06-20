from __future__ import annotations

"""
Sample rows from a versioned flips.csv for manual review.

Run from repo root:

PYTHONPATH=. uv run python experiments/truncate_posts_2026_06_19/show_examples.py --version v3
PYTHONPATH=. uv run python experiments/truncate_posts_2026_06_19/show_examples.py --version v3 --sample-size 50
"""

from pathlib import Path

import pandas as pd
import typer

from experiments.truncate_posts_2026_06_19.paths import (
    ensure_version_dir,
    flips_csv,
    parse_version,
    sample_flips_csv,
)

RANDOM_SEED = 42

app = typer.Typer(add_completion=False)


def sample_flips(
    input_csv: Path,
    output_csv: Path,
    *,
    sample_size: int,
    random_state: int = RANDOM_SEED,
) -> pd.DataFrame:
    df = pd.read_csv(input_csv)
    if len(df) < sample_size:
        raise ValueError(
            f"Only {len(df)} posts available in {input_csv}; need {sample_size}."
        )

    sampled = df.sample(n=sample_size, random_state=random_state).reset_index(drop=True)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    sampled.to_csv(output_csv, index=False)
    return sampled


@app.command()
def main(
    version: str = typer.Option(
        "v3",
        "--version",
        "-v",
        help="Truncation version: v1, v2, v3, truncation_v1, truncation_v2, or truncation_v3.",
    ),
    sample_size: int = typer.Option(
        125,
        "--sample-size",
        "-n",
        min=1,
        help="Number of posts to sample from flips.csv.",
    ),
) -> None:
    parsed = parse_version(version)
    ensure_version_dir(parsed)
    input_csv = flips_csv(parsed)
    output_csv = sample_flips_csv(parsed)

    sampled = sample_flips(
        input_csv,
        output_csv,
        sample_size=sample_size,
    )

    print(f"Version: {parsed.value}")
    print(f"Input CSV: {input_csv}")
    print(f"Wrote {len(sampled)} posts to {output_csv}")


if __name__ == "__main__":
    app()
