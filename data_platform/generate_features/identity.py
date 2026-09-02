"""Prompt and model identity for a feature-generation run.

Run from the repo root:

    PYTHONPATH=. uv run python -c "from data_platform.generate_features.identity import identity_for_spec"
"""

from __future__ import annotations

import hashlib

from data_platform.generate_features.models import FeatureIdentity, FeatureSpec
from lib.constants import DEFAULT_LLM_MODEL

PERSPECTIVE_MODEL_ID = "perspective-api"


def prompt_hash(system_prompt: str | None) -> str | None:
    """Return a SHA-256 hex digest of ``system_prompt``, or None when omitted."""
    if system_prompt is None:
        return None
    return hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()


def model_id_for_spec(spec: FeatureSpec) -> str:
    """Return the default LLM model id, or Perspective for non-LLM features."""
    if spec.system_prompt is None:
        return PERSPECTIVE_MODEL_ID
    return DEFAULT_LLM_MODEL


def identity_for_spec(spec: FeatureSpec) -> FeatureIdentity:
    """Return model id and prompt hash for ``spec``."""
    return FeatureIdentity(
        model_id=model_id_for_spec(spec),
        prompt_hash=prompt_hash(spec.system_prompt),
    )
