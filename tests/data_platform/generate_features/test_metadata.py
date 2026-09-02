from __future__ import annotations

import json

import pytest

from data_platform.generate_features.metadata import (
    flush_metadata,
    load_or_init_metadata,
    mark_feature_completed,
    mark_feature_in_progress,
    metadata_path,
    set_sync_status_completed,
    update_batch_counts,
)
from data_platform.generate_features.models import (
    FeatureRunConfig,
    FeatureRunMetadata,
    FeatureStatus,
)
from tests.data_platform.constants import FEATURES_DATASET_ID, PREPROCESSED_RUN
from data_platform.generate_features.registry import FEATURE_REGISTRY
from lib.constants import DEFAULT_LLM_MODEL
from tests.data_platform.generate_features.conftest import make_feature_generation_config


def test_load_or_init_metadata_creates_file(features_dir) -> None:
    config = make_feature_generation_config(
        features_dir,
        run_config=FeatureRunConfig(batch_size=32, opik_enabled=False),
    )
    metadata = load_or_init_metadata(
        config,
        feature_names=("is_political",),
    )
    assert metadata_path(features_dir).exists()
    assert metadata.features["is_political"].status == "pending"
    assert metadata.config.batch_size == 32


def test_flush_metadata_round_trip(features_dir) -> None:
    metadata = FeatureRunMetadata(
        dataset_id=FEATURES_DATASET_ID,
        source_preprocessed_runs=[PREPROCESSED_RUN],
        config=FeatureRunConfig(),
    )
    metadata.features["is_political"] = FeatureStatus()
    mark_feature_in_progress(metadata, "is_political")
    update_batch_counts(metadata, "is_political", labeled_delta=5, failed_batches_delta=1)
    mark_feature_completed(metadata, "is_political", labeled=5)
    set_sync_status_completed(metadata)
    flush_metadata(features_dir, metadata)

    with metadata_path(features_dir).open(encoding="utf-8") as f:
        data = json.load(f)
    assert data["sync_status"] == "completed"
    assert data["features"]["is_political"]["labeled"] == 5
    assert data["features"]["is_political"]["failed_batches"] == 1


def test_load_or_init_metadata_records_feature_identity(features_dir) -> None:
    """Given a new feature run, when metadata is created, then prompt/model identity is stored."""
    spec = FEATURE_REGISTRY["is_political"]
    config = make_feature_generation_config(
        features_dir,
        feature_registry={"is_political": spec},
    )

    metadata = load_or_init_metadata(config, feature_names=("is_political",))

    assert metadata.features["is_political"].model_id == DEFAULT_LLM_MODEL
    assert metadata.features["is_political"].prompt_hash is not None


def test_load_or_init_metadata_rejects_identity_change_on_resume(features_dir) -> None:
    """Given existing metadata with a different prompt hash, when reloading, then raise."""
    spec = FEATURE_REGISTRY["is_political"]
    config = make_feature_generation_config(
        features_dir,
        feature_registry={"is_political": spec},
    )
    metadata = load_or_init_metadata(config, feature_names=("is_political",))
    metadata.features["is_political"].prompt_hash = "old-hash"
    metadata.features["is_political"].model_id = "old-model"
    flush_metadata(features_dir, metadata)

    with pytest.raises(ValueError, match="identity changed"):
        load_or_init_metadata(config, feature_names=("is_political",))
