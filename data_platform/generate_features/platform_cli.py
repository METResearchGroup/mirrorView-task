"""Shared CLI helpers and orchestration for platform feature generation.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/generate_bluesky_features.py \\
        --dataset-id bluesky_<uuid> --batch-size 64
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
    generate_campaign_feature,
    generate_features,
)
from data_platform.generate_features.models import CampaignRunConfig, FeatureRunConfig
from data_platform.generate_features.registry import FEATURE_REGISTRY
from data_platform.utils.dataset import validate_dataset_id
from data_platform.utils.feature_labels import FeatureLabelQuery
from data_platform.utils.platform_specific_columns import PlatformSpecificColumns
from data_platform.utils.storage import METADATA_FILENAME, StorageManager, StorageStage

StorageManagerFactory = Callable[..., StorageManager]

FEATURE_RUN_COMPLETED_STATUS = "completed"
FEATURE_CHECKPOINT_NAME_ERROR = "checkpoint must be a single feature run directory name"
CURRENT_DIR_NAME = "."
PARENT_DIR_NAME = ".."
DEFAULT_BATCH_SIZE = 64
DEFAULT_MAX_CONCURRENCY = 80
FEATURES_OPTION_HELP = (
    "Feature names. Repeat the flag for each feature, e.g. --features is_political"
)
CHECKPOINT_OPTION_HELP = (
    "Unfinished feature run timestamp to continue (e.g. 2026_05_30-12:00:00). "
    "Omit this flag to start a new feature run."
)
CAMPAIGN_BATCH_SIZE = 2000
CAMPAIGN_ID_OPTION_HELP = (
    "S3 campaign id (e.g. bluesky_2026_09_03_235130_llm_features_v1). Requires "
    "--preprocessed-run, exactly one --features value, and --batch-size 2000. "
    "Re-running the same command resumes from the campaign prefix in S3."
)
PREPROCESSED_RUN_OPTION_HELP = (
    "Preprocessed run timestamp to label in campaign mode (e.g. 2026_09_03-23:51:30)."
)
CAMPAIGN_FLAGS_TOGETHER_ERROR = "--campaign-id and --preprocessed-run must be passed together"
CAMPAIGN_CHECKPOINT_ERROR = "--checkpoint cannot be combined with --campaign-id"
CAMPAIGN_BATCH_SIZE_ERROR = f"campaign mode requires --batch-size {CAMPAIGN_BATCH_SIZE}"
CAMPAIGN_SINGLE_FEATURE_ERROR = "campaign mode requires exactly one --features value"
CAMPAIGN_ENGINE_ERROR = "campaign mode requires a feature with engine_type 'openai'"
PREPROCESSED_RUN_NAME_ERROR = "preprocessed-run must be a single run directory name"


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
        When an unfinished feature run already exists. Pass ``--checkpoint``
        with that feature run timestamp to continue it.
    """
    unfinished = _unfinished_feature_run_dirs(feature_storage)
    if unfinished:
        newest = max(unfinished, key=lambda path: path.name)
        raise ValueError(
            f"An unfinished feature run exists at {newest}. "
            f"Pass --checkpoint {newest.name} to continue that feature run"
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
        records, config, spec.empty_message, resume=checkpoint is not None
    )


def generate_platform_features(
    spec: FeaturePlatformSpec,
    dataset_id: str,
    *,
    batch_size: int = 64,
    max_concurrency: int = 80,
    feature_subset: list[str] | None = None,
    checkpoint: str | None = None,
) -> dict[str, Path]:
    """Generate the requested feature labels in a new or unfinished feature run.

    Omit ``checkpoint`` to start a new feature run folder. Pass ``checkpoint``
    to continue that unfinished feature run.

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
    checkpoint
        Named unfinished ``features/{timestamp}/`` folder. Pass None to start
        a new feature run.

    Returns
    -------
    dict[str, Path]
        Feature name to the label file written in the feature run folder.

    Raises
    ------
    FileNotFoundError
        When the dataset has no preprocessed run directory, or when the named
        feature run folder is missing.
    RuntimeError
        When a preprocessed run is missing ``metadata.json`` or is not
        marked complete.
    ValueError
        When ``checkpoint`` is omitted and an unfinished feature run already
        exists, or when the named feature run is already completed.
    """
    return _run_platform_feature_generation(
        spec,
        dataset_id,
        batch_size,
        max_concurrency,
        feature_subset,
        checkpoint=checkpoint,
    )


def load_pinned_preprocessed_records(
    spec: FeaturePlatformSpec,
    dataset_id: str,
    preprocessed_run: str,
) -> pd.DataFrame:
    """Load and validate the rows of one named preprocessed run.

    Raises
    ------
    ValueError
        When ``preprocessed_run`` is not a single folder name.
    FileNotFoundError
        When that run has no records file.
    """
    if not _is_single_dir_name(preprocessed_run):
        raise ValueError(PREPROCESSED_RUN_NAME_ERROR)
    storage = spec.storage_cls(StorageStage.PREPROCESSED, dataset_id)
    records = storage.load_records(run_dir=storage.root_dir / preprocessed_run)
    if records.empty:
        return pd.DataFrame()
    return pd.DataFrame(
        spec.model_cls.model_validate(row).model_dump()
        for row in records.to_dict(orient="records")
    )


def _is_single_dir_name(value: str) -> bool:
    path = Path(value)
    return (
        not path.is_absolute()
        and len(path.parts) == 1
        and path.name not in {CURRENT_DIR_NAME, PARENT_DIR_NAME}
    )


def _require_campaign_flags(
    campaign_id: str | None,
    preprocessed_run: str | None,
    feature_subset: list[str] | None,
    batch_size: int,
    checkpoint: str | None,
) -> tuple[str, str, str]:
    """Return ``(campaign_id, preprocessed_run, feature_name)`` or raise ``ValueError`` naming the bad flag."""
    if campaign_id is None or preprocessed_run is None:
        raise ValueError(CAMPAIGN_FLAGS_TOGETHER_ERROR)
    if checkpoint is not None:
        raise ValueError(CAMPAIGN_CHECKPOINT_ERROR)
    if batch_size != CAMPAIGN_BATCH_SIZE:
        raise ValueError(CAMPAIGN_BATCH_SIZE_ERROR)
    if not feature_subset or len(feature_subset) != 1:
        raise ValueError(CAMPAIGN_SINGLE_FEATURE_ERROR)
    (feature_name,) = generate_feature_subset(feature_subset) or ()
    if FEATURE_REGISTRY[feature_name].engine_type != "openai":
        raise ValueError(CAMPAIGN_ENGINE_ERROR)
    return campaign_id, preprocessed_run, feature_name


def generate_platform_campaign_feature(
    spec: FeaturePlatformSpec,
    dataset_id: str,
    *,
    campaign_id: str | None,
    preprocessed_run: str | None,
    feature_subset: list[str] | None,
    batch_size: int,
    checkpoint: str | None = None,
) -> str:
    """Run campaign mode for exactly one feature and return its S3 feature prefix URI.

    Re-running with the same flags resumes from the manifest under that prefix.

    Raises
    ------
    ValueError
        When only one of ``campaign_id`` and ``preprocessed_run`` is given, when
        ``checkpoint`` is given, when ``batch_size`` is not 2000, or when
        ``feature_subset`` does not name exactly one OpenAI feature.
    FileNotFoundError
        When the named preprocessed run has no records file.
    """
    campaign_id, preprocessed_run, feature_name = _require_campaign_flags(
        campaign_id, preprocessed_run, feature_subset, batch_size, checkpoint
    )
    dataset_id = validate_dataset_id(dataset_id)
    records = load_pinned_preprocessed_records(spec, dataset_id, preprocessed_run)
    campaign = CampaignRunConfig(
        campaign_id=campaign_id,
        dataset_id=dataset_id,
        preprocessed_run=preprocessed_run,
        platform=spec.platform,
        batch_size=batch_size,
    )
    paths = generate_campaign_feature(
        records,
        FEATURE_REGISTRY[feature_name],
        campaign,
        FeatureRunConfig(batch_size=batch_size),
    )
    prefix_uri = paths.uri(paths.prefix)
    print(f"generate_features: campaign {campaign_id} {feature_name} -> {prefix_uri}")
    return prefix_uri


def build_feature_cli_main(spec: FeaturePlatformSpec, dataset_id_help: str):
    """Return the Typer command for one platform feature-generation script."""

    def main(
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
        campaign_id: str | None = typer.Option(
            None, "--campaign-id", help=CAMPAIGN_ID_OPTION_HELP
        ),
        preprocessed_run: str | None = typer.Option(
            None, "--preprocessed-run", help=PREPROCESSED_RUN_OPTION_HELP
        ),
    ) -> None:
        """Generate feature labels. Pass --checkpoint to continue an unfinished feature run, or --campaign-id with --preprocessed-run for S3 campaign mode."""
        if campaign_id is not None or preprocessed_run is not None:
            generate_platform_campaign_feature(
                spec,
                dataset_id,
                campaign_id=campaign_id,
                preprocessed_run=preprocessed_run,
                feature_subset=features_from_cli(features),
                batch_size=batch_size,
                checkpoint=checkpoint,
            )
            return
        generate_platform_features(
            spec,
            dataset_id,
            batch_size=batch_size,
            max_concurrency=max_concurrency,
            feature_subset=features_from_cli(features),
            checkpoint=checkpoint,
        )

    return main


def build_feature_cli_app(
    spec: FeaturePlatformSpec,
    dataset_id_help: str,
) -> typer.Typer:
    """Return a Typer app whose optional ``--checkpoint`` continues an unfinished feature run.

    Parameters
    ----------
    spec
        Platform storage, model, and column spec.
    dataset_id_help
        Help text for ``--dataset-id``.

    Returns
    -------
    typer.Typer
        CLI that starts a new feature run unless ``--checkpoint`` is passed.
    """
    app = typer.Typer()
    app.command()(build_feature_cli_main(spec, dataset_id_help))
    return app
