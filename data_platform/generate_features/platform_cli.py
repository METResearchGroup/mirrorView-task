"""Shared CLI helpers and orchestration for platform feature generation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import typer
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
from data_platform.utils.storage import METADATA_FILENAME, StorageManager, StorageStage

StorageManagerFactory = Callable[..., StorageManager]

FEATURE_RUN_COMPLETED_STATUS = "completed"
FEATURE_CHECKPOINT_NAME_ERROR = "checkpoint must be a single feature run directory name"
RESUME_FLAG_ERROR = "Pass --checkpoint or --latest, but not both"
CURRENT_DIR_NAME = "."
PARENT_DIR_NAME = ".."
DEFAULT_BATCH_SIZE = 64
DEFAULT_MAX_CONCURRENCY = 80
FEATURES_OPTION_HELP = (
    "Feature name(s); repeat the flag per feature, e.g. --features is_political"
)
CHECKPOINT_OPTION_HELP = (
    "Unfinished feature run timestamp to resume (e.g. 2026_05_30-12:00:00)"
)
LATEST_OPTION_HELP = "Resume the newest unfinished feature run for this dataset."


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
    empty_message: str,
    resume: bool,
) -> dict[str, Path]:
    if records.empty:
        print(empty_message)
        return {}
    return generate_features(records, config, resume)


def _require_single_feature_run_name(checkpoint: str) -> str:
    """Return a single folder name. Raise if the value is an absolute path, ``.``, ``..``, or a name with extra path parts.

    Parameters
    ----------
    checkpoint
        Feature run timestamp, for example ``2026_05_30-12:00:00``.

    Returns
    -------
    str
        The validated folder name.

    Raises
    ------
    ValueError
        When ``checkpoint`` is not a single folder name.
    """
    requested_path = Path(checkpoint)
    if (
        requested_path.is_absolute()
        or len(requested_path.parts) != 1
        or requested_path.name in {CURRENT_DIR_NAME, PARENT_DIR_NAME}
    ):
        raise ValueError(FEATURE_CHECKPOINT_NAME_ERROR)
    return checkpoint


def _start_new_feature_run(feature_storage: StorageManager) -> Path:
    """Create a new ``features/{timestamp}/`` folder for this dataset.

    Raises
    ------
    ValueError
        When an unfinished feature run already exists. The operator must pass
        ``--checkpoint`` with that folder's timestamp to resume it.
    """
    unfinished = _unfinished_feature_run_dirs(feature_storage)
    if unfinished:
        newest = max(unfinished, key=lambda path: path.name)
        raise ValueError(
            f"An unfinished feature run exists at {newest}; "
            f"pass --checkpoint {newest.name} to resume it"
        )
    return feature_storage.create_new_run_dir()


def _unfinished_feature_run_dirs(feature_storage: StorageManager) -> list[Path]:
    """Return feature run directories whose metadata is not completed."""
    if not feature_storage.root_dir.exists():
        return []
    unfinished: list[Path] = []
    for path in feature_storage.root_dir.iterdir():
        if not path.is_dir():
            continue
        metadata_path = path / METADATA_FILENAME
        if not metadata_path.exists():
            continue
        metadata = feature_storage.load_run_metadata(path)
        if metadata.get("sync_status") != FEATURE_RUN_COMPLETED_STATUS:
            unfinished.append(path)
    return unfinished


def _load_feature_checkpoint(feature_storage: StorageManager, checkpoint: str) -> Path:
    """Return an existing unfinished ``features/{timestamp}/`` folder. If that folder is missing, raise instead of creating it.

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
    run_name = _require_single_feature_run_name(checkpoint)
    run_dir = feature_storage.root_dir / run_name
    if not run_dir.is_dir():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")
    metadata = feature_storage.load_run_metadata(run_dir)
    if metadata.get("sync_status") == FEATURE_RUN_COMPLETED_STATUS:
        raise ValueError(f"Run is already completed: {run_dir}")
    return run_dir


def feature_run_dir(
    feature_storage: StorageManager,
    checkpoint: str | None,
) -> Path:
    """Return ``features/{timestamp}/`` for a new run or an unfinished checkpoint.

    If ``checkpoint`` is None, this starts a new timestamped folder. If you pass
    ``checkpoint``, this returns that existing unfinished folder.

    Parameters
    ----------
    checkpoint
        Timestamp of an existing unfinished feature run to resume. Pass None
        when you want a new run.

    Returns
    -------
    Path
        The feature run directory. Resume paths return the existing folder
        without creating a new one.

    Raises
    ------
    ValueError
        If ``checkpoint`` is not a single folder name, if you start a new run
        while an unfinished run exists, or if the named run is already
        completed.
    FileNotFoundError
        When the named checkpoint folder is missing.
    """
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
) -> FeatureGenerationConfig:
    """Build a FeatureGenerationConfig for timestamped feature CSV output.

    Parameters
    ----------
    checkpoint
        Existing ``features/{timestamp}/`` folder to resume. Pass None when
        you want a new run.
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
    features_dir = feature_run_dir(feature_label_storage, checkpoint)
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
    batch_size: int = 64,
    max_concurrency: int = 80,
    feature_subset: list[str] | None = None,
) -> dict[str, Path]:
    """Start a new feature run and generate the requested feature labels.

    Parameters
    ----------
    spec
        Platform storage, model, and column spec.
    dataset_id
        Dataset identifier from ingestion YAML.
    batch_size
        Label batch size.
    max_concurrency
        Engine concurrency cap.
    feature_subset
        Optional registry subset. None runs every feature.

    Returns
    -------
    dict[str, Path]
        Feature name to the label file written in the new folder.

    Raises
    ------
    ValueError
        When an unfinished feature run already exists for this dataset.
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
    )
    return run_feature_generation(
        records, config, spec.empty_message, resume=False
    )


def require_latest_unfinished_feature_run_dir(feature_storage: StorageManager) -> Path:
    """Return the newest unfinished feature run directory for this dataset.

    Parameters
    ----------
    feature_storage
        Features-stage storage manager for the dataset.

    Returns
    -------
    Path
        Newest feature run directory whose ``sync_status`` is not completed.

    Raises
    ------
    FileNotFoundError
        When no unfinished feature run exists.
    """
    raise NotImplementedError


def resolve_resume_checkpoint(
    feature_storage: StorageManager,
    checkpoint: str | None,
    latest: bool,
) -> str:
    """Return the feature run folder name to resume.

    Parameters
    ----------
    feature_storage
        Features-stage storage manager for the dataset.
    checkpoint
        Named unfinished feature run timestamp, or None when using ``latest``.
    latest
        When True, resume the newest unfinished feature run.

    Returns
    -------
    str
        Single folder name under ``features/``.

    Raises
    ------
    ValueError
        When both ``checkpoint`` and ``latest`` are set, or when neither is set.
    FileNotFoundError
        When ``latest`` is set and no unfinished feature run exists.
    """
    raise NotImplementedError


def generate_platform_features_from_checkpoint(
    spec: FeaturePlatformSpec,
    dataset_id: str,
    checkpoint: str | None,
    latest: bool,
    batch_size: int,
    max_concurrency: int,
    feature_subset: list[str] | None,
) -> dict[str, Path]:
    """Resume an unfinished feature run and generate the requested labels.

    Parameters
    ----------
    spec
        Platform storage, model, and column spec.
    dataset_id
        Dataset identifier from ingestion YAML.
    checkpoint
        Named unfinished ``features/{timestamp}/`` folder, or None with ``latest``.
    latest
        When True, resume the newest unfinished feature run.
    batch_size
        Label batch size.
    max_concurrency
        Engine concurrency cap.
    feature_subset
        Optional registry subset. None runs every feature.

    Returns
    -------
    dict[str, Path]
        Feature name to the label file written in the resumed folder.

    Raises
    ------
    ValueError
        When both resume flags are set, neither is set, or the named run is
        already completed.
    FileNotFoundError
        When the named folder is missing, or when ``latest`` finds no
        unfinished run.
    """
    raise NotImplementedError


def build_feature_cli_app(
    spec: FeaturePlatformSpec,
    dataset_id_help: str,
) -> typer.Typer:
    """Return a Typer app with exclusive ``new-run`` and ``resume`` commands.

    Parameters
    ----------
    spec
        Platform storage, model, and column spec.
    dataset_id_help
        Help text for ``--dataset-id``.

    Returns
    -------
    typer.Typer
        CLI that requires ``new-run`` or ``resume``.
    """
    app = typer.Typer(no_args_is_help=True)

    @app.command("new-run")
    def new_run_command(
        dataset_id: str = typer.Option(..., "--dataset-id", help=dataset_id_help),
        batch_size: int = typer.Option(DEFAULT_BATCH_SIZE, "--batch-size"),
        max_concurrency: int = typer.Option(
            DEFAULT_MAX_CONCURRENCY, "--max-concurrency"
        ),
        features: list[str] | None = typer.Option(
            None,
            "--features",
            help=FEATURES_OPTION_HELP,
        ),
    ) -> None:
        generate_platform_features(
            spec,
            dataset_id,
            batch_size=batch_size,
            max_concurrency=max_concurrency,
            feature_subset=features_from_cli(features),
        )

    @app.command("resume")
    def resume_command(
        dataset_id: str = typer.Option(..., "--dataset-id", help=dataset_id_help),
        batch_size: int = typer.Option(DEFAULT_BATCH_SIZE, "--batch-size"),
        max_concurrency: int = typer.Option(
            DEFAULT_MAX_CONCURRENCY, "--max-concurrency"
        ),
        features: list[str] | None = typer.Option(
            None,
            "--features",
            help=FEATURES_OPTION_HELP,
        ),
        checkpoint: str | None = typer.Option(
            None,
            "--checkpoint",
            help=CHECKPOINT_OPTION_HELP,
        ),
        latest: bool = typer.Option(
            False,
            "--latest",
            help=LATEST_OPTION_HELP,
        ),
    ) -> None:
        generate_platform_features_from_checkpoint(
            spec,
            dataset_id,
            checkpoint,
            latest,
            batch_size,
            max_concurrency,
            features_from_cli(features),
        )

    return app
