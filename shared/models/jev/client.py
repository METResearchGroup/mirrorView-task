"""TypeSafe API key lookup and ``TypeSafeClassifier`` construction.

Run from repo root::

    PYTHONPATH=. uv run python -c "from shared.models.jev.client import build_jev_classifier, get_jev_api_key; print(get_jev_api_key.__name__)"
"""

from __future__ import annotations

from langchain_typesafe import TypeSafeClassifier

from shared.models.jev.constants import (
    JEV_MODEL_ID,
    JEV_REQUEST_TIMEOUT_SECONDS,
)


def get_jev_api_key() -> str:
    """Return the TypeSafe API key from ``TYPESAFE_API_KEY`` or Secrets Manager."""
    raise NotImplementedError


def build_jev_classifier(
    model_id: str = JEV_MODEL_ID,
    api_key: str | None = None,
    timeout: float = JEV_REQUEST_TIMEOUT_SECONDS,
) -> TypeSafeClassifier:
    """Build a classifier pinned to ``model_id``. Looks up the key when omitted."""
    raise NotImplementedError
