"""Experiment path helpers for BERTopic modeling (original text role, v1).

Run from repo root::

    PYTHONPATH=. uv run --extra bertopic python -c \\
      \"from experiments.bertopic_modeling_2026_08_05.src import paths; print(paths.embeddings_dir('original'))\"
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
TEXT_ROLE_V1 = "original"
_ALLOWED_TEXT_ROLES = frozenset({TEXT_ROLE_V1})
_RUN_TIMESTAMP_FORMAT = "%Y%m%dT%H%M%SZ"


def _require_original_role(role: str) -> str:
    """Validate text role for v1 (original only).

    Parameters
    ----------
    role
        Requested text role string.

    Returns
    -------
    str
        The validated role.

    Raises
    ------
    ValueError
        If ``role`` is not ``\"original\"``.
    """
    if role not in _ALLOWED_TEXT_ROLES:
        raise ValueError(
            f"Unsupported text role {role!r} in v1; only {TEXT_ROLE_V1!r} is allowed "
            "(mirror is deferred)."
        )
    return role


def embeddings_dir(role: str) -> Path:
    """Return ``outputs/embeddings/<role>/`` under the experiment root."""
    role = _require_original_role(role)
    return EXPERIMENT_ROOT / "outputs" / "embeddings" / role


def topics_dir(role: str) -> Path:
    """Return ``outputs/topics/<role>/`` under the experiment root."""
    role = _require_original_role(role)
    return EXPERIMENT_ROOT / "outputs" / "topics" / role


def labels_dir(role: str) -> Path:
    """Return ``outputs/labels/<role>/`` under the experiment root."""
    role = _require_original_role(role)
    return EXPERIMENT_ROOT / "outputs" / "labels" / role


def figures_dir(role: str) -> Path:
    """Return ``outputs/figures/<role>/`` under the experiment root."""
    role = _require_original_role(role)
    return EXPERIMENT_ROOT / "outputs" / "figures" / role


def new_run_timestamp() -> str:
    """Return a UTC run stamp like ``20260805T131500Z``."""
    return datetime.now(timezone.utc).strftime(_RUN_TIMESTAMP_FORMAT)
