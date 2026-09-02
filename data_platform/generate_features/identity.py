"""Prompt and model identity for a feature-generation run.

Run from the repo root:

    PYTHONPATH=. uv run python -c "from data_platform.generate_features.identity import identity_for_spec"
"""

from __future__ import annotations

from data_platform.generate_features.models import FeatureIdentity, FeatureSpec


def prompt_hash(system_prompt: str | None) -> str | None:
    """Return a hex digest of ``system_prompt``, or None when the feature has no prompt."""
    raise NotImplementedError


def model_id_for_spec(spec: FeatureSpec) -> str:
    """Return the model id recorded for this feature spec."""
    raise NotImplementedError


def identity_for_spec(spec: FeatureSpec) -> FeatureIdentity:
    """Return model id and prompt hash for ``spec``."""
    raise NotImplementedError
