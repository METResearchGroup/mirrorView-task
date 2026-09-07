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
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from data_platform.curate.apply_rules import FilterStepResult
from data_platform.curate.consolidate import (
    LLM_CAMPAIGN_FEATURE_NAMES,
    REDDIT_EXPECTED_WIDE_ROW_COUNT,
    REDDIT_PREPROCESSED_WIDE_COLUMNS,
    WIDE_SORT_KEY,
    build_reddit_llm_campaign_wide_table,
    reddit_llm_campaign_wide_columns,
)
from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore


MIRRORVIEW_RULES_PATH = (
    Path(__file__).resolve().parent / "configs" / "reddit" / "mirrorview.yaml"
)
WIDE_MANIFEST_FILENAME = "manifest.json"
WIDE_PARQUET_FILENAME = "features.parquet"
REDDIT_CAMPAIGN_PLATFORM = "reddit"
PREPROCESSED_COMMENTS_FILENAME = "comments.parquet"
STANCE_CROSSTAB_ROWS = ("left", "right")
TOXICITY_CROSSTAB_COLUMNS = ("low", "medium", "high")
FORBIDDEN_WIDE_COLUMNS = frozenset(
    {
        "toxicity_prob",
        "toxicity_tier",
        "label_timestamp",
        "run_id",
        "is_toxic_tiered",
    }
)


@dataclass(frozen=True)
class CampaignConsolidateArgs:
    """CLI inputs for the Reddit LLM campaign wide join."""

    dataset_id: str
    preprocessed_run: str
    campaign_id: str
    output_s3_uri: str
    curate_config: Path


@dataclass(frozen=True)
class FeatureInputRecord:
    """Verified feature ``final.parquet`` and its manifest metadata."""

    feature_name: str
    final_key: str
    final_sha256: str
    final_row_count: int
    manifest_key: str
    manifest_sha256: str
    local_parquet: Path


@dataclass(frozen=True)
class PreprocessedInputRecord:
    """Pinned preprocessed comments used as the wide-join left table."""

    key: str
    sha256: str
    local_parquet: Path


@dataclass(frozen=True)
class CuratedDatasetRecord:
    """MirrorView-filtered rows plus stance by toxicity counts."""

    row_count: int
    parquet_key: str
    parquet_sha256: str
    metadata_key: str
    metadata_sha256: str
    rules_hash: str
    filter_steps: list[dict[str, Any]]
    stance_by_toxicity: dict[str, dict[str, int]]


@dataclass(frozen=True)
class WideConsolidateResult:
    """Uploaded wide Parquet, manifest, and optional curated export."""

    wide_rows: int
    wide_columns: tuple[str, ...]
    wide_parquet_uri: str
    wide_parquet_sha256: str
    manifest_uri: str
    sort_key: str
    feature_inputs: tuple[FeatureInputRecord, ...]
    preprocessed: PreprocessedInputRecord
    curated: CuratedDatasetRecord | None


def parse_args(argv: list[str] | None = None) -> CampaignConsolidateArgs:
    parser = argparse.ArgumentParser(
        description="Join seven Reddit LLM campaign features into one wide Parquet object."
    )
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--preprocessed-run", required=True)
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--output-s3-uri", required=True)
    parser.add_argument(
        "--curate-config",
        default=str(MIRRORVIEW_RULES_PATH),
        help="YAML rules applied to the wide table after the join.",
    )
    parsed = parser.parse_args(argv)
    return CampaignConsolidateArgs(
        dataset_id=parsed.dataset_id,
        preprocessed_run=parsed.preprocessed_run,
        campaign_id=parsed.campaign_id,
        output_s3_uri=parsed.output_s3_uri,
        curate_config=Path(parsed.curate_config),
    )


def verify_feature_manifest(
    store: CampaignObjectStore,
    feature_name: str,
    campaign_id: str,
    dataset_id: str,
) -> tuple[str, dict[str, Any]]:
    raise NotImplementedError


def download_campaign_inputs(
    store: CampaignObjectStore,
    args: CampaignConsolidateArgs,
    work_dir: Path,
) -> tuple[PreprocessedInputRecord, tuple[FeatureInputRecord, ...]]:
    raise NotImplementedError


def validate_wide_table(wide: pd.DataFrame) -> None:
    raise NotImplementedError


def curate_mirrorview_dataset(
    store: CampaignObjectStore,
    wide: pd.DataFrame,
    args: CampaignConsolidateArgs,
) -> CuratedDatasetRecord:
    raise NotImplementedError


def upload_wide_artifacts(
    store: CampaignObjectStore,
    wide: pd.DataFrame,
    args: CampaignConsolidateArgs,
    preprocessed: PreprocessedInputRecord,
    feature_inputs: tuple[FeatureInputRecord, ...],
    curated: CuratedDatasetRecord | None,
) -> tuple[str, str, str]:
    raise NotImplementedError


def run_campaign_consolidation(args: CampaignConsolidateArgs) -> WideConsolidateResult:
    raise NotImplementedError


def print_result(result: WideConsolidateResult) -> None:
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run_campaign_consolidation(args)
    print_result(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
