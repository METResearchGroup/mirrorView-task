"""Shared curation pipeline for platform entrypoints."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import typer

from data_platform.curate.apply_rules import ApplyRulesResult, apply_rules, load_rules_config
from data_platform.curate.consolidate import ConsolidateConfig, build_wide_table
from data_platform.generate_features.metadata import metadata_path
from data_platform.generate_features.models import FeatureRunMetadata
from data_platform.utils.config_paths import resolve_config_path
from data_platform.utils.dataset import dataset_root, relative_run_path, validate_dataset_id
from data_platform.utils.gate_checks import require_features_complete
from data_platform.utils.platform_specific_columns import PlatformSpecificColumns
from data_platform.utils.storage import StorageManager
from lib.timestamp_utils import get_current_timestamp

StorageManagerFactory = Callable[..., StorageManager]


@dataclass(frozen=True)
class CuratePlatformSpec:
    """Settings object for one platform's curate command-line script.

    Bluesky sets the completeness and skip flags to true. Reddit and Twitter
    leave ``require_features_complete``, ``require_all_runs_complete``, and
    ``skip_if_up_to_date`` false, so each call writes a new curated run. If you
    set any of those flags to true on another platform, ``curate_with_spec``
    honors them the same way.
    """

    platform: str
    storage_cls: StorageManagerFactory
    columns: PlatformSpecificColumns
    record_noun: str
    require_features_complete: bool = False
    require_all_runs_complete: bool = False
    skip_if_up_to_date: bool = False


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
) -> Path:
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

    posts_glob = preprocessed_storage.root_dir / "*" / preprocessed_storage.records_filename
    consolidate_kwargs: dict[str, Any] = {
        "posts_file": posts_glob,
        "features_root": features_root,
        "id_column": spec.columns.records_id_column,
        "feature_file_id_column": spec.columns.feature_file_id_column,
    }

    wide_df = build_wide_table(ConsolidateConfig(**consolidate_kwargs))
    rules_result = apply_rules(wide_df, rules)
    filtered_df = rules_result.dataframe

    run_dir = curated_storage.create_new_run_dir(get_current_timestamp())
    output_filename = curated_storage.filename_for(rules.output.stem)
    output_path = curated_storage.write_dataframe(filtered_df, run_dir, filename=output_filename)

    source_preprocessed_runs = [relative_run_path(root, d) for d in all_run_dirs]
    metadata = build_curate_metadata(
        dataset_id=dataset_id,
        rules_name=rules.name,
        rules_hash=rules_hash,
        source_preprocessed_runs=source_preprocessed_runs,
        wide_df=wide_df,
        filtered_df=filtered_df,
        rules_result=rules_result,
        export_filename=output_filename,
    )
    curated_storage.write_run_metadata(run_dir, metadata)

    print(
        f"curate_{spec.platform}: kept {len(filtered_df)} of {len(wide_df)} "
        f"{spec.record_noun} -> {run_dir}"
    )
    return output_path


def load_features_run_metadata(platform: str, dataset_id: str) -> FeatureRunMetadata:
    """Load the latest timestamped features/metadata.json for a dataset.

    Raises
    ------
    FileNotFoundError
        When no feature run directory or metadata file exists.
    """
    features_root = dataset_root(platform, dataset_id) / "features"
    if not features_root.exists():
        raise FileNotFoundError(f"No features metadata found for dataset {dataset_id}")
    run_dirs = [path for path in features_root.iterdir() if path.is_dir()]
    if not run_dirs:
        raise FileNotFoundError(f"No features metadata found for dataset {dataset_id}")
    latest = max(run_dirs, key=lambda path: path.name)
    features_meta_path = metadata_path(latest)
    if not features_meta_path.exists():
        raise FileNotFoundError(f"No features metadata found for dataset {dataset_id}")
    with features_meta_path.open(encoding="utf-8") as handle:
        return FeatureRunMetadata.from_dict(json.load(handle))


def _preprocessed_run_dirs(spec: CuratePlatformSpec, dataset_id: str) -> list[Path]:
    preprocessed_storage = spec.storage_cls("preprocessed", dataset_id)
    if not preprocessed_storage.root_dir.exists():
        return []
    return sorted(path for path in preprocessed_storage.root_dir.iterdir() if path.is_dir())


def curated_export_if_up_to_date(
    spec: CuratePlatformSpec,
    dataset_id: str,
    rules_hash: str,
    features_meta: FeatureRunMetadata,
) -> Path | None:
    """Return the path of the latest curated export when the preprocess runs and
    the rules file have not changed.

    The function compares the current preprocess run list and the rules hash
    with the latest curated run. It returns None when you need a new curated
    export.
    """
    root = dataset_root(spec.platform, dataset_id)
    current_runs = [
        relative_run_path(root, path) for path in _preprocessed_run_dirs(spec, dataset_id)
    ]
    if features_meta.source_preprocessed_runs != current_runs:
        return None
    curated_storage = spec.storage_cls("curated", dataset_id)
    if not curated_storage.root_dir.exists():
        return None
    run_dirs = sorted(path for path in curated_storage.root_dir.iterdir() if path.is_dir())
    if not run_dirs:
        return None
    return _matching_curated_export(curated_storage, run_dirs[-1], current_runs, rules_hash)


def _matching_curated_export(
    curated_storage: StorageManager,
    latest_run_dir: Path,
    current_runs: list[str],
    rules_hash: str,
) -> Path | None:
    latest_meta = curated_storage.load_run_metadata(latest_run_dir)
    if latest_meta.get("source_preprocessed_runs") != current_runs:
        return None
    if latest_meta.get("rules_hash") != rules_hash:
        return None
    output_filename = latest_meta.get("files", {}).get("export")
    if not output_filename:
        return None
    output_path = latest_run_dir / output_filename
    if not output_path.exists():
        return None
    return output_path


def curate_with_spec(config_path: Path, dataset_id: str, spec: CuratePlatformSpec) -> Path:
    """Run curation for one platform, using the completeness and skip flags on
    ``spec``.

    Reddit and Twitter leave those flags false. Bluesky sets them true.

    Returns
    -------
    Path
        Path of the curated export CSV.

    Raises
    ------
    FileNotFoundError
        When required features metadata is missing.
    RuntimeError
        When a completeness check fails.
    """
    dataset_id = validate_dataset_id(dataset_id)
    rules_hash = hashlib.sha256(config_path.read_bytes()).hexdigest()
    features_meta = _load_and_gate_features(spec, dataset_id)
    if spec.require_all_runs_complete:
        spec.storage_cls("preprocessed", dataset_id).require_all_runs_complete(dataset_id)
    if spec.skip_if_up_to_date:
        if features_meta is None:
            raise RuntimeError(f"Features metadata required to skip curation for {dataset_id}")
        existing = curated_export_if_up_to_date(spec, dataset_id, rules_hash, features_meta)
        if existing is not None:
            print(f"curate_{spec.platform}: already up to date, skipping ({existing})")
            return existing
    return run_curation(config_path, dataset_id, spec, rules_hash=rules_hash)


def _load_and_gate_features(
    spec: CuratePlatformSpec, dataset_id: str
) -> FeatureRunMetadata | None:
    """Load features metadata when completeness or skip flags require it.

    Returns None when both ``require_features_complete`` and
    ``skip_if_up_to_date`` are false, because those callers do not read
    features metadata.
    """
    if not spec.require_features_complete and not spec.skip_if_up_to_date:
        return None
    features_meta = load_features_run_metadata(spec.platform, dataset_id)
    if spec.require_features_complete:
        require_features_complete(features_meta, dataset_id)
    return features_meta


def run_curate_main(
    *,
    spec: CuratePlatformSpec,
    configs_dir: Path,
    configs_help: str,
    dataset_id: str,
    config: Path,
) -> None:
    """Shared Typer ``main`` used by each platform curate script."""
    config_path = resolve_config_path(config, configs_dir)
    curate_with_spec(config_path, dataset_id, spec)


def make_curate_cli(
    spec: CuratePlatformSpec,
    configs_dir: Path,
    *,
    configs_help: str,
) -> Callable[[], None]:
    """Return a Typer ``main`` function for a platform curate script."""

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
