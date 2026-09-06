"""Load and flush features/{timestamp}/metadata.json for resumable feature generation.

Create a new run with ``init_feature_run_metadata``. Resume an unfinished run
with ``load_feature_run_metadata``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from data_platform.generate_features.models import (
    FeatureGenerationConfig,
    FeatureRunMetadata,
    FeatureSpec,
    FeatureStatus,
)
from data_platform.utils.dataset import dataset_root, relative_run_path
from data_platform.utils.storage import METADATA_FILENAME
from lib.constants import DEFAULT_BEDROCK_NOVA_MICRO, DEFAULT_LLM_MODEL
from lib.timestamp_utils import get_current_timestamp

PERSPECTIVE_MODEL_ID = "perspective-api"


def metadata_path(features_dir: Path) -> Path:
    """Return the path to metadata.json in a feature run directory."""
    return features_dir / METADATA_FILENAME


def flush_metadata(features_dir: Path, metadata: FeatureRunMetadata) -> None:
    """Atomically write metadata.json under features_dir with an updated timestamp."""
    features_dir.mkdir(parents=True, exist_ok=True)
    metadata.updated_at = get_current_timestamp()
    path = metadata_path(features_dir)
    tmp_path = features_dir / f"{METADATA_FILENAME}.tmp"
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(metadata.to_dict(), f, indent=2)
    tmp_path.replace(path)


def resolve_source_preprocessed_runs(config: FeatureGenerationConfig) -> list[str]:
    """Return relative paths for all preprocessed run dirs for this dataset."""
    root = dataset_root(config.platform, config.input_storage.dataset_id)
    preprocessed_root = config.input_storage.root_dir
    if not preprocessed_root.exists():
        return []
    return [
        relative_run_path(root, run_dir)
        for run_dir in sorted(preprocessed_root.iterdir())
        if run_dir.is_dir()
    ]


def prompt_hash(system_prompt: str | None) -> str | None:
    """Return a SHA-256 hex digest of ``system_prompt``, or None when omitted."""
    if system_prompt is None:
        return None
    return hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()


def model_id_for_spec(spec: FeatureSpec) -> str:
    """Return the default LLM model id, or Perspective for thread-pool features."""
    if spec.engine_type == "thread_pool":
        return PERSPECTIVE_MODEL_ID
    if spec.engine_type == "bedrock":
        return DEFAULT_BEDROCK_NOVA_MICRO
    return DEFAULT_LLM_MODEL


def _stamp_or_check_identity(
    metadata: FeatureRunMetadata,
    config: FeatureGenerationConfig,
    feature_names: tuple[str, ...],
) -> None:
    for name in feature_names:
        spec = config.feature_registry.get(name)
        if spec is None:
            continue
        model_id = model_id_for_spec(spec)
        hashed_prompt = prompt_hash(spec.system_prompt)
        status = metadata.features.setdefault(name, FeatureStatus())
        if status.model_id is None and status.prompt_hash is None:
            status.model_id = model_id
            status.prompt_hash = hashed_prompt
            continue
        if status.model_id != model_id or status.prompt_hash != hashed_prompt:
            raise ValueError(
                f"Feature {name} identity changed for this run directory. "
                "You cannot resume this folder. Remove or complete this unfinished "
                "run before starting a new generate_features run."
            )


def init_feature_run_metadata(
    config: FeatureGenerationConfig,
    feature_names: tuple[str, ...],
) -> FeatureRunMetadata:
    """Create metadata.json for a new feature run.

    Parameters
    ----------
    config
        Feature generation config whose ``features_dir`` is the new run folder.
    feature_names
        Registry names to stamp as pending features.

    Returns
    -------
    FeatureRunMetadata
        In-progress metadata flushed to disk.

    Raises
    ------
    ValueError
        When ``metadata.json`` already exists in this folder.
    """
    path = metadata_path(config.features_dir)
    if path.exists():
        raise ValueError(f"Feature run metadata already exists: {path}")
    source_preprocessed_runs = resolve_source_preprocessed_runs(config)
    features = {name: FeatureStatus() for name in feature_names}
    metadata = FeatureRunMetadata(
        dataset_id=config.input_storage.dataset_id,
        source_preprocessed_runs=source_preprocessed_runs,
        sync_status="in_progress",
        features=features,
        config=config.run_config,
        updated_at=get_current_timestamp(),
    )
    _stamp_or_check_identity(metadata, config, feature_names)
    flush_metadata(config.features_dir, metadata)
    return metadata


def load_feature_run_metadata(
    config: FeatureGenerationConfig,
    feature_names: tuple[str, ...],
) -> FeatureRunMetadata:
    """Load metadata.json for an unfinished feature run.

    Parameters
    ----------
    config
        Feature generation config whose ``features_dir`` is the resume folder.
    feature_names
        Registry names whose model and prompt identity must still match.

    Returns
    -------
    FeatureRunMetadata
        Existing metadata, with identity stamps checked.

    Raises
    ------
    FileNotFoundError
        When ``metadata.json`` is missing.
    ValueError
        When the run is already completed, or when model or prompt identity
        no longer matches this folder.
    """
    path = metadata_path(config.features_dir)
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(encoding="utf-8") as handle:
        metadata = FeatureRunMetadata.from_dict(json.load(handle))
    if metadata.sync_status == "completed":
        raise ValueError(f"Run is already completed: {config.features_dir}")
    metadata.source_preprocessed_runs = resolve_source_preprocessed_runs(config)
    _stamp_or_check_identity(metadata, config, feature_names)
    flush_metadata(config.features_dir, metadata)
    return metadata


def mark_feature_in_progress(
    metadata: FeatureRunMetadata,
    feature_name: str,
) -> FeatureRunMetadata:
    """Mark one feature as in_progress and set the overall sync status accordingly."""
    status = metadata.features.setdefault(feature_name, FeatureStatus())
    status.status = "in_progress"
    metadata.sync_status = "in_progress"
    return metadata


def mark_feature_completed(
    metadata: FeatureRunMetadata,
    feature_name: str,
    labeled: int,
) -> FeatureRunMetadata:
    """Mark one feature completed and record its final labeled row count."""
    status = metadata.features.setdefault(feature_name, FeatureStatus())
    status.status = "completed"
    status.labeled = labeled
    return metadata


def update_batch_counts(
    metadata: FeatureRunMetadata,
    feature_name: str,
    labeled_delta: int,
    failed_batches_delta: int,
) -> FeatureRunMetadata:
    """Increment labeled and failed-batch counters after an atomic batch finishes."""
    status = metadata.features.setdefault(feature_name, FeatureStatus())
    status.labeled += labeled_delta
    status.failed_batches += failed_batches_delta
    return metadata


def set_sync_status_completed(metadata: FeatureRunMetadata) -> FeatureRunMetadata:
    """Set sync_status to completed when every feature in the registry has finished."""
    metadata.sync_status = "completed"
    return metadata
