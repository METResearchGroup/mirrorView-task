"""Generate features for preprocessed Reddit comments.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/generate_reddit_features.py \\
        new-run --dataset-id reddit_<uuid> --batch-size 64

    PYTHONPATH=. uv run python data_platform/generate_features/generate_reddit_features.py \\
        resume --dataset-id reddit_<uuid> --checkpoint 2026_05_30-12:00:00

    PYTHONPATH=. uv run python data_platform/generate_features/generate_reddit_features.py \\
        resume --dataset-id reddit_<uuid> --latest
"""

from __future__ import annotations

from pathlib import Path

from data_platform.generate_features.platform_cli import (
    FeaturePlatformSpec,
    build_feature_cli_app,
    build_feature_config,
    generate_platform_features,
    generate_platform_features_from_checkpoint,
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

app = build_feature_cli_app(
    REDDIT_SPEC,
    "Dataset identifier from ingestion YAML (reddit_<uuid>)",
)


def reddit_feature_config(*args, **kwargs):
    return build_feature_config(REDDIT_SPEC, *args, **kwargs)


def load_comments(dataset_id: str):
    return load_preprocessed_records(REDDIT_SPEC, dataset_id)


def generate_reddit_features(
    dataset_id: str,
    batch_size: int = 64,
    max_concurrency: int = 80,
    feature_subset: list[str] | None = None,
) -> dict[str, Path]:
    """Start a new Reddit feature run and generate the requested labels.

    Parameters
    ----------
    dataset_id
        Dataset identifier from ingestion YAML.
    batch_size
        Label batch size.
    max_concurrency
        Engine concurrency cap.
    feature_subset
        Optional registry subset. None runs every feature.

    Returns
    -------
    dict[str, Path]
        Feature name to the label file written in the new folder.
    """
    return generate_platform_features(
        REDDIT_SPEC,
        dataset_id,
        batch_size=batch_size,
        max_concurrency=max_concurrency,
        feature_subset=feature_subset,
    )


def generate_reddit_features_from_checkpoint(
    dataset_id: str,
    checkpoint: str,
    batch_size: int = 64,
    max_concurrency: int = 80,
    feature_subset: list[str] | None = None,
) -> dict[str, Path]:
    """Resume an unfinished Reddit feature run.

    Parameters
    ----------
    dataset_id
        Dataset identifier from ingestion YAML.
    checkpoint
        Named unfinished feature run timestamp.
    batch_size
        Label batch size.
    max_concurrency
        Engine concurrency cap.
    feature_subset
        Optional registry subset. None runs every feature.

    Returns
    -------
    dict[str, Path]
        Feature name to the label file written in the resumed folder.
    """
    return generate_platform_features_from_checkpoint(
        REDDIT_SPEC,
        dataset_id,
        checkpoint,
        batch_size=batch_size,
        max_concurrency=max_concurrency,
        feature_subset=feature_subset,
    )


def main() -> None:
    """CLI entrypoint. Requires new-run or resume."""
    app()


if __name__ == "__main__":
    main()
