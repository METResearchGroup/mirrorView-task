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
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import boto3
import duckdb
import pandas as pd

from data_platform.curate.apply_rules import (
    ApplyRulesResult,
    CurateRulesConfig,
    FilterStepResult,
    apply_rules,
    load_rules_config,
)
from data_platform.curate.consolidate import (
    FEATURE_WIDE_COLUMNS,
    LLM_CAMPAIGN_FEATURE_NAMES,
    WIDE_SORT_KEY,
)
from data_platform.curate.runner import build_curate_metadata
from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    FeaturePaths,
    s3_uri,
)
from data_platform.utils.dataset import dataset_root, relative_run_path
from data_platform.utils.object_store import DEFAULT_S3_REGION, S3_KEY_PREFIX, sha256_hex
from data_platform.utils.platform_specific_columns import STANDARDIZED_SOURCE_RECORD_ID_COLUMN
from data_platform.utils.storage import DATA_ROOT, TwitterStorageManager
from lib.timestamp_utils import get_current_timestamp

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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(SHA256_READ_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _s3_client() -> Any:
    return boto3.client("s3", region_name=DEFAULT_S3_REGION)


def _twitter_feature_paths(campaign_id: str, feature_name: str, dataset_id: str) -> FeaturePaths:
    return FeaturePaths.for_campaign(
        campaign_id,
        feature_name,
        platform=TWITTER_PLATFORM,
        dataset_id=dataset_id,
    )


def _preprocessed_posts_key(dataset_id: str, preprocessed_run: str) -> str:
    return (
        f"{S3_KEY_PREFIX}/{TWITTER_PLATFORM}/{dataset_id}/"
        f"preprocessed/{preprocessed_run}/posts.csv"
    )


def _inventory_path(dataset_id: str) -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "data"
        / TWITTER_PLATFORM
        / dataset_id
        / INVENTORY_FILENAME
    )


def _expected_posts_sha256(dataset_id: str, posts_key: str) -> str:
    inventory = json.loads(_inventory_path(dataset_id).read_text(encoding="utf-8"))
    for obj in inventory["objects"]:
        if obj.get("s3_key") == posts_key:
            return str(obj["sha256"]).lower()
    raise ValueError(f"inventory has no object for {posts_key}")


def _require_sha256(label: str, actual: str, expected: str) -> None:
    if actual != expected:
        raise ValueError(f"{label} SHA-256 mismatch: expected {expected}, object {actual}")


def _download_key(client: Any, bucket: str, key: str, dest: Path) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    client.download_file(bucket, key, str(dest))
    return _sha256_file(dest)


def _require_final_row_count(feature_name: str, manifest: dict[str, Any]) -> dict[str, Any]:
    final = manifest.get("final_parquet") or {}
    if final.get("row_count") != TWITTER_EXPECTED_WIDE_ROW_COUNT:
        raise ValueError(
            f"{feature_name} final.parquet row_count is {final.get('row_count')}, "
            f"expected {TWITTER_EXPECTED_WIDE_ROW_COUNT}"
        )
    return final


def verify_feature_manifest(
    store: CampaignObjectStore,
    feature_name: str,
    campaign_id: str,
    dataset_id: str,
) -> tuple[str, dict[str, Any]]:
    """Return manifest SHA-256 and parsed JSON after checking row count 6374."""
    paths = _twitter_feature_paths(campaign_id, feature_name, dataset_id)
    stored = store.get(paths.manifest_key)
    if stored is None:
        raise FileNotFoundError(f"missing feature manifest: {paths.uri(paths.manifest_key)}")
    manifest = json.loads(stored.body)
    _require_final_row_count(feature_name, manifest)
    digest = sha256_hex(stored.body)
    print(f"accepted {feature_name} manifest sha256={digest}")
    return digest, manifest


def _feature_record(
    paths: FeaturePaths,
    feature_name: str,
    manifest_sha: str,
    final: dict[str, Any],
    digest: str,
    local_path: Path,
) -> FeatureInputRecord:
    return FeatureInputRecord(
        feature_name=feature_name,
        final_key=paths.final_key,
        final_sha256=digest,
        final_row_count=int(final["row_count"]),
        manifest_key=paths.manifest_key,
        manifest_sha256=manifest_sha,
        local_parquet=local_path,
    )


def _download_feature_final(
    store: CampaignObjectStore,
    client: Any,
    args: CampaignConsolidateArgs,
    work_dir: Path,
    feature_name: str,
) -> FeatureInputRecord:
    paths = _twitter_feature_paths(args.campaign_id, feature_name, args.dataset_id)
    manifest_sha, manifest = verify_feature_manifest(
        store, feature_name, args.campaign_id, args.dataset_id
    )
    local_path = work_dir / feature_name / "final.parquet"
    digest = _download_key(client, store.bucket, paths.final_key, local_path)
    _require_sha256(
        f"{feature_name} final.parquet",
        digest,
        str(manifest["final_parquet"]["sha256"]).lower(),
    )
    return _feature_record(
        paths, feature_name, manifest_sha, manifest["final_parquet"], digest, local_path
    )


def _download_posts_csv(
    client: Any,
    store: CampaignObjectStore,
    args: CampaignConsolidateArgs,
    work_dir: Path,
) -> PreprocessedInputRecord:
    posts_key = _preprocessed_posts_key(args.dataset_id, args.preprocessed_run)
    expected = _expected_posts_sha256(args.dataset_id, posts_key)
    posts_path = work_dir / "posts.csv"
    posts_sha = _download_key(client, store.bucket, posts_key, posts_path)
    _require_sha256("posts.csv", posts_sha, expected)
    return PreprocessedInputRecord(key=posts_key, sha256=posts_sha, local_csv=posts_path)


def download_campaign_inputs(
    store: CampaignObjectStore,
    args: CampaignConsolidateArgs,
    work_dir: Path,
) -> tuple[PreprocessedInputRecord, tuple[FeatureInputRecord, ...]]:
    """Download pinned posts.csv and seven verified ``final.parquet`` files."""
    client = _s3_client()
    preprocessed = _download_posts_csv(client, store, args, work_dir)
    features = tuple(
        _download_feature_final(store, client, args, work_dir, feature_name)
        for feature_name in LLM_CAMPAIGN_FEATURE_NAMES
    )
    return preprocessed, features


def _sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def _posts_cte_sql(posts_file: Path) -> str:
    id_column = STANDARDIZED_SOURCE_RECORD_ID_COLUMN
    selected = ", ".join(
        f"CAST({column} AS VARCHAR) AS {column}" if column == id_column else column
        for column in TWITTER_PREPROCESSED_WIDE_COLUMNS
    )
    csv_path = _sql_path(posts_file)
    return f"posts AS (SELECT {selected} FROM read_csv('{csv_path}', union_by_name = true))"


def _feature_cte_sql(feature_name: str, parquet_path: Path) -> str:
    column_pairs = FEATURE_WIDE_COLUMNS[feature_name]
    inner_cols = ", ".join(
        f"{source} AS {alias}" if source != alias else source for source, alias in column_pairs
    )
    outer_cols = ", ".join(alias for _, alias in column_pairs)
    id_column = STANDARDIZED_SOURCE_RECORD_ID_COLUMN
    parquet = _sql_path(parquet_path)
    return f"""
feat_{feature_name} AS (
    SELECT {id_column}, {outer_cols}
    FROM (
        SELECT CAST({id_column} AS VARCHAR) AS {id_column}, {inner_cols},
            ROW_NUMBER() OVER (
                PARTITION BY CAST({id_column} AS VARCHAR)
                ORDER BY label_timestamp DESC NULLS LAST, CAST({id_column} AS VARCHAR)
            ) AS rn
        FROM read_parquet('{parquet}')
    )
    WHERE rn = 1
)"""


def _twitter_join_sql(posts_file: Path, feature_files: dict[str, Path]) -> str:
    id_column = STANDARDIZED_SOURCE_RECORD_ID_COLUMN
    join_clauses = [
        f"INNER JOIN feat_{feature_name} USING ({id_column})"
        for feature_name in LLM_CAMPAIGN_FEATURE_NAMES
    ]
    label_cols = [
        f"feat_{feature_name}.{alias}"
        for feature_name in LLM_CAMPAIGN_FEATURE_NAMES
        for _, alias in FEATURE_WIDE_COLUMNS[feature_name]
    ]
    posts_cols = [f"posts.{column}" for column in TWITTER_PREPROCESSED_WIDE_COLUMNS]
    feature_ctes = [
        _feature_cte_sql(feature_name, feature_files[feature_name])
        for feature_name in LLM_CAMPAIGN_FEATURE_NAMES
    ]
    ctes = ",\n".join([_posts_cte_sql(posts_file), *feature_ctes])
    return f"""
WITH {ctes}
SELECT {", ".join(posts_cols + label_cols)}
FROM posts
{" ".join(join_clauses)}
ORDER BY posts.{id_column} ASC
"""


def _missing_feature_names(feature_files: dict[str, Path]) -> list[str]:
    return [name for name in LLM_CAMPAIGN_FEATURE_NAMES if name not in feature_files]


def build_twitter_llm_campaign_wide_table(
    posts_file: Path,
    feature_files: dict[str, Path],
) -> pd.DataFrame:
    """Inner-join pinned csv posts to seven campaign ``final.parquet`` files."""
    missing = _missing_feature_names(feature_files)
    if missing:
        raise KeyError(f"missing campaign feature parquet paths: {missing}")
    sql = _twitter_join_sql(posts_file, feature_files)
    conn = duckdb.connect()
    try:
        return conn.execute(sql).fetchdf()
    finally:
        conn.close()


def _validate_wide_rows(wide: pd.DataFrame) -> None:
    id_column = STANDARDIZED_SOURCE_RECORD_ID_COLUMN
    if len(wide) != TWITTER_EXPECTED_WIDE_ROW_COUNT:
        raise ValueError(f"wide_rows={len(wide)}, expected {TWITTER_EXPECTED_WIDE_ROW_COUNT}")
    unique_ids = wide[id_column].astype(str).nunique()
    if unique_ids != TWITTER_EXPECTED_WIDE_ROW_COUNT:
        raise ValueError(
            f"distinct source_record_id={unique_ids}, expected {TWITTER_EXPECTED_WIDE_ROW_COUNT}"
        )
    if not wide[id_column].astype(str).is_monotonic_increasing:
        raise ValueError("wide rows are not sorted by source_record_id ASC")


def _validate_wide_labels(wide: pd.DataFrame, expected_columns: tuple[str, ...]) -> None:
    label_columns = expected_columns[len(TWITTER_PREPROCESSED_WIDE_COLUMNS) :]
    null_counts = {
        column: int(wide[column].isna().sum())
        for column in label_columns
        if int(wide[column].isna().sum()) > 0
    }
    if null_counts:
        raise ValueError(f"null feature values: {null_counts}")


def validate_wide_table(wide: pd.DataFrame) -> None:
    """Raise ValueError when the wide table misses the Twitter campaign contract."""
    expected = twitter_llm_campaign_wide_columns()
    actual = tuple(wide.columns)
    if actual != expected:
        raise ValueError(f"wide columns {actual} do not match {expected}")
    _validate_wide_rows(wide)
    forbidden = FORBIDDEN_WIDE_COLUMNS.intersection(actual)
    if forbidden:
        raise ValueError(f"wide table contains forbidden columns: {sorted(forbidden)}")
    _validate_wide_labels(wide, expected)


def _upload_bytes(store: CampaignObjectStore, key: str, body: bytes) -> str:
    stored = store.get(key)
    if stored is None:
        return store.put_new(key, body).sha256
    return store.replace(key, body, etag=stored.etag).sha256


def _full_data_key(path: Path) -> str:
    return f"{S3_KEY_PREFIX}/{path.relative_to(DATA_ROOT).as_posix()}"


def _curated_export_filename(stem: str) -> str:
    return f"{stem}.{CURATED_EXPORT_SUFFIX}"


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


def _write_curated_parquet(
    store: CampaignObjectStore,
    filtered: pd.DataFrame,
    output_path: Path,
) -> tuple[str, str]:
    parquet_key = _full_data_key(output_path)
    digest = _upload_bytes(store, parquet_key, filtered.to_parquet(index=False))
    return parquet_key, digest


def _curate_metadata_document(
    args: CampaignConsolidateArgs,
    rules: CurateRulesConfig,
    rules_hash: str,
    wide: pd.DataFrame,
    filtered: pd.DataFrame,
    applied: ApplyRulesResult,
    export_filename: str,
    stance_by_toxicity: dict[str, dict[str, int]],
) -> dict[str, Any]:
    dataset = dataset_root(TWITTER_PLATFORM, args.dataset_id)
    preprocessed_dir = dataset / "preprocessed" / args.preprocessed_run
    metadata = build_curate_metadata(
        dataset_id=args.dataset_id,
        rules_name=rules.name,
        rules_hash=rules_hash,
        source_preprocessed_runs=[relative_run_path(dataset, preprocessed_dir)],
        wide_df=wide,
        filtered_df=filtered,
        rules_result=applied,
        export_filename=export_filename,
    )
    metadata["crosstab_political_stance_by_llm_toxicity_tier"] = stance_by_toxicity
    return metadata


def _curated_record(
    filtered: pd.DataFrame,
    parquet_key: str,
    parquet_sha: str,
    metadata_key: str,
    metadata_sha: str,
    rules_hash: str,
    applied: ApplyRulesResult,
    stance_by_toxicity: dict[str, dict[str, int]],
) -> CuratedDatasetRecord:
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


def _object_sha256(store: CampaignObjectStore, key: str) -> str:
    stored = store.get(key)
    if stored is None:
        raise FileNotFoundError(f"missing object after write: {s3_uri(store.bucket, key)}")
    return sha256_hex(stored.body)


def _apply_mirrorview_rules(
    args: CampaignConsolidateArgs, wide: pd.DataFrame
) -> tuple[CurateRulesConfig, str, ApplyRulesResult]:
    rules = load_rules_config(args.curate_config)
    rules_hash = hashlib.sha256(args.curate_config.read_bytes()).hexdigest()
    return rules, rules_hash, apply_rules(wide, rules)


def curate_mirrorview_dataset(
    store: CampaignObjectStore,
    wide: pd.DataFrame,
    args: CampaignConsolidateArgs,
) -> CuratedDatasetRecord:
    """Apply Twitter MirrorView YAML filters and upload ``mirrorview.parquet``."""
    rules, rules_hash, applied = _apply_mirrorview_rules(args, wide)
    filtered = applied.dataframe
    curated_storage = TwitterStorageManager("curated", args.dataset_id)
    run_dir = curated_storage.create_new_run_dir(get_current_timestamp())
    export_filename = _curated_export_filename(rules.output.stem)
    parquet_key, parquet_sha = _write_curated_parquet(store, filtered, run_dir / export_filename)
    stance_by_toxicity = _stance_by_toxicity(filtered)
    metadata = _curate_metadata_document(
        args, rules, rules_hash, wide, filtered, applied, export_filename, stance_by_toxicity
    )
    metadata_key = _full_data_key(curated_storage.write_run_metadata(run_dir, metadata))
    return _curated_record(
        filtered,
        parquet_key,
        parquet_sha,
        metadata_key,
        _object_sha256(store, metadata_key),
        rules_hash,
        applied,
        stance_by_toxicity,
    )


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
