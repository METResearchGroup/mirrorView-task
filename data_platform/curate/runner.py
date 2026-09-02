"""Shared curation pipeline for platform entrypoints."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import typer

from data_platform.constants import COMMENTS_FILENAME, POSTS_FILENAME
from data_platform.curate.apply_rules import ApplyRulesResult, apply_rules, load_rules_config
from data_platform.curate.consolidate import ConsolidateConfig, build_wide_table
from data_platform.utils.config_paths import resolve_config_path
from data_platform.utils.dataset import dataset_root, validate_dataset_id
from data_platform.utils.paths import to_package_relative
from data_platform.utils.platform_specific_columns import PlatformSpecificColumns
from data_platform.utils.storage import StorageManager
from lib.timestamp_utils import get_current_timestamp

StorageManagerFactory = Callable[..., StorageManager]


@dataclass(frozen=True)
class CuratePlatformSpec:
    platform: str
    storage_cls: StorageManagerFactory
    columns: PlatformSpecificColumns
    record_noun: str


def build_curate_metadata(
    *,
    dataset_id: str,
    rules_name: str,
    rules_hash: str,
    source_preprocessed_runs: list[str],
    wide_df: pd.DataFrame,
    filtered_df: pd.DataFrame,
    rules_result: ApplyRulesResult,
    export_filename: str,
) -> dict[str, Any]:
    return {
        "dataset_id": dataset_id,
        "name": rules_name,
        "rules_hash": rules_hash,
        "source_preprocessed_runs": source_preprocessed_runs,
        "row_counts": {
            "preprocessed": len(wide_df),
            "wide": len(wide_df),
            "after_filters": len(filtered_df),
        },
        "filter_results": [
            {
                **step.rule.model_dump(),
                "records_before": step.records_before,
                "records_passing": step.records_passing,
            }
            for step in rules_result.steps
        ],
        "files": {"export": export_filename},
    }


def run_curation(
    config_path: Path, dataset_id: str, spec: CuratePlatformSpec, *, rules_hash: str
) -> str:
    """Join labels, apply YAML filters, and write a curated export.

    Returns
    -------
    str
        Package-relative path of the curated csv, including the export file name.
    """
    dataset_id = validate_dataset_id(dataset_id)
    root = dataset_root(spec.platform, dataset_id)
    preprocessed_storage = spec.storage_cls("preprocessed", dataset_id)
    curated_storage = spec.storage_cls("curated", dataset_id)
    features_root = root / "features"

    rules = load_rules_config(config_path)
    if not preprocessed_storage.root_dir.exists():
        raise FileNotFoundError(f"No preprocessed runs found for dataset {dataset_id}")
    all_run_dirs = sorted(p for p in preprocessed_storage.root_dir.iterdir() if p.is_dir())
    if not all_run_dirs:
        raise FileNotFoundError(f"No preprocessed runs found for dataset {dataset_id}")

    records_filename = (
        COMMENTS_FILENAME if spec.columns.records_file_key == "comments" else POSTS_FILENAME
    )
    posts_glob = preprocessed_storage.root_dir / "*" / records_filename
    consolidate_kwargs: dict[str, Any] = {
        "posts_file": posts_glob,
        "features_root": features_root,
    }
    if spec.columns.records_id_column != "uri":
        consolidate_kwargs["id_column"] = spec.columns.records_id_column
        consolidate_kwargs["feature_file_id_column"] = spec.columns.feature_file_id_column

    wide_df = build_wide_table(ConsolidateConfig(**consolidate_kwargs))
    rules_result = apply_rules(wide_df, rules)
    filtered_df = rules_result.dataframe

    relative_run_dir = curated_storage.create_new_run_dir(get_current_timestamp())
    relative_file_path = f"{relative_run_dir}/{rules.output.filename}"
    curated_storage.write_dataframe(filtered_df, relative_file_path)

    source_preprocessed_runs = [to_package_relative(d) for d in all_run_dirs]
    metadata = build_curate_metadata(
        dataset_id=dataset_id,
        rules_name=rules.name,
        rules_hash=rules_hash,
        source_preprocessed_runs=source_preprocessed_runs,
        wide_df=wide_df,
        filtered_df=filtered_df,
        rules_result=rules_result,
        export_filename=rules.output.filename,
    )
    curated_storage.write_run_metadata(relative_run_dir, metadata)

    print(
        f"curate_{spec.platform}: kept {len(filtered_df)} of {len(wide_df)} "
        f"{spec.record_noun} -> {relative_run_dir}"
    )
    return relative_file_path


def curate_with_spec(config_path: Path, dataset_id: str, spec: CuratePlatformSpec) -> str:
    """Run curation for a platform spec, hashing the rules config for metadata."""
    rules_hash = hashlib.sha256(config_path.read_bytes()).hexdigest()
    return run_curation(config_path, dataset_id, spec, rules_hash=rules_hash)


def run_curate_main(
    *,
    spec: CuratePlatformSpec,
    configs_dir: Path,
    configs_help: str,
    dataset_id: str,
    config: Path,
) -> None:
    """Shared Typer main for Reddit/Twitter curate CLIs."""
    config_path = resolve_config_path(config, configs_dir)
    curate_with_spec(config_path, dataset_id, spec)


def make_curate_cli(
    spec: CuratePlatformSpec,
    configs_dir: Path,
    *,
    configs_help: str,
) -> Callable[[], None]:
    """Build a Typer CLI entrypoint for a platform curate script."""

    def main(
        dataset_id: str = typer.Option(
            ...,
            "--dataset-id",
            help=f"Dataset identifier from ingestion YAML ({spec.platform}_<uuid>)",
        ),
        config: Path = typer.Option(
            Path("mirrorview.yaml"),
            "--config",
            "-c",
            help=configs_help,
        ),
    ) -> None:
        run_curate_main(
            spec=spec,
            configs_dir=configs_dir,
            configs_help=configs_help,
            dataset_id=dataset_id,
            config=config,
        )

    return main
