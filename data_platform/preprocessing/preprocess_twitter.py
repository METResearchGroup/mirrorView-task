"""Preprocess Twitter posts from raw CSV storage to filtered preprocessed output.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/preprocessing/preprocess_twitter.py \\
        --dataset-id twitter_<uuid>
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import typer

from data_platform.models.sync import SyncTwitterPostModel
from data_platform.preprocessing.runner import (
    PreprocessPlatformSpec,
    TextValidator,
)
from data_platform.preprocessing.runner import (
    passes_all_validators as _passes_all_validators,
)
from data_platform.preprocessing.runner import (
    preprocess_records as run_preprocess_records,
)
from data_platform.preprocessing.truncate_long_text import truncate_long_text
from data_platform.preprocessing.validators.twitter_validators import (
    check_if_twitter_text_has_no_external_urls,
    check_if_valid_twitter_post_length,
    strip_tco_links,
)
from data_platform.preprocessing.validators.validators import (
    check_if_not_phone,
    check_if_text_english,
)
from data_platform.utils.platform_specific_columns import TWITTER_COLUMNS
from data_platform.utils.storage import TwitterStorageManager

POST_TEXT_VALIDATORS: tuple[TextValidator, ...] = (
    check_if_not_phone,
    check_if_valid_twitter_post_length,
    check_if_twitter_text_has_no_external_urls,
    check_if_text_english,
)

TWITTER_SPEC = PreprocessPlatformSpec(
    platform="twitter",
    storage_cls=TwitterStorageManager,
    model_cls=SyncTwitterPostModel,
    columns=TWITTER_COLUMNS,
    text_validators=POST_TEXT_VALIDATORS,
    text_transforms=(strip_tco_links, truncate_long_text),
    author_handle_source_column="username",
)


def passes_all_validators(
    text: str,
    validators: Sequence[TextValidator] = POST_TEXT_VALIDATORS,
) -> bool:
    return _passes_all_validators(text, validators)


def preprocess_records(dataset_id: str) -> Path:
    return run_preprocess_records(dataset_id, TWITTER_SPEC)


def main(
    dataset_id: str = typer.Option(
        ...,
        "--dataset-id",
        help="Dataset identifier from ingestion YAML (twitter_<uuid>)",
    ),
) -> None:
    preprocess_records(dataset_id)


if __name__ == "__main__":
    typer.run(main)
