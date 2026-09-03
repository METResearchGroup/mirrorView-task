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

FEATURE_RUN_COMPLETED_STATUS = "completed"
FEATURE_CHECKPOINT_NAME_ERROR = "checkpoint must be a single feature run directory name"
FEATURE_CHECKPOINT_OR_LATEST_ERROR = "Pass --checkpoint or --latest, but not both"
CURRENT_DIR_NAME = "."
PARENT_DIR_NAME = ".."


@dataclass(frozen=True)
class FeaturePlatformSpec:
    platform: str
    storage_cls: StorageManagerFactory
    model_cls: type[BaseModel]
    columns: PlatformSpecificColumns
    empty_message: str
    require_all_runs_complete: bool = False


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


def _require_single_feature_run_name(checkpoint: str) -> str:
    """Return a single folder name, or raise if the value could escape the features stage.

    Parameters
    ----------
    checkpoint
        Feature run timestamp, for example ``2026_05_30-12:00:00``. Absolute
        paths, ``.``, ``..``, and names with extra path parts are rejected.

    Returns
    -------
    str
        The validated folder name.

    Raises
    ------
    ValueError
        When ``checkpoint`` is not a single folder name.
    """
    raise NotImplementedError


def _start_new_feature_run(feature_storage: StorageManager) -> Path:
    """Create a new ``features/{timestamp}/`` folder for this dataset.

    Raises
    ------
    ValueError
        When an unfinished feature run already exists. The operator must pass
        ``--checkpoint`` or ``--latest`` to resume it.
    """
    raise NotImplementedError


def _load_feature_checkpoint(feature_storage: StorageManager, checkpoint: str) -> Path:
    """Return an existing unfinished ``features/{timestamp}/`` folder.

    Does not create a missing folder.

    Parameters
    ----------
    checkpoint
        Feature run timestamp directory name.

    Raises
    ------
    FileNotFoundError
        When the named folder does not exist.
    ValueError
        When ``checkpoint`` is not a single folder name, or when the run is
        already completed.
    """
    raise NotImplementedError


def _latest_unfinished_feature_run_dir(feature_storage: StorageManager) -> Path:
    """Return the newest unfinished feature run directory for this dataset.

    Raises
    ------
    FileNotFoundError
        When no unfinished feature run exists.
    """
    raise NotImplementedError


def feature_run_dir(
    feature_storage: StorageManager,
    checkpoint: str | None,
    latest: bool,
) -> Path:
    """Return ``features/{timestamp}/`` for a new run or an unfinished checkpoint.

    Neither ``checkpoint`` nor ``latest`` starts a new timestamped folder.
    ``checkpoint`` loads that folder. ``latest`` loads the newest unfinished
    folder. Exactly one of ``checkpoint`` or ``latest`` is required to resume.
    The two resume options cannot be combined.

    Parameters
    ----------
    checkpoint
        Existing feature run timestamp to resume, or None to start a new run
        when ``latest`` is False.
    latest
        When True, resume the newest unfinished feature run.

    Returns
    -------
    Path
        The feature run directory. Resume paths return the existing folder
        without creating a new one.

    Raises
    ------
    ValueError
        When both resume options are set, when ``checkpoint`` is not a single
        folder name, when a new run is requested while an unfinished run
        exists, or when the named run is already completed.
    FileNotFoundError
        When the named checkpoint folder is missing, or when ``latest`` is set
        and no unfinished feature run exists.
    """
    if checkpoint is not None and latest:
        raise ValueError(FEATURE_CHECKPOINT_OR_LATEST_ERROR)
    if latest:
        return _latest_unfinished_feature_run_dir(feature_storage)
    if checkpoint is not None:
        return _load_feature_checkpoint(feature_storage, checkpoint)
    return _start_new_feature_run(feature_storage)


def build_feature_config(
    spec: FeaturePlatformSpec,
    dataset_id: str,
    *,
    run_config: FeatureRunConfig,
    features_subset: tuple[str, ...] | None = None,
    checkpoint: str | None = None,
    latest: bool = False,
) -> FeatureGenerationConfig:
    """Build a FeatureGenerationConfig for timestamped feature CSV output.

    Parameters
    ----------
    checkpoint
        Existing ``features/{timestamp}/`` folder to resume. None starts a new
        run when ``latest`` is False.
    latest
        When True, resume the newest unfinished feature run.
    """
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
    features_dir = feature_run_dir(feature_label_storage, checkpoint, latest)
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
    checkpoint: str | None = None,
    latest: bool = False,
) -> dict[str, Path]:
    """Load platform records and generate the requested feature labels.

    Parameters
    ----------
    checkpoint
        Existing ``features/{timestamp}/`` folder to resume. None starts a new
        run when ``latest`` is False.
    latest
        When True, resume the newest unfinished feature run.
    """
    dataset_id = validate_dataset_id(dataset_id)

    if spec.require_all_runs_complete:
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
        checkpoint=checkpoint,
        latest=latest,
    )
    return run_feature_generation(records, config, empty_message=spec.empty_message)
