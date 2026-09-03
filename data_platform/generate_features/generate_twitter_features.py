"""Generate features for preprocessed Twitter posts.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/generate_twitter_features.py \\
        --dataset-id twitter_<uuid> --batch-size 64

    PYTHONPATH=. uv run python data_platform/generate_features/generate_twitter_features.py \\
        --dataset-id twitter_<uuid> --checkpoint 2026_05_30-12:00:00
"""

from __future__ import annotations

from pathlib import Path

from data_platform.generate_features.platform_cli import (
    FeaturePlatformSpec,
    build_feature_cli_app,
    build_feature_config,
    generate_platform_features,
    load_preprocessed_records,
)
from data_platform.models.sync import PreprocessedTwitterPostModel
from data_platform.utils.platform_specific_columns import TWITTER_COLUMNS
from data_platform.utils.storage import TwitterStorageManager

TWITTER_SPEC = FeaturePlatformSpec(
    platform="twitter",
    storage_cls=TwitterStorageManager,
    model_cls=PreprocessedTwitterPostModel,
    columns=TWITTER_COLUMNS,
    empty_message="generate_twitter_features: no preprocessed posts found",
)

app = build_feature_cli_app(
    TWITTER_SPEC,
    "Dataset identifier from ingestion YAML (twitter_<uuid>)",
)


def twitter_feature_config(*args, **kwargs):
    return build_feature_config(TWITTER_SPEC, *args, **kwargs)


def load_posts(dataset_id: str):
    return load_preprocessed_records(TWITTER_SPEC, dataset_id)


def generate_twitter_features(
    dataset_id: str,
    *,
    batch_size: int = 64,
    max_concurrency: int = 80,
    feature_subset: list[str] | None = None,
    checkpoint: str | None = None,
) -> dict[str, Path]:
    """Generate Twitter feature labels in a new or unfinished feature run.

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
    checkpoint
        Named unfinished feature run timestamp. Pass None to start a new
        feature run.

    Returns
    -------
    dict[str, Path]
        Feature name to the label file written in the feature run folder.
    """
    return generate_platform_features(
        TWITTER_SPEC,
        dataset_id,
        batch_size=batch_size,
        max_concurrency=max_concurrency,
        feature_subset=feature_subset,
        checkpoint=checkpoint,
    )


def main() -> None:
    """CLI entrypoint for Twitter feature generation."""
    app()


if __name__ == "__main__":
    main()
