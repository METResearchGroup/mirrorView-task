"""Deterministic ten-post smoke sample shared by every feature of a Bluesky campaign.

Run from the repo root to write the committed ids file:

    PYTHONPATH=. uv run python data_platform/generate_features/deterministic_smoke_sample.py \\
        --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \\
        --preprocessed-run 2026_09_03-23:51:30 \\
        --output docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/deterministic_ten_post_ids.json
"""

from __future__ import annotations

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


def select_deterministic_sample(
    records: pd.DataFrame, count: int = SMOKE_POST_COUNT
) -> pd.DataFrame:
    raise NotImplementedError


def load_deterministic_ten_posts(dataset_id: str, preprocessed_run: str) -> pd.DataFrame:
    raise NotImplementedError


def load_deterministic_ten_post_ids(dataset_id: str, preprocessed_run: str) -> list[str]:
    raise NotImplementedError


def write_deterministic_ten_post_ids(
    dataset_id: str, preprocessed_run: str, output: Path
) -> Path:
    raise NotImplementedError


def main(
    dataset_id: str = typer.Option(..., "--dataset-id"),
    preprocessed_run: str = typer.Option(..., "--preprocessed-run"),
    output: Path = typer.Option(..., "--output"),
) -> None:
    raise NotImplementedError


if __name__ == "__main__":
    typer.run(main)
