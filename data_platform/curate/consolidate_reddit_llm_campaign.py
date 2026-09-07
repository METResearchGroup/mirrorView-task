"""Join pinned Reddit comments with seven campaign LLM feature files into one wide Parquet object.

Runtime validation (automated tests are forbidden by Step 11):

given seven feature manifests whose final.parquet SHA-256 and row_count are 400000
when the CLI joins pinned comments on source_record_id
then stdout includes each accepted manifest digest, wide_rows=400000, wide_columns=16,
     sort_key=source_record_id ASC, and the wide manifest URI

given a missing or SHA-mismatched feature final.parquet
when the CLI verifies inputs
then it raises before writing wide/features.parquet

given the uploaded wide parquet
when DuckDB describes columns and counts distinct source_record_id
then columns match the sixteen-name contract, n=uniq=400000, and no llm_toxicity_tier is null

given the same wide table and data_platform/curate/configs/reddit/mirrorview.yaml
when apply_rules runs
then curated row count and political_stance x llm_toxicity_tier counts are written
     under the dataset curated/ stage, in a timestamped run directory

Run from the repo root:

    PYTHONPATH=. python data_platform/curate/consolidate_reddit_llm_campaign.py \\
        --dataset-id reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079 \\
        --preprocessed-run 2026_09_03-23:39:28 \\
        --campaign-id reddit_2026_09_03_233928_llm_features_v1 \\
        --output-s3-uri s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/wide/features.parquet
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from data_platform.curate.consolidate import (
    LLM_CAMPAIGN_FEATURE_NAMES,
    REDDIT_EXPECTED_WIDE_ROW_COUNT,
    REDDIT_PREPROCESSED_WIDE_COLUMNS,
    WIDE_SORT_KEY,
    build_reddit_llm_campaign_wide_table,
    reddit_llm_campaign_wide_columns,
)


def parse_args(argv: list[str] | None = None):
    raise NotImplementedError


def verify_feature_manifest(store, feature_name: str, campaign_id: str, dataset_id: str):
    raise NotImplementedError


def download_campaign_inputs(store, args, work_dir: Path):
    raise NotImplementedError


def validate_wide_table(wide) -> None:
    raise NotImplementedError


def curate_mirrorview_dataset(store, wide, args):
    raise NotImplementedError


def upload_wide_artifacts(store, wide, args, preprocessed, feature_inputs, curated):
    raise NotImplementedError


def run_campaign_consolidation(args):
    raise NotImplementedError


def print_result(result) -> None:
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run_campaign_consolidation(args)
    print_result(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
