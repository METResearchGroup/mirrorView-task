"""Deterministic ten-row smoke sample shared by every feature of a campaign.

Run from the repo root to write the committed Reddit ids file:

    PYTHONPATH=. uv run python data_platform/generate_features/deterministic_smoke_sample.py \\
        --platform reddit \\
        --dataset-id reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079 \\
        --preprocessed-run 2026_09_03-23:39:28 \\
        --output docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/deterministic_ten_comment_ids.json
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import typer

from data_platform.generate_features.generate_bluesky_features import BLUESKY_SPEC
from data_platform.generate_features.platform_cli import (
    FeaturePlatformSpec,
    load_pinned_preprocessed_records,
)
from data_platform.utils.platform_specific_columns import (
    STANDARDIZED_SOURCE_RECORD_ID_COLUMN,
    STANDARDIZED_TEXT_COLUMN,
)

PLATFORM_BLUESKY = "bluesky"
PLATFORM_REDDIT = "reddit"

SMOKE_POST_COUNT = 10
SELECTION_RULE = (
    "Keep rows with non-empty text, sort by ascending source_record_id, take the first ten."
)
JSON_INDENT = 2


def select_deterministic_sample(
    records: pd.DataFrame, count: int = SMOKE_POST_COUNT
) -> pd.DataFrame:
    """Return the first ``count`` rows with non-empty text in ascending ``source_record_id`` order.

    The rule takes no feature as input, so every feature that labels the same
    preprocessed run labels the same rows.

    Raises
    ------
    ValueError
        When fewer than ``count`` rows have text.
    """
    text = records[STANDARDIZED_TEXT_COLUMN].fillna("").astype(str).str.strip()
    with_text = records[text != ""]
    if len(with_text) < count:
        raise ValueError(f"need {count} rows with text, found {len(with_text)}")
    ordered = with_text.sort_values(STANDARDIZED_SOURCE_RECORD_ID_COLUMN, kind="stable")
    return ordered.head(count).reset_index(drop=True)


def load_deterministic_ten_posts_for_spec(
    spec: FeaturePlatformSpec, dataset_id: str, preprocessed_run: str
) -> pd.DataFrame:
    """Load one pinned preprocessed run through ``spec`` and return its ten smoke rows.

    Parameters
    ----------
    spec
        Platform storage and column settings. Bluesky callers pass ``BLUESKY_SPEC``.
        Reddit callers pass ``REDDIT_SPEC``.
    dataset_id
        Dataset folder name under the platform's preprocessed tree.
    preprocessed_run
        Single preprocessed run directory name.
    """
    records = load_pinned_preprocessed_records(spec, dataset_id, preprocessed_run)
    return select_deterministic_sample(records)


def load_deterministic_ten_post_ids_for_spec(
    spec: FeaturePlatformSpec, dataset_id: str, preprocessed_run: str
) -> list[str]:
    """Return the ten smoke ``source_record_id`` values for ``spec`` in ascending order."""
    posts = load_deterministic_ten_posts_for_spec(spec, dataset_id, preprocessed_run)
    return posts[STANDARDIZED_SOURCE_RECORD_ID_COLUMN].astype(str).tolist()


def write_deterministic_ten_post_ids_for_spec(
    spec: FeaturePlatformSpec, dataset_id: str, preprocessed_run: str, output: Path
) -> Path:
    """Write the ten ids for ``spec`` with the dataset, run, and selection rule as JSON."""
    document = {
        "dataset_id": dataset_id,
        "preprocessed_run": preprocessed_run,
        "selection_rule": SELECTION_RULE,
        "source_record_ids": load_deterministic_ten_post_ids_for_spec(
            spec, dataset_id, preprocessed_run
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(f"{json.dumps(document, indent=JSON_INDENT)}\n", encoding="utf-8")
    return output


def load_deterministic_ten_posts(
    dataset_id: str,
    preprocessed_run: str,
    spec: FeaturePlatformSpec | None = None,
) -> pd.DataFrame:
    """Load the pinned preprocessed run and return its ten smoke rows with every column.

    ``spec`` selects the platform storage. None keeps the Bluesky spec so
    existing Bluesky callers stay valid. Twitter passes ``TWITTER_SPEC``.
    """
    return load_deterministic_ten_posts_for_spec(
        spec or BLUESKY_SPEC, dataset_id, preprocessed_run
    )


def load_deterministic_ten_post_ids(dataset_id: str, preprocessed_run: str) -> list[str]:
    """Return the ten Bluesky smoke ``source_record_id`` values in ascending order."""
    return load_deterministic_ten_post_ids_for_spec(BLUESKY_SPEC, dataset_id, preprocessed_run)


def write_deterministic_ten_post_ids(
    dataset_id: str, preprocessed_run: str, output: Path
) -> Path:
    """Write the ten Bluesky ids with the dataset, run, and selection rule as JSON and return ``output``."""
    return write_deterministic_ten_post_ids_for_spec(
        BLUESKY_SPEC, dataset_id, preprocessed_run, output
    )


def _spec_for_platform(platform: str) -> FeaturePlatformSpec:
    if platform == PLATFORM_BLUESKY:
        return BLUESKY_SPEC
    if platform == PLATFORM_REDDIT:
        from data_platform.generate_features.generate_reddit_features import REDDIT_SPEC

        return REDDIT_SPEC
    raise typer.BadParameter(f"platform must be {PLATFORM_BLUESKY} or {PLATFORM_REDDIT}")


def main(
    dataset_id: str = typer.Option(..., "--dataset-id"),
    preprocessed_run: str = typer.Option(..., "--preprocessed-run"),
    output: Path = typer.Option(..., "--output"),
    platform: str = typer.Option(PLATFORM_BLUESKY, "--platform"),
) -> None:
    """Write the deterministic ten-row ids of one preprocessed run to a JSON file."""
    written = write_deterministic_ten_post_ids_for_spec(
        _spec_for_platform(platform), dataset_id, preprocessed_run, output
    )
    print(f"deterministic_ten_post_ids={written}")


if __name__ == "__main__":
    typer.run(main)
