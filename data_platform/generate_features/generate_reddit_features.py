"""Generate features for preprocessed Reddit comments.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/generate_reddit_features.py \\
        --dataset-id reddit_<uuid> --batch-size 64

    PYTHONPATH=. uv run python data_platform/generate_features/generate_reddit_features.py \\
        --dataset-id reddit_<uuid> --checkpoint 2026_05_30-12:00:00
"""

from __future__ import annotations

from pathlib import Path

import typer

from data_platform.generate_features.platform_cli import (
    FeaturePlatformSpec,
    build_feature_cli_app,
    build_feature_cli_main,
    build_feature_config,
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

_DATASET_ID_HELP = "Dataset identifier from ingestion YAML (reddit_<uuid>)"
app = build_feature_cli_app(REDDIT_SPEC, _DATASET_ID_HELP)
main = build_feature_cli_main(REDDIT_SPEC, _DATASET_ID_HELP)


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
    checkpoint: str | None = None,
) -> dict[str, Path]:
    """Generate Reddit feature labels in a new or unfinished feature run.

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
        REDDIT_SPEC,
        dataset_id,
        batch_size=batch_size,
        max_concurrency=max_concurrency,
        feature_subset=feature_subset,
        checkpoint=checkpoint,
    )


if __name__ == "__main__":
    typer.run(main)
