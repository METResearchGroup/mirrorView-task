"""Join pinned Twitter posts with seven campaign LLM feature files into one wide Parquet object.

Runtime validation (automated tests are forbidden by issue 235):

given seven feature manifests whose final.parquet SHA-256 and row_count are 6374,
     and posts.csv whose SHA-256 matches the inventory
when the CLI joins pinned posts on source_record_id
then stdout includes each accepted manifest digest, wide_rows=6374, wide_columns=21,
     sort_key=source_record_id ASC, and the wide manifest URI

given a missing or SHA-mismatched feature final.parquet, or a posts.csv SHA-256
     that does not match the inventory
when the CLI verifies inputs
then it raises before writing wide/features.parquet

given the uploaded wide parquet
when the columns and row count are checked
then column names match the 21-name contract, n=6374, and no llm_toxicity_tier is null

given the same wide table and data_platform/curate/configs/twitter/mirrorview.yaml
when apply_rules runs
then curated row count and political_stance x llm_toxicity_tier counts are written
     under the dataset curated/ stage, in a timestamped run directory,
     as mirrorview.parquet plus metadata.json

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/curate/consolidate_twitter_llm_campaign.py \\
        --dataset-id twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547 \\
        --preprocessed-run 2026_09_06-19:28:47 \\
        --campaign-id twitter_2026_09_06_192847_llm_features_v1 \\
        --output-s3-uri s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/wide/features.parquet
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from data_platform.curate.consolidate import (
    FEATURE_WIDE_COLUMNS,
    LLM_CAMPAIGN_FEATURE_NAMES,
    WIDE_SORT_KEY,
)
from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from data_platform.utils.platform_specific_columns import STANDARDIZED_SOURCE_RECORD_ID_COLUMN
from data_platform.utils.storage import TwitterStorageManager

MIRRORVIEW_RULES_PATH = (
    Path(__file__).resolve().parent / "configs" / "twitter" / "mirrorview.yaml"
)
TWITTER_PLATFORM = "twitter"
TWITTER_EXPECTED_WIDE_ROW_COUNT = 6374
WIDE_MANIFEST_FILENAME = "manifest.json"
WIDE_PARQUET_FILENAME = "features.parquet"
CURATED_EXPORT_SUFFIX = "parquet"
SHA256_READ_CHUNK_BYTES = 1024 * 1024
STANCE_CROSSTAB_ROWS = ("left", "right")
TOXICITY_CROSSTAB_COLUMNS = ("low", "medium", "high")
INVENTORY_FILENAME = "s3_preprocessed_inventory.json"
TWITTER_PREPROCESSED_WIDE_COLUMNS: tuple[str, ...] = (
    "tweet_id",
    "record_id",
    "url",
    "username",
    "author_handle",
    "text",
    "created_at",
    "like_count",
    "retweet_count",
    "reply_count",
    "quote_count",
    "keyword",
    "sync_timestamp",
    STANDARDIZED_SOURCE_RECORD_ID_COLUMN,
)
FORBIDDEN_WIDE_COLUMNS = frozenset(
    {
        "toxicity_prob",
        "toxicity_tier",
        "label_timestamp",
        "run_id",
        "is_toxic_tiered",
        "author_id",
    }
)


@dataclass(frozen=True)
class CampaignConsolidateArgs:
    """CLI inputs for the Twitter LLM campaign wide join."""

    dataset_id: str
    preprocessed_run: str
    campaign_id: str
    output_s3_uri: str
    curate_config: Path


@dataclass(frozen=True)
class FeatureInputRecord:
    """Verified feature ``final.parquet`` and its parameter manifest."""

    feature_name: str
    final_key: str
    final_sha256: str
    final_row_count: int
    manifest_key: str
    manifest_sha256: str
    local_parquet: Path


@dataclass(frozen=True)
class PreprocessedInputRecord:
    """Pinned preprocessed posts used as the wide-join left table."""

    key: str
    sha256: str
    local_csv: Path


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
    """Uploaded wide Parquet, manifest, and curated export."""

    wide_rows: int
    wide_columns: tuple[str, ...]
    wide_parquet_uri: str
    wide_parquet_sha256: str
    manifest_uri: str
    sort_key: str
    feature_inputs: tuple[FeatureInputRecord, ...]
    preprocessed: PreprocessedInputRecord
    curated: CuratedDatasetRecord | None


def twitter_llm_campaign_wide_columns() -> tuple[str, ...]:
    """Return the 21 wide columns in campaign contract order."""
    label_columns = tuple(
        alias
        for feature_name in LLM_CAMPAIGN_FEATURE_NAMES
        for _, alias in FEATURE_WIDE_COLUMNS[feature_name]
    )
    return TWITTER_PREPROCESSED_WIDE_COLUMNS + label_columns


def parse_args(argv: list[str] | None = None) -> CampaignConsolidateArgs:
    parser = argparse.ArgumentParser(
        description="Join seven Twitter LLM campaign features into one wide Parquet object."
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
    """Return manifest SHA-256 and parsed JSON after checking row count 6374."""
    raise NotImplementedError


def download_campaign_inputs(
    store: CampaignObjectStore,
    args: CampaignConsolidateArgs,
    work_dir: Path,
) -> tuple[PreprocessedInputRecord, tuple[FeatureInputRecord, ...]]:
    """Download pinned posts.csv and seven verified ``final.parquet`` files."""
    raise NotImplementedError


def build_twitter_llm_campaign_wide_table(
    posts_file: Path,
    feature_files: dict[str, Path],
) -> pd.DataFrame:
    """Inner-join pinned csv posts to seven campaign ``final.parquet`` files."""
    raise NotImplementedError


def validate_wide_table(wide: pd.DataFrame) -> None:
    """Raise ValueError when the wide table misses the Twitter campaign contract."""
    raise NotImplementedError


def curate_mirrorview_dataset(
    store: CampaignObjectStore,
    wide: pd.DataFrame,
    args: CampaignConsolidateArgs,
) -> CuratedDatasetRecord:
    """Apply Twitter MirrorView YAML filters and upload ``mirrorview.parquet``."""
    raise NotImplementedError


def upload_wide_artifacts(
    store: CampaignObjectStore,
    wide: pd.DataFrame,
    args: CampaignConsolidateArgs,
    preprocessed: PreprocessedInputRecord,
    feature_inputs: tuple[FeatureInputRecord, ...],
    curated: CuratedDatasetRecord | None,
) -> tuple[str, str, str]:
    """Upload ``features.parquet`` and ``manifest.json``."""
    raise NotImplementedError


def run_campaign_consolidation(args: CampaignConsolidateArgs) -> WideConsolidateResult:
    """Download inputs, join, validate, upload wide artifacts, and curate."""
    raise NotImplementedError


def print_result(result: WideConsolidateResult) -> None:
    """Print the stdout contract plus curated row count and crosstab."""
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run_campaign_consolidation(args)
    print_result(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
