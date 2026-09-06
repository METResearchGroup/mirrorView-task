from __future__ import annotations

import json

import pytest

from data_platform.generate_features.metadata import (
    flush_metadata,
    init_feature_run_metadata,
    load_feature_run_metadata,
    mark_feature_completed,
    mark_feature_in_progress,
    metadata_path,
    model_id_for_spec,
    prompt_hash,
    set_sync_status_completed,
    update_batch_counts,
)
from data_platform.generate_features.models import (
    FeatureRunConfig,
    FeatureRunMetadata,
    FeatureStatus,
)
from data_platform.generate_features.registry import FEATURE_REGISTRY
from lib.constants import DEFAULT_LLM_MODEL
from tests.data_platform.constants import FEATURES_DATASET_ID, PREPROCESSED_RUN
from tests.data_platform.generate_features.conftest import make_feature_generation_config


class TestInitFeatureRunMetadata:
    """Tests for init_feature_run_metadata()."""

    def test_creates_in_progress_metadata_file(self, features_dir) -> None:
        config = make_feature_generation_config(
            features_dir,
            run_config=FeatureRunConfig(batch_size=32),
        )

        metadata = init_feature_run_metadata(config, ("is_political",))

        assert metadata_path(features_dir).exists()
        assert metadata.features["is_political"].status == "pending"
        assert metadata.config.batch_size == 32
        assert metadata.sync_status == "in_progress"

    def test_records_feature_identity(self, features_dir) -> None:
        spec = FEATURE_REGISTRY["is_political"]
        config = make_feature_generation_config(
            features_dir,
            feature_registry={"is_political": spec},
        )

        metadata = init_feature_run_metadata(config, ("is_political",))

        assert metadata.features["is_political"].model_id == DEFAULT_LLM_MODEL
        assert metadata.features["is_political"].prompt_hash is not None

    def test_fails_when_metadata_already_exists(self, features_dir) -> None:
        config = make_feature_generation_config(
            features_dir,
            feature_registry={"is_political": FEATURE_REGISTRY["is_political"]},
        )
        init_feature_run_metadata(config, ("is_political",))

        with pytest.raises(ValueError, match="already exists"):
            init_feature_run_metadata(config, ("is_political",))


class TestLoadFeatureRunMetadata:
    """Tests for load_feature_run_metadata()."""

    def test_loads_existing_in_progress_metadata(self, features_dir) -> None:
        spec = FEATURE_REGISTRY["is_political"]
        config = make_feature_generation_config(
            features_dir,
            feature_registry={"is_political": spec},
        )
        created = init_feature_run_metadata(config, ("is_political",))

        metadata = load_feature_run_metadata(config, ("is_political",))

        assert metadata.features["is_political"].model_id == created.features["is_political"].model_id
        assert metadata.sync_status == "in_progress"

    def test_fails_when_metadata_is_missing(self, features_dir) -> None:
        config = make_feature_generation_config(features_dir)

        with pytest.raises(FileNotFoundError):
            load_feature_run_metadata(config, ("is_political",))

    def test_fails_when_run_is_completed(self, features_dir) -> None:
        spec = FEATURE_REGISTRY["is_political"]
        config = make_feature_generation_config(
            features_dir,
            feature_registry={"is_political": spec},
        )
        metadata = init_feature_run_metadata(config, ("is_political",))
        set_sync_status_completed(metadata)
        flush_metadata(features_dir, metadata)

        with pytest.raises(ValueError, match="completed"):
            load_feature_run_metadata(config, ("is_political",))

    def test_rejects_prompt_hash_change(self, features_dir) -> None:
        spec = FEATURE_REGISTRY["is_political"]
        config = make_feature_generation_config(
            features_dir,
            feature_registry={"is_political": spec},
        )
        metadata = init_feature_run_metadata(config, ("is_political",))
        metadata.features["is_political"].prompt_hash = "old-hash"
        flush_metadata(features_dir, metadata)

        with pytest.raises(ValueError, match="identity changed"):
            load_feature_run_metadata(config, ("is_political",))

    def test_rejects_model_id_change(self, features_dir) -> None:
        spec = FEATURE_REGISTRY["is_political"]
        config = make_feature_generation_config(
            features_dir,
            feature_registry={"is_political": spec},
        )
        metadata = init_feature_run_metadata(config, ("is_political",))
        metadata.features["is_political"].model_id = "old-model"
        flush_metadata(features_dir, metadata)

        with pytest.raises(ValueError, match="identity changed"):
            load_feature_run_metadata(config, ("is_political",))


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


def test_model_id_follows_engine_type() -> None:
    from dataclasses import replace

    from lib.constants import DEFAULT_BEDROCK_NOVA_MICRO

    assert model_id_for_spec(FEATURE_REGISTRY["is_political"]) == DEFAULT_LLM_MODEL
    assert model_id_for_spec(FEATURE_REGISTRY["is_toxic_tiered"]) == "perspective-api"
    promptless = replace(FEATURE_REGISTRY["is_political"], system_prompt=None)
    assert model_id_for_spec(promptless) == DEFAULT_LLM_MODEL
    assert prompt_hash(promptless.system_prompt) is None
    bedrock_spec = replace(FEATURE_REGISTRY["is_political"], engine_type="bedrock")
    assert model_id_for_spec(bedrock_spec) == DEFAULT_BEDROCK_NOVA_MICRO


def test_prompt_hash_changes_when_prompt_changes() -> None:
    first = prompt_hash(FEATURE_REGISTRY["is_political"].system_prompt)
    second = prompt_hash(FEATURE_REGISTRY["is_likely_spam"].system_prompt)
    assert first is not None
    assert second is not None
    assert first != second
    assert len(first) == 64
