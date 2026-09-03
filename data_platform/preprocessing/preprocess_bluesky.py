"""Preprocess Bluesky posts from raw CSV storage to filtered preprocessed output.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/preprocessing/preprocess_bluesky.py \\
        --dataset-id bluesky_<uuid>

    PYTHONPATH=. uv run python data_platform/preprocessing/preprocess_bluesky.py \\
        --config data_platform/preprocessing/configs/bluesky/jetstream_dump.yaml
"""

from __future__ import annotations

from pathlib import Path

import typer

from data_platform.models.sync import SyncBlueskyPostModel
from data_platform.preprocessing.runner import (
    PreprocessPlatformSpec,
    TextValidator,
)
from data_platform.preprocessing.runner import (
    preprocess_records as run_preprocess_records,
)
from data_platform.preprocessing.validators.bluesky_validators import (
    check_if_valid_post_length,
)
from data_platform.preprocessing.validators.validators import (
    check_if_not_phone,
    check_if_post_has_no_urls,
    check_if_text_english,
)
from data_platform.utils.platform_specific_columns import BLUESKY_COLUMNS
from data_platform.utils.storage import BlueskyStorageManager

POST_TEXT_VALIDATORS: tuple[TextValidator, ...] = (
    check_if_not_phone,
    check_if_valid_post_length,
    check_if_post_has_no_urls,
    check_if_text_english,
)

BLUESKY_SPEC = PreprocessPlatformSpec(
    platform="bluesky",
    storage_cls=BlueskyStorageManager,
    model_cls=SyncBlueskyPostModel,
    columns=BLUESKY_COLUMNS,
    text_validators=POST_TEXT_VALIDATORS,
    author_handle_source_column="author_handle",
)


def preprocess_records(
    dataset_id: str,
    sample_size: int | None = None,
    sample_seed: int | None = None,
) -> Path:
    """Run Bluesky preprocess, optionally sampling kept rows before write.

    Parameters
    ----------
    dataset_id
        Dataset identifier from ingestion or dump YAML.
    sample_size
        Maximum kept rows to write. ``None`` writes every kept row.
    sample_seed
        Seed used when ``sample_size`` is set.

    Returns
    -------
    pathlib.Path
        Path to the new preprocessed run directory.
    """
    return run_preprocess_records(
        dataset_id,
        BLUESKY_SPEC,
        sample_size,
        sample_seed,
    )


def main(
    dataset_id: str | None = typer.Option(
        None,
        "--dataset-id",
        help="Dataset identifier from ingestion YAML (bluesky_<uuid>)",
    ),
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Dump or preprocess YAML with dataset_id and sample settings",
    ),
    sample_size: int | None = typer.Option(
        None,
        "--sample-size",
        help="Override YAML sample size; omit to write every kept row",
    ),
    sample_seed: int | None = typer.Option(
        None,
        "--sample-seed",
        help="Override YAML sample seed; required when sampling",
    ),
) -> None:
    preprocess_records(dataset_id or "", sample_size, sample_seed)


if __name__ == "__main__":
    typer.run(main)
