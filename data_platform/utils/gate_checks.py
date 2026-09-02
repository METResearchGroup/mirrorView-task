from __future__ import annotations

from data_platform.generate_features.models import FeatureRunMetadata
from data_platform.utils.storage import StorageManager


def require_all_runs_complete(storage: StorageManager, dataset_id: str) -> None:
    """Raise when the stage has no run directory, or when a run is incomplete."""
    storage.require_all_runs_complete(dataset_id)


def require_features_complete(meta: FeatureRunMetadata, dataset_id: str) -> None:
    if meta.sync_status != "completed":
        raise RuntimeError(f"Features for dataset {dataset_id} are not complete locally")
