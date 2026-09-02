from __future__ import annotations

import pytest

from data_platform.generate_features.generate_bluesky_features import BLUESKY_SPEC
from data_platform.generate_features.models import FeatureRunConfig
from data_platform.generate_features.platform_cli import (
    build_feature_config,
    features_from_cli,
    generate_feature_subset,
)
from tests.data_platform.constants import FEATURES_DATASET_ID, PREPROCESSED_RUN_DIR


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
