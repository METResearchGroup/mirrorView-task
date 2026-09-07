"""Deterministic ten-post smoke sample shared by every feature of a Bluesky campaign.

Run from the repo root to write the committed ids file:

    PYTHONPATH=. uv run python data_platform/generate_features/deterministic_smoke_sample.py \\
        --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \\
        --preprocessed-run 2026_09_03-23:51:30 \\
        --output docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/deterministic_ten_post_ids.json
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import typer

from data_platform.generate_features.generate_bluesky_features import BLUESKY_SPEC
from data_platform.generate_features.platform_cli import load_pinned_preprocessed_records
from data_platform.utils.platform_specific_columns import (
    STANDARDIZED_SOURCE_RECORD_ID_COLUMN,
    STANDARDIZED_TEXT_COLUMN,
)

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


def load_deterministic_ten_posts(dataset_id: str, preprocessed_run: str) -> pd.DataFrame:
    """Load the pinned preprocessed run and return its ten smoke rows with every column."""
    records = load_pinned_preprocessed_records(BLUESKY_SPEC, dataset_id, preprocessed_run)
    return select_deterministic_sample(records)


def load_deterministic_ten_post_ids(dataset_id: str, preprocessed_run: str) -> list[str]:
    """Return the ten smoke ``source_record_id`` values in ascending order."""
    posts = load_deterministic_ten_posts(dataset_id, preprocessed_run)
    return posts[STANDARDIZED_SOURCE_RECORD_ID_COLUMN].astype(str).tolist()


def write_deterministic_ten_post_ids(
    dataset_id: str, preprocessed_run: str, output: Path
) -> Path:
    """Write the ten ids with the dataset, run, and selection rule as JSON and return ``output``."""
    document = {
        "dataset_id": dataset_id,
        "preprocessed_run": preprocessed_run,
        "selection_rule": SELECTION_RULE,
        "source_record_ids": load_deterministic_ten_post_ids(dataset_id, preprocessed_run),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(f"{json.dumps(document, indent=JSON_INDENT)}\n", encoding="utf-8")
    return output


def main(
    dataset_id: str = typer.Option(..., "--dataset-id"),
    preprocessed_run: str = typer.Option(..., "--preprocessed-run"),
    output: Path = typer.Option(..., "--output"),
) -> None:
    """Write the deterministic ten-post ids of one preprocessed run to a JSON file."""
    written = write_deterministic_ten_post_ids(dataset_id, preprocessed_run, output)
    print(f"deterministic_ten_post_ids={written}")


if __name__ == "__main__":
    typer.run(main)
