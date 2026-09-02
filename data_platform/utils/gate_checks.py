from __future__ import annotations

from data_platform.generate_features.models import FeatureRunMetadata


def require_features_complete(meta: FeatureRunMetadata, dataset_id: str) -> None:
    if meta.sync_status != "completed":
        raise RuntimeError(f"Features for dataset {dataset_id} are not complete locally")
