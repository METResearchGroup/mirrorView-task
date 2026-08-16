from __future__ import annotations

from data_platform.generate_features.models import FeatureRunMetadata
from data_platform.utils.storage import StorageManager


def require_all_runs_complete(storage: StorageManager, dataset_id: str) -> None:
    if not storage.all_runs_complete():
        raise RuntimeError(
            f"Not all {storage.stage} runs for dataset {dataset_id} are complete locally"
        )


def require_features_complete(meta: FeatureRunMetadata, dataset_id: str) -> None:
    if meta.sync_status != "completed":
        raise RuntimeError(f"Features for dataset {dataset_id} are not complete locally")
