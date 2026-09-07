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

from data_platform.curate.consolidate import LLM_CAMPAIGN_FEATURE_NAMES
from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from data_platform.utils.storage import TwitterStorageManager

MIRRORVIEW_RULES_PATH = Path(__file__).resolve().parent / "configs" / "twitter" / "mirrorview.yaml"


@dataclass(frozen=True)
class CampaignConsolidateArgs:
    """CLI inputs for the Twitter LLM campaign wide join."""


@dataclass(frozen=True)
class FeatureInputRecord:
    """Verified feature final.parquet and its parameter manifest."""


@dataclass(frozen=True)
class PreprocessedInputRecord:
    """Pinned preprocessed posts used as the wide-join left table."""


@dataclass(frozen=True)
class CuratedDatasetRecord:
    """MirrorView-filtered rows plus stance by toxicity counts."""


@dataclass(frozen=True)
class WideConsolidateResult:
    """Uploaded wide Parquet, manifest, and curated export."""


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
    parser.parse_args(argv)
    raise NotImplementedError


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


def build_twitter_llm_campaign_wide_table(
    posts_file: Path,
    feature_files: dict[str, Path],
) -> Any:
    raise NotImplementedError


def validate_wide_table(wide: Any) -> None:
    raise NotImplementedError


def curate_mirrorview_dataset(
    store: CampaignObjectStore,
    wide: Any,
    args: CampaignConsolidateArgs,
    curated_storage: TwitterStorageManager,
) -> CuratedDatasetRecord:
    raise NotImplementedError


def upload_wide_artifacts(
    store: CampaignObjectStore,
    wide: Any,
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
    _ = LLM_CAMPAIGN_FEATURE_NAMES
    sys.exit(main())
