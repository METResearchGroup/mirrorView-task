"""Shared CLI helpers and orchestration for platform feature generation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pydantic import BaseModel

from data_platform.generate_features.generate_features import (
    FeatureGenerationConfig,
    generate_features,
)
from data_platform.generate_features.models import FeatureRunConfig
from data_platform.generate_features.registry import FEATURE_REGISTRY
from data_platform.utils.dataset import validate_dataset_id
from data_platform.utils.feature_labels import FeatureLabelQuery
from data_platform.utils.platform_specific_columns import PlatformSpecificColumns
from data_platform.utils.storage import StorageManager, StorageStage

StorageManagerFactory = Callable[..., StorageManager]


@dataclass(frozen=True)
class FeaturePlatformSpec:
    """FeaturePlatformSpec is the platform settings for one feature generation command.

    Whether preprocessed runs are complete is not a field on this spec.
    ``generate_platform_features`` always requires complete runs.
    """

    platform: str
    storage_cls: StorageManagerFactory
    model_cls: type[BaseModel]
    columns: PlatformSpecificColumns
    empty_message: str


def generate_feature_subset(features: list[str] | None) -> tuple[str, ...] | None:
    """Validate feature names and return a registry subset, or None to run all features."""
    if not features:
        return None
    unknown = set(features) - set(FEATURE_REGISTRY)
    if unknown:
        raise ValueError(f"Unknown features: {sorted(unknown)}")
    return tuple(features)


def features_from_cli(raw: list[str] | None) -> list[str] | None:
    """Normalize Typer --features values into a list of feature names."""
    if raw is None:
        return None
    names = [part.strip() for item in raw for part in item.split(",") if part.strip()]
    return names or None


def run_feature_generation(
    records: pd.DataFrame,
    config: FeatureGenerationConfig,
    *,
    empty_message: str,
) -> dict[str, Path]:
    if records.empty:
        print(empty_message)
        return {}
    return generate_features(records, config)


def feature_run_dir(
    feature_storage: StorageManager,
    run_dir_name: str | None,
) -> Path:
    """Return ``features/{timestamp}/``, creating the directory if needed.

    ``run_dir_name`` must be a single folder name when set. Absolute paths,
    ``.``, ``..``, and names with extra path parts are rejected here so a
    CLI ``--run-dir`` cannot write outside the features stage.
    """
    if run_dir_name is None:
        return feature_storage.create_new_run_dir()
    requested_path = Path(run_dir_name)
    if (
        requested_path.is_absolute()
        or len(requested_path.parts) != 1
        or requested_path.name in {".", ".."}
    ):
        raise ValueError("run_dir_name must be a single feature run directory name")
    return feature_storage.create_new_run_dir(run_dir_name)


def build_feature_config(
    spec: FeaturePlatformSpec,
    dataset_id: str,
    *,
    run_config: FeatureRunConfig,
    features_subset: tuple[str, ...] | None = None,
    run_dir_name: str | None = None,
) -> FeatureGenerationConfig:
    """Build a FeatureGenerationConfig for timestamped feature CSV output."""
    dataset_id = validate_dataset_id(dataset_id)
    registry = FEATURE_REGISTRY
    if features_subset:
        registry = {name: FEATURE_REGISTRY[name] for name in features_subset}

    columns = spec.columns
    feature_label_storage = StorageManager(
        spec.platform,
        StorageStage.FEATURES,
        BaseModel,
        dataset_id,
        records_filename="features",
    )
    features_dir = feature_run_dir(feature_label_storage, run_dir_name)
    return FeatureGenerationConfig(
        platform=spec.platform,
        id_column=columns.records_id_column,
        text_column=columns.text_column,
        feature_registry=registry,
        input_storage=spec.storage_cls(StorageStage.PREPROCESSED, dataset_id),
        features_dir=features_dir,
        feature_label_query=FeatureLabelQuery(
            feature_storage=feature_label_storage,
            id_column=columns.records_id_column,
            feature_file_id_column=columns.feature_file_id_column,
        ),
        run_config=run_config,
    )


def load_preprocessed_records(spec: FeaturePlatformSpec, dataset_id: str) -> pd.DataFrame:
    """Load preprocessed records from all preprocessed run dirs."""
    storage = spec.storage_cls(StorageStage.PREPROCESSED, dataset_id)
    if not storage.root_dir.exists():
        return pd.DataFrame()
    all_rows = []
    for run_dir in sorted(storage.root_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        records = storage.load_records(run_dir=run_dir)
        if records.empty:
            continue
        all_rows.extend(records.to_dict(orient="records"))
    if not all_rows:
        return pd.DataFrame()
    return pd.DataFrame(spec.model_cls.model_validate(row).model_dump() for row in all_rows)


def generate_platform_features(
    spec: FeaturePlatformSpec,
    dataset_id: str,
    *,
    batch_size: int = 64,
    max_concurrency: int = 80,
    feature_subset: list[str] | None = None,
    run_dir_name: str | None = None,
) -> dict[str, Path]:
    """The command loads platform records and generates the requested feature labels.

    Every preprocessed run for the dataset must be complete before labels
    are generated.

    Raises
    ------
    FileNotFoundError
        When the dataset has no preprocessed run directory.
    RuntimeError
        When a preprocessed run is missing ``metadata.json`` or is not
        marked complete.
    """
    dataset_id = validate_dataset_id(dataset_id)

    preprocessed_storage = spec.storage_cls(StorageStage.PREPROCESSED, dataset_id)
    if preprocessed_storage.latest_run_dir() is None:
        raise FileNotFoundError(f"No preprocessed runs found for dataset {dataset_id}")
    preprocessed_storage.require_all_runs_complete(dataset_id)

    features_subset = generate_feature_subset(feature_subset)
    run_config = FeatureRunConfig(
        batch_size=batch_size,
        max_concurrency=max_concurrency,
    )
    records = load_preprocessed_records(spec, dataset_id)
    if records.empty:
        print(spec.empty_message)
        return {}
    config = build_feature_config(
        spec,
        dataset_id,
        run_config=run_config,
        features_subset=features_subset,
        run_dir_name=run_dir_name,
    )
    return run_feature_generation(records, config, empty_message=spec.empty_message)
