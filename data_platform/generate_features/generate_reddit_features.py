"""Generate features for preprocessed Reddit comments.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/generate_reddit_features.py \\
        --dataset-id reddit_<uuid> --batch-size 64
"""

from __future__ import annotations

from pathlib import Path

import typer

from data_platform.generate_features.platform_cli import (
    FeaturePlatformSpec,
    build_feature_config,
    features_from_cli,
    generate_platform_features,
    load_preprocessed_records,
)
from data_platform.models.sync import PreprocessedRedditCommentModel
from data_platform.utils.platform_specific_columns import REDDIT_COLUMNS
from data_platform.utils.storage import RedditStorageManager

REDDIT_SPEC = FeaturePlatformSpec(
    platform="reddit",
    storage_cls=RedditStorageManager,
    model_cls=PreprocessedRedditCommentModel,
    columns=REDDIT_COLUMNS,
    empty_message="generate_reddit_features: no preprocessed comments found",
)


def reddit_feature_config(*args, **kwargs):
    return build_feature_config(REDDIT_SPEC, *args, **kwargs)


def load_comments(dataset_id: str):
    return load_preprocessed_records(REDDIT_SPEC, dataset_id)


def generate_reddit_features(
    dataset_id: str,
    *,
    batch_size: int = 64,
    max_concurrency: int = 80,
    feature_subset: list[str] | None = None,
    run_dir_name: str | None = None,
) -> dict[str, Path]:
    """Load Reddit comments and generate the requested feature labels."""
    return generate_platform_features(
        REDDIT_SPEC,
        dataset_id,
        batch_size=batch_size,
        max_concurrency=max_concurrency,
        feature_subset=feature_subset,
        run_dir_name=run_dir_name,
    )


def main(
    dataset_id: str = typer.Option(
        ...,
        "--dataset-id",
        help="Dataset identifier from ingestion YAML (reddit_<uuid>)",
    ),
    batch_size: int = typer.Option(64, "--batch-size"),
    max_concurrency: int = typer.Option(80, "--max-concurrency"),
    features: list[str] | None = typer.Option(
        None,
        "--features",
        help="Feature name(s); repeat the flag per feature, e.g. --features is_political",
    ),
    run_dir: str | None = typer.Option(
        None,
        "--run-dir",
        help="Feature run timestamp to resume (e.g. 2026_05_30-12:00:00)",
    ),
) -> None:
    """CLI entrypoint for resumable Reddit feature generation."""
    generate_reddit_features(
        dataset_id,
        batch_size=batch_size,
        max_concurrency=max_concurrency,
        feature_subset=features_from_cli(features),
        run_dir_name=run_dir,
    )


if __name__ == "__main__":
    typer.run(main)
