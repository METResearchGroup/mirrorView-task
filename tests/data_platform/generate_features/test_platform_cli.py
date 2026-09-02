from __future__ import annotations

from pathlib import Path

import pytest

from data_platform.generate_features.generate_bluesky_features import BLUESKY_SPEC
from data_platform.generate_features.generate_twitter_features import generate_twitter_features
from data_platform.generate_features.models import FeatureRunConfig
from data_platform.generate_features.platform_cli import (
    build_feature_config,
    feature_run_dir,
    features_from_cli,
    generate_feature_subset,
)
from data_platform.utils.storage import BlueskyStorageManager, StorageStage
from tests.data_platform.constants import (
    FEATURES_DATASET_ID,
    PREPROCESSED_RUN_DIR,
    VALID_TWITTER_DATASET_ID,
)


def test_generate_feature_subset_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown features"):
        generate_feature_subset(["not_a_real_feature"])


def test_generate_feature_subset_none_returns_none() -> None:
    assert generate_feature_subset(None) is None
    assert generate_feature_subset([]) is None


def test_generate_feature_subset_valid_names() -> None:
    assert generate_feature_subset(["is_political"]) == ("is_political",)


def test_features_from_cli_none() -> None:
    assert features_from_cli(None) is None


def test_features_from_cli_comma_and_repeat() -> None:
    assert features_from_cli(["is_political", "is_news_or_opinion,is_self_contained"]) == [
        "is_political",
        "is_news_or_opinion",
        "is_self_contained",
    ]


def test_features_from_cli_empty_strings_returns_none() -> None:
    assert features_from_cli([""]) is None


def test_build_feature_config_uses_timestamped_features_dir(data_root) -> None:
    """Given a dataset, when building config, then features_dir is features/{timestamp}/."""
    config = build_feature_config(
        BLUESKY_SPEC,
        FEATURES_DATASET_ID,
        run_config=FeatureRunConfig(opik_enabled=False),
    )

    assert config.features_dir.parent.name == "features"
    assert config.features_dir.name != "features"
    assert config.features_dir.is_dir()


def test_build_feature_config_resumes_named_run_dir(data_root) -> None:
    """Given run_dir_name, when building config, then features_dir is that timestamp folder."""
    config = build_feature_config(
        BLUESKY_SPEC,
        FEATURES_DATASET_ID,
        run_config=FeatureRunConfig(opik_enabled=False),
        run_dir_name=PREPROCESSED_RUN_DIR,
    )

    assert config.features_dir.name == PREPROCESSED_RUN_DIR
    assert config.features_dir.parent.name == "features"


def test_feature_run_dir_rejects_path_escape(data_root: Path) -> None:
    """Given a run name with path separators, when resolving, then raise."""
    storage = BlueskyStorageManager(
        StorageStage.FEATURES,
        FEATURES_DATASET_ID,
        records_filename="features",
    )

    with pytest.raises(ValueError, match="single feature run directory name"):
        feature_run_dir(storage, "../other-dir")


def test_empty_twitter_input_does_not_create_feature_run(data_root: Path) -> None:
    """Given no preprocessed posts, when generating features, then no features run dir is created."""
    result = generate_twitter_features(VALID_TWITTER_DATASET_ID, opik_enabled=False)

    assert result == {}
    features_root = data_root / "twitter" / VALID_TWITTER_DATASET_ID / "features"
    assert not features_root.exists()
