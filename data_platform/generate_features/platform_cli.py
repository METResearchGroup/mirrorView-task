"""Shared CLI helpers and orchestration for platform feature generation.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/generate_bluesky_features.py \\
        new-run --dataset-id bluesky_<uuid> --batch-size 64
"""

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
RESUME_FLAG_ERROR = "Pass exactly one of --checkpoint or --latest"
CURRENT_DIR_NAME = "."
PARENT_DIR_NAME = ".."
DEFAULT_BATCH_SIZE = 64
DEFAULT_MAX_CONCURRENCY = 80
FEATURES_OPTION_HELP = (
    "Feature names. Repeat the flag for each feature, e.g. --features is_political"
)
CHECKPOINT_OPTION_HELP = (
    "Unfinished feature run timestamp to resume (e.g. 2026_05_30-12:00:00)"
)
LATEST_OPTION_HELP = "Resume the newest unfinished feature run for this dataset."


@dataclass(frozen=True)
class FeaturePlatformSpec:
    """Platform settings for one feature generation command."""

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
        ``resume --checkpoint`` with that feature run timestamp, or
        ``resume --latest``, to continue it.
    """
    unfinished = _unfinished_feature_run_dirs(feature_storage)
    if unfinished:
        newest = max(unfinished, key=lambda path: path.name)
        raise ValueError(
            f"An unfinished feature run exists at {newest}. "
            f"Use resume --checkpoint {newest.name} to continue that feature run"
        )
    return feature_storage.create_new_run_dir()


def _unfinished_feature_run_dirs(feature_storage: StorageManager) -> list[Path]:
    """Return feature run directories that are not marked completed.

    A directory with no ``metadata.json`` counts as unfinished. That covers a
    crash after ``create_new_run_dir()`` and before metadata is written.
    """
    if not feature_storage.root_dir.exists():
        return []
    unfinished: list[Path] = []
    for path in feature_storage.root_dir.iterdir():
        if not path.is_dir():
            continue
        metadata_path = path / METADATA_FILENAME
        if not metadata_path.exists():
            unfinished.append(path)
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
    metadata_path = run_dir / METADATA_FILENAME
    if not metadata_path.exists():
        return run_dir
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
    feature_label_storage = _feature_label_storage(spec, dataset_id)
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


def _feature_label_storage(spec: FeaturePlatformSpec, dataset_id: str) -> StorageManager:
    return StorageManager(
        spec.platform,
        StorageStage.FEATURES,
        BaseModel,
        dataset_id,
        records_filename="features",
    )


def _require_complete_preprocessed_runs(spec: FeaturePlatformSpec, dataset_id: str) -> None:
    preprocessed_storage = spec.storage_cls(StorageStage.PREPROCESSED, dataset_id)
    if preprocessed_storage.latest_run_dir() is None:
        raise FileNotFoundError(f"No preprocessed runs found for dataset {dataset_id}")
    preprocessed_storage.require_all_runs_complete(dataset_id)


def _run_platform_feature_generation(
    spec: FeaturePlatformSpec,
    dataset_id: str,
    batch_size: int,
    max_concurrency: int,
    feature_subset: list[str] | None,
    checkpoint: str | None,
    resume: bool,
) -> dict[str, Path]:
    dataset_id = validate_dataset_id(dataset_id)
    _require_complete_preprocessed_runs(spec, dataset_id)
    features_subset = generate_feature_subset(feature_subset)
    run_config = FeatureRunConfig(
        batch_size=batch_size,
        max_concurrency=max_concurrency,
    )
    records = load_preprocessed_records(spec, dataset_id)
    if records.empty:
        if checkpoint is not None:
            build_feature_config(
                spec,
                dataset_id,
                run_config=run_config,
                features_subset=features_subset,
                checkpoint=checkpoint,
            )
        print(spec.empty_message)
        return {}
    config = build_feature_config(
        spec,
        dataset_id,
        run_config=run_config,
        features_subset=features_subset,
        checkpoint=checkpoint,
    )
    return run_feature_generation(
        records, config, spec.empty_message, resume
    )


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
    FileNotFoundError
        When the dataset has no preprocessed run directory.
    RuntimeError
        When a preprocessed run is missing ``metadata.json`` or is not
        marked complete.
    ValueError
        When an unfinished feature run already exists for this dataset.
    """
    return _run_platform_feature_generation(
        spec,
        dataset_id,
        batch_size,
        max_concurrency,
        feature_subset,
        checkpoint=None,
        resume=False,
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
    unfinished = _unfinished_feature_run_dirs(feature_storage)
    if not unfinished:
        raise FileNotFoundError(
            f"No unfinished feature run exists under {feature_storage.root_dir}"
        )
    return max(unfinished, key=lambda path: path.name)


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
    if (checkpoint is not None and latest) or (checkpoint is None and not latest):
        raise ValueError(RESUME_FLAG_ERROR)
    if checkpoint is not None:
        return checkpoint
    return require_latest_unfinished_feature_run_dir(feature_storage).name


def generate_platform_features_from_checkpoint(
    spec: FeaturePlatformSpec,
    dataset_id: str,
    checkpoint: str,
    batch_size: int = 64,
    max_concurrency: int = 80,
    feature_subset: list[str] | None = None,
) -> dict[str, Path]:
    """Resume an unfinished feature run and generate the requested labels.

    Parameters
    ----------
    spec
        Platform storage, model, and column spec.
    dataset_id
        Dataset identifier from ingestion YAML.
    checkpoint
        Named unfinished ``features/{timestamp}/`` folder.
    batch_size
        Label batch size.
    max_concurrency
        Engine concurrency cap.
    feature_subset
        Optional registry subset. None runs every feature.

    Returns
    -------
    dict[str, Path]
        Feature name to the label file written in the resumed feature run folder.

    Raises
    ------
    ValueError
        When the named feature run is already completed.
    FileNotFoundError
        When the named feature run folder is missing.
    """
    return _run_platform_feature_generation(
        spec,
        dataset_id,
        batch_size,
        max_concurrency,
        feature_subset,
        checkpoint=checkpoint,
        resume=True,
    )


def build_feature_cli_app(
    spec: FeaturePlatformSpec,
    dataset_id_help: str,
) -> typer.Typer:
    """Return a Typer app with separate ``new-run`` and ``resume`` commands.

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
        """Start a new feature run under features/{timestamp}/. If an unfinished feature run already exists, you get an error."""
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
        """Resume an unfinished feature run. Pass exactly one of --checkpoint or --latest."""
        dataset_id = validate_dataset_id(dataset_id)
        run_name = resolve_resume_checkpoint(
            _feature_label_storage(spec, dataset_id),
            checkpoint,
            latest,
        )
        generate_platform_features_from_checkpoint(
            spec,
            dataset_id,
            run_name,
            batch_size=batch_size,
            max_concurrency=max_concurrency,
            feature_subset=features_from_cli(features),
        )

    return app
