"""Run flip generation on the pinned filtered stimulus sample.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/generate_flips_2026_09_08/run.py --help
"""

from __future__ import annotations

import sys

import typer

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.generate_flips_2026_09_08.load_filtered_dataset import (
    load_filtered_dataset,
)
from experiments.generate_flips_2026_09_08.sources import (
    OUTPUT_S3_BUCKET,
    pinned_filtered_source,
)
from lib.constants import REPO_ROOT

EXPERIMENT_DIR = REPO_ROOT / "experiments" / "generate_flips_2026_09_08"
DEFAULT_CACHE_DIR = EXPERIMENT_DIR / "cache"

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def main(
    run_id: str | None = typer.Option(None, "--run-id"),
    max_posts: int | None = typer.Option(None, "--max-posts"),
    bucket: str = typer.Option(OUTPUT_S3_BUCKET, "--bucket"),
) -> None:
    """Load the pinned filtered parquet and generate mirrored posts."""
    source = pinned_filtered_source()
    store = CampaignObjectStore(bucket)
    load_filtered_dataset(source, store, DEFAULT_CACHE_DIR)
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(app())
