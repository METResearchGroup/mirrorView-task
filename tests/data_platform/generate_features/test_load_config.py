"""Tests for YAML engine configuration used by feature generation."""

from __future__ import annotations

from data_platform.generate_features.load_config import (
    DEFAULT_FEATURE_GENERATION_CONFIG_PATH,
    apply_engine_to_registry,
    load_feature_generation_config,
)
from data_platform.generate_features.platform_cli import feature_registry_from_yaml


def test_scaffold_imports_resolve() -> None:
    assert DEFAULT_FEATURE_GENERATION_CONFIG_PATH.name == "default.yaml"
    assert load_feature_generation_config is not None
    assert apply_engine_to_registry is not None
    assert feature_registry_from_yaml is not None
