"""Run flip generation on the pinned unified 2,300 post upsample.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/generate_flips_for_upsampled_posts_2026_09_08/run.py --help
"""

from __future__ import annotations

import sys

import typer

from experiments.generate_flips_for_upsampled_posts_2026_09_08.load_unified_dataset import (
    load_unified_dataset,
)
from experiments.generate_flips_for_upsampled_posts_2026_09_08.sources import (
    pinned_unified_source,
)

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def main(
    run_id: str = typer.Option("", "--run-id"),
    max_posts: int | None = typer.Option(None, "--max-posts"),
    bucket: str = typer.Option("", "--bucket"),
) -> None:
    """Load the pinned unified parquet and generate mirrored posts."""
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(app())
