"""Join pinned Bluesky posts with seven campaign LLM feature files into one wide Parquet object.

Run from the repo root:

    PYTHONPATH=. python data_platform/curate/consolidate_bluesky_llm_campaign.py \\
        --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \\
        --preprocessed-run 2026_09_03-23:51:30 \\
        --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \\
        --output-s3-uri s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/wide/features.parquet
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from data_platform.curate.apply_rules import ApplyRulesResult
from data_platform.curate.consolidate import (
    EXPECTED_WIDE_ROW_COUNT,
    LLM_CAMPAIGN_FEATURE_NAMES,
    PREPROCESSED_WIDE_COLUMNS,
)
from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore

MIRRORVIEW_RULES_PATH = (
    Path(__file__).resolve().parent / "configs" / "bluesky" / "mirrorview.yaml"
)
CURATED_RELATIVE_KEY = "curated/mirrorview.parquet"
CURATED_METADATA_RELATIVE_KEY = "curated/metadata.json"
WIDE_MANIFEST_FILENAME = "manifest.json"
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
    """CLI inputs for the Bluesky LLM campaign wide join."""

    dataset_id: str
    preprocessed_run: str
    campaign_id: str
    output_s3_uri: str
    curate_config: Path


@dataclass(frozen=True)
class FeatureInputRecord:
    """Verified feature ``final.parquet`` and its provenance manifest."""

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
        description="Join seven Bluesky LLM campaign features into one wide Parquet object."
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
    """Return manifest SHA-256 and parsed JSON after checking row count 200000."""
    raise NotImplementedError("feature manifest verification is not implemented")


def download_campaign_inputs(
    store: CampaignObjectStore,
    args: CampaignConsolidateArgs,
    work_dir: Path,
) -> tuple[PreprocessedInputRecord, tuple[FeatureInputRecord, ...]]:
    """Download pinned posts and seven verified ``final.parquet`` files."""
    raise NotImplementedError("campaign input download is not implemented")


def validate_wide_table(wide: pd.DataFrame) -> None:
    """Raise ValueError when the wide table misses the Step 15 contract."""
    raise NotImplementedError("wide table validation is not implemented")


def upload_wide_artifacts(
    store: CampaignObjectStore,
    wide: pd.DataFrame,
    args: CampaignConsolidateArgs,
    preprocessed: PreprocessedInputRecord,
    feature_inputs: tuple[FeatureInputRecord, ...],
    curated: CuratedDatasetRecord | None,
) -> tuple[str, str, str]:
    """Upload ``features.parquet`` and ``manifest.json``. Return parquet SHA-256, parquet URI, manifest URI."""
    raise NotImplementedError("wide artifact upload is not implemented")


def curate_mirrorview_dataset(
    store: CampaignObjectStore,
    wide: pd.DataFrame,
    args: CampaignConsolidateArgs,
    wide_parquet_key: str,
) -> CuratedDatasetRecord:
    """Apply existing MirrorView YAML filters and upload the curated Parquet."""
    raise NotImplementedError("mirrorview curation is not implemented")


def run_campaign_consolidation(args: CampaignConsolidateArgs) -> WideConsolidateResult:
    """Download inputs, join, validate, upload wide artifacts, and curate."""
    raise NotImplementedError("campaign consolidation is not implemented")


def print_result(result: WideConsolidateResult) -> None:
    """Print the Step 15 stdout contract plus curated row count."""
    raise NotImplementedError("result printing is not implemented")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run_campaign_consolidation(args)
    print_result(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
