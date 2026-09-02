"""Generate features for preprocessed Bluesky posts.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/generate_bluesky_features.py \\
        --dataset-id bluesky_<uuid> --batch-size 64
"""

from __future__ import annotations

from pathlib import Path

import typer

from data_platform.generate_features.platform_cli import (
    FeaturePlatformSpec,
    features_from_cli,
    generate_platform_features,
)
from data_platform.models.sync import SyncBlueskyPostModel
from data_platform.utils.platform_specific_columns import BLUESKY_COLUMNS
from data_platform.utils.storage import BlueskyStorageManager

BLUESKY_SPEC = FeaturePlatformSpec(
    platform="bluesky",
    storage_cls=BlueskyStorageManager,
    model_cls=SyncBlueskyPostModel,
    columns=BLUESKY_COLUMNS,
    empty_message="generate_bluesky_features: no preprocessed posts found",
    require_all_runs_complete=True,
)


def generate_bluesky_features(
    dataset_id: str,
    *,
    batch_size: int = 64,
    max_concurrency: int = 80,
    feature_subset: list[str] | None = None,
) -> dict[str, Path]:
    """Load Bluesky posts and generate the requested feature labels."""
    return generate_platform_features(
        BLUESKY_SPEC,
        dataset_id,
        batch_size=batch_size,
        max_concurrency=max_concurrency,
        feature_subset=feature_subset,
    )


def main(
    dataset_id: str = typer.Option(
        ...,
        "--dataset-id",
        help="Dataset identifier from ingestion YAML (bluesky_<uuid>)",
    ),
    batch_size: int = typer.Option(64, "--batch-size"),
    max_concurrency: int = typer.Option(80, "--max-concurrency"),
    features: list[str] | None = typer.Option(
        None,
        "--features",
        help="Feature name(s); repeat the flag per feature, e.g. --features is_political",
    ),
) -> None:
    """CLI entrypoint for resumable Bluesky feature generation."""
    generate_bluesky_features(
        dataset_id,
        batch_size=batch_size,
        max_concurrency=max_concurrency,
        feature_subset=features_from_cli(features),
    )


if __name__ == "__main__":
    typer.run(main)
