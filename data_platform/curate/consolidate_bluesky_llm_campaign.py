"""Join pinned Bluesky posts with seven campaign LLM feature files into one wide Parquet object.

Runtime validation (automated tests are forbidden by Step 15):

given seven feature manifests whose final.parquet SHA-256 and row_count are 200000
when the CLI joins pinned posts on source_record_id
then stdout includes each accepted manifest digest, wide_rows=200000, wide_columns=19,
     sort_key=source_record_id ASC, and the wide manifest URI

given a missing or SHA-mismatched feature final.parquet
when the CLI verifies inputs
then it raises before writing wide/features.parquet

given the uploaded wide parquet
when DuckDB describes columns and counts distinct source_record_id
then columns match the nineteen-name contract, n=uniq=200000, and no llm_toxicity_tier is null

given the same wide table and data_platform/curate/configs/bluesky/mirrorview.yaml
when apply_rules runs
then curated row count and political_stance x llm_toxicity_tier counts are written
     under wide/curated/

Run from the repo root:

    PYTHONPATH=. python data_platform/curate/consolidate_bluesky_llm_campaign.py \\
        --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \\
        --preprocessed-run 2026_09_03-23:51:30 \\
        --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \\
        --output-s3-uri s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/wide/features.parquet
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import boto3
import pandas as pd

from data_platform.curate.apply_rules import FilterStepResult, apply_rules, load_rules_config
from data_platform.curate.consolidate import (
    EXPECTED_WIDE_ROW_COUNT,
    LLM_CAMPAIGN_FEATURE_NAMES,
    PREPROCESSED_WIDE_COLUMNS,
    WIDE_SORT_KEY,
    build_llm_campaign_wide_table,
    llm_campaign_wide_columns,
)
from data_platform.curate.runner import build_curate_metadata
from data_platform.generate_features.s3_feature_campaign import (
    DEFAULT_CAMPAIGN_PLATFORM,
    S3_KEY_PREFIX,
    CampaignObjectStore,
    FeaturePaths,
    parse_s3_uri,
    s3_uri,
)
from data_platform.utils.object_store import DEFAULT_S3_REGION, sha256_hex
from data_platform.utils.platform_specific_columns import STANDARDIZED_SOURCE_RECORD_ID_COLUMN

MIRRORVIEW_RULES_PATH = (
    Path(__file__).resolve().parent / "configs" / "bluesky" / "mirrorview.yaml"
)
CURATED_RELATIVE_KEY = "curated/mirrorview.parquet"
CURATED_METADATA_RELATIVE_KEY = "curated/metadata.json"
WIDE_MANIFEST_FILENAME = "manifest.json"
WIDE_PARQUET_FILENAME = "features.parquet"
SHA256_READ_CHUNK_BYTES = 1024 * 1024
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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(SHA256_READ_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(document: dict[str, Any]) -> bytes:
    return json.dumps(document, indent=2).encode("utf-8")


def _s3_client() -> Any:
    return boto3.client("s3", region_name=DEFAULT_S3_REGION)


def _preprocessed_posts_key(dataset_id: str, preprocessed_run: str) -> str:
    return (
        f"{S3_KEY_PREFIX}/{DEFAULT_CAMPAIGN_PLATFORM}/{dataset_id}/"
        f"preprocessed/{preprocessed_run}/posts.parquet"
    )


def _wide_prefix(output_key: str) -> str:
    if not output_key.endswith(WIDE_PARQUET_FILENAME):
        raise ValueError(
            f"output-s3-uri must end with {WIDE_PARQUET_FILENAME}, got {output_key!r}"
        )
    return output_key[: -len(WIDE_PARQUET_FILENAME)]


def _download_key(client: Any, bucket: str, key: str, dest: Path) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    client.download_file(bucket, key, str(dest))
    return _sha256_file(dest)


def _upload_bytes(store: CampaignObjectStore, key: str, body: bytes) -> str:
    stored = store.get(key)
    if stored is None:
        return store.put_new(key, body).sha256
    return store.replace(key, body, etag=stored.etag).sha256


def verify_feature_manifest(
    store: CampaignObjectStore,
    feature_name: str,
    campaign_id: str,
    dataset_id: str,
) -> tuple[str, dict[str, Any]]:
    """Return manifest SHA-256 and parsed JSON after checking row count 200000."""
    paths = FeaturePaths.canonical(campaign_id, feature_name, dataset_id=dataset_id)
    stored = store.get(paths.manifest_key)
    if stored is None:
        raise FileNotFoundError(f"missing feature manifest: {paths.uri(paths.manifest_key)}")
    manifest = json.loads(stored.body)
    final = manifest.get("final_parquet") or {}
    if final.get("row_count") != EXPECTED_WIDE_ROW_COUNT:
        raise ValueError(
            f"{feature_name} final.parquet row_count is {final.get('row_count')}, "
            f"expected {EXPECTED_WIDE_ROW_COUNT}"
        )
    digest = sha256_hex(stored.body)
    print(f"accepted {feature_name} manifest sha256={digest}")
    return digest, manifest


def download_campaign_inputs(
    store: CampaignObjectStore,
    args: CampaignConsolidateArgs,
    work_dir: Path,
) -> tuple[PreprocessedInputRecord, tuple[FeatureInputRecord, ...]]:
    """Download pinned posts and seven verified ``final.parquet`` files."""
    client = _s3_client()
    posts_key = _preprocessed_posts_key(args.dataset_id, args.preprocessed_run)
    posts_path = work_dir / "posts.parquet"
    posts_sha = _download_key(client, store.bucket, posts_key, posts_path)
    preprocessed = PreprocessedInputRecord(key=posts_key, sha256=posts_sha, local_parquet=posts_path)
    features = tuple(
        _download_feature_final(store, client, args, work_dir, feature_name)
        for feature_name in LLM_CAMPAIGN_FEATURE_NAMES
    )
    return preprocessed, features


def _download_feature_final(
    store: CampaignObjectStore,
    client: Any,
    args: CampaignConsolidateArgs,
    work_dir: Path,
    feature_name: str,
) -> FeatureInputRecord:
    paths = FeaturePaths.canonical(args.campaign_id, feature_name, dataset_id=args.dataset_id)
    manifest_sha, manifest = verify_feature_manifest(
        store, feature_name, args.campaign_id, args.dataset_id
    )
    final = manifest["final_parquet"]
    local_path = work_dir / feature_name / "final.parquet"
    digest = _download_key(client, store.bucket, paths.final_key, local_path)
    expected = str(final["sha256"]).lower()
    if digest != expected:
        raise ValueError(
            f"{feature_name} final.parquet SHA-256 mismatch: manifest {expected}, object {digest}"
        )
    return FeatureInputRecord(
        feature_name=feature_name,
        final_key=paths.final_key,
        final_sha256=digest,
        final_row_count=int(final["row_count"]),
        manifest_key=paths.manifest_key,
        manifest_sha256=manifest_sha,
        local_parquet=local_path,
    )


def validate_wide_table(wide: pd.DataFrame) -> None:
    """Raise ValueError when the wide table misses the Step 15 contract."""
    expected = llm_campaign_wide_columns()
    actual = tuple(wide.columns)
    if actual != expected:
        raise ValueError(f"wide columns {actual} do not match {expected}")
    _validate_wide_rows(wide)
    forbidden = FORBIDDEN_WIDE_COLUMNS.intersection(actual)
    if forbidden:
        raise ValueError(f"wide table contains forbidden columns: {sorted(forbidden)}")
    _validate_wide_labels(wide, expected)


def _validate_wide_rows(wide: pd.DataFrame) -> None:
    id_column = STANDARDIZED_SOURCE_RECORD_ID_COLUMN
    if len(wide) != EXPECTED_WIDE_ROW_COUNT:
        raise ValueError(f"wide_rows={len(wide)}, expected {EXPECTED_WIDE_ROW_COUNT}")
    unique_ids = wide[id_column].astype(str).nunique()
    if unique_ids != EXPECTED_WIDE_ROW_COUNT:
        raise ValueError(f"distinct source_record_id={unique_ids}, expected {EXPECTED_WIDE_ROW_COUNT}")
    ids = wide[id_column].astype(str)
    if not ids.is_monotonic_increasing:
        raise ValueError("wide rows are not sorted by source_record_id ASC")


def _validate_wide_labels(wide: pd.DataFrame, expected_columns: tuple[str, ...]) -> None:
    label_columns = expected_columns[len(PREPROCESSED_WIDE_COLUMNS) :]
    null_counts = {
        column: int(wide[column].isna().sum())
        for column in label_columns
        if int(wide[column].isna().sum()) > 0
    }
    if null_counts:
        raise ValueError(f"null feature values: {null_counts}")


def _filter_step_record(step: FilterStepResult) -> dict[str, Any]:
    return {
        **step.rule.model_dump(),
        "records_before": step.records_before,
        "records_passing": step.records_passing,
    }


def _stance_by_toxicity(filtered: pd.DataFrame) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {
        stance: {tier: 0 for tier in TOXICITY_CROSSTAB_COLUMNS} for stance in STANCE_CROSSTAB_ROWS
    }
    grouped = filtered.groupby(["political_stance", "llm_toxicity_tier"], dropna=False).size()
    for (stance, tier), row_count in grouped.items():
        stance_key = str(stance)
        tier_key = str(tier)
        counts.setdefault(stance_key, {})
        counts[stance_key][tier_key] = int(row_count)
    return counts


def curate_mirrorview_dataset(
    store: CampaignObjectStore,
    wide: pd.DataFrame,
    args: CampaignConsolidateArgs,
    wide_parquet_key: str,
) -> CuratedDatasetRecord:
    """Apply existing MirrorView YAML filters and upload the curated Parquet."""
    rules = load_rules_config(args.curate_config)
    rules_hash = hashlib.sha256(args.curate_config.read_bytes()).hexdigest()
    applied = apply_rules(wide, rules)
    filtered = applied.dataframe
    prefix = _wide_prefix(wide_parquet_key)
    parquet_key = f"{prefix}{CURATED_RELATIVE_KEY}"
    metadata_key = f"{prefix}{CURATED_METADATA_RELATIVE_KEY}"
    parquet_sha = _upload_bytes(store, parquet_key, filtered.to_parquet(index=False))
    stance_by_toxicity = _stance_by_toxicity(filtered)
    metadata = build_curate_metadata(
        dataset_id=args.dataset_id,
        rules_name=rules.name,
        rules_hash=rules_hash,
        source_preprocessed_runs=[args.preprocessed_run],
        wide_df=wide,
        filtered_df=filtered,
        rules_result=applied,
        export_filename="mirrorview.parquet",
    )
    metadata["crosstab_political_stance_by_llm_toxicity_tier"] = stance_by_toxicity
    metadata_sha = _upload_bytes(store, metadata_key, _json_bytes(metadata))
    return CuratedDatasetRecord(
        row_count=len(filtered),
        parquet_key=parquet_key,
        parquet_sha256=parquet_sha,
        metadata_key=metadata_key,
        metadata_sha256=metadata_sha,
        rules_hash=rules_hash,
        filter_steps=[_filter_step_record(step) for step in applied.steps],
        stance_by_toxicity=stance_by_toxicity,
    )


def _feature_manifest_block(
    store: CampaignObjectStore, record: FeatureInputRecord
) -> dict[str, Any]:
    return {
        "manifest_uri": s3_uri(store.bucket, record.manifest_key),
        "manifest_sha256": record.manifest_sha256,
        "final_parquet": {
            "key": record.final_key,
            "sha256": record.final_sha256,
            "row_count": record.final_row_count,
        },
    }


def _wide_manifest_document(
    store: CampaignObjectStore,
    args: CampaignConsolidateArgs,
    wide_key: str,
    wide_sha: str,
    preprocessed: PreprocessedInputRecord,
    feature_inputs: tuple[FeatureInputRecord, ...],
    curated: CuratedDatasetRecord | None,
) -> dict[str, Any]:
    document: dict[str, Any] = {
        "dataset_id": args.dataset_id,
        "preprocessed_run": args.preprocessed_run,
        "campaign_id": args.campaign_id,
        "row_count": EXPECTED_WIDE_ROW_COUNT,
        "columns": list(llm_campaign_wide_columns()),
        "sort_key": WIDE_SORT_KEY,
        "wide_parquet": {
            "key": wide_key,
            "sha256": wide_sha,
            "row_count": EXPECTED_WIDE_ROW_COUNT,
        },
        "preprocessed": {"key": preprocessed.key, "sha256": preprocessed.sha256},
        "features": {
            record.feature_name: _feature_manifest_block(store, record)
            for record in feature_inputs
        },
    }
    if curated is not None:
        document["curated"] = {
            "rules_config": str(args.curate_config),
            "rules_hash": curated.rules_hash,
            "row_count": curated.row_count,
            "parquet": {"key": curated.parquet_key, "sha256": curated.parquet_sha256},
            "metadata": {"key": curated.metadata_key, "sha256": curated.metadata_sha256},
            "crosstab_political_stance_by_llm_toxicity_tier": curated.stance_by_toxicity,
        }
    return document


def upload_wide_artifacts(
    store: CampaignObjectStore,
    wide: pd.DataFrame,
    args: CampaignConsolidateArgs,
    preprocessed: PreprocessedInputRecord,
    feature_inputs: tuple[FeatureInputRecord, ...],
    curated: CuratedDatasetRecord | None,
) -> tuple[str, str, str]:
    """Upload ``features.parquet`` and ``manifest.json``. Return parquet SHA-256, parquet URI, manifest URI."""
    bucket, wide_key = parse_s3_uri(args.output_s3_uri)
    if bucket != store.bucket:
        raise ValueError(f"output bucket {bucket} does not match campaign bucket {store.bucket}")
    wide_sha = _upload_bytes(store, wide_key, wide.to_parquet(index=False))
    manifest_key = f"{_wide_prefix(wide_key)}{WIDE_MANIFEST_FILENAME}"
    manifest = _wide_manifest_document(
        store, args, wide_key, wide_sha, preprocessed, feature_inputs, curated
    )
    _upload_bytes(store, manifest_key, _json_bytes(manifest))
    return wide_sha, s3_uri(store.bucket, wide_key), s3_uri(store.bucket, manifest_key)


def run_campaign_consolidation(args: CampaignConsolidateArgs) -> WideConsolidateResult:
    """Download inputs, join, validate, upload wide artifacts, and curate."""
    paths = FeaturePaths.canonical(
        args.campaign_id, LLM_CAMPAIGN_FEATURE_NAMES[0], dataset_id=args.dataset_id
    )
    store = CampaignObjectStore(paths.bucket)
    with TemporaryDirectory() as tmp:
        preprocessed, features = download_campaign_inputs(store, args, Path(tmp))
        wide = build_llm_campaign_wide_table(
            preprocessed.local_parquet,
            {record.feature_name: record.local_parquet for record in features},
        )
        validate_wide_table(wide)
        _, wide_key = parse_s3_uri(args.output_s3_uri)
        curated = curate_mirrorview_dataset(store, wide, args, wide_key)
        wide_sha, parquet_uri, manifest_uri = upload_wide_artifacts(
            store, wide, args, preprocessed, features, curated
        )
    return WideConsolidateResult(
        wide_rows=len(wide),
        wide_columns=tuple(wide.columns),
        wide_parquet_uri=parquet_uri,
        wide_parquet_sha256=wide_sha,
        manifest_uri=manifest_uri,
        sort_key=WIDE_SORT_KEY,
        feature_inputs=features,
        preprocessed=preprocessed,
        curated=curated,
    )


def print_result(result: WideConsolidateResult) -> None:
    """Print the Step 15 stdout contract plus curated row count."""
    print(f"wide_rows={result.wide_rows}")
    print(f"wide_columns={len(result.wide_columns)}")
    print(f"manifest={result.manifest_uri}")
    print(f"sort_key={result.sort_key}")
    if result.curated is None:
        return
    print(f"curated_rows={result.curated.row_count}")
    print("curated_crosstab_political_stance_by_llm_toxicity_tier=")
    print(json.dumps(result.curated.stance_by_toxicity, indent=2))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run_campaign_consolidation(args)
    print_result(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
