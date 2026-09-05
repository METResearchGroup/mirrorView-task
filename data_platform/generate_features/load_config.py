"""Load feature-generation YAML and apply the configured engine.

Run from root: PYTHONPATH=. uv run python -c \\
    "from data_platform.generate_features.load_config import load_feature_generation_config"
"""

from __future__ import annotations

from pathlib import Path

from data_platform.generate_features.models import FeatureSpec

DEFAULT_FEATURE_GENERATION_CONFIG_PATH = Path(
    "data_platform/generate_features/configs/default.yaml"
)


def load_feature_generation_config(config_path: Path | None = None):
    """Load engine settings from a feature-generation YAML file."""
    raise NotImplementedError


def apply_engine_to_registry(
    registry: dict[str, FeatureSpec],
    loaded_config,
) -> dict[str, FeatureSpec]:
    """Return a registry whose LLM features use the YAML engine."""
    raise NotImplementedError
