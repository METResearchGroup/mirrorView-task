"""Path helpers for the Part 3 original and mirror BERTopic experiment.

Run from repo root::

    PYTHONPATH=. uv run python -c \\
      "from experiments.bertopic_original_mirror_part3_2026_09_24.src import paths; print(paths.embeddings_dir('original'))"
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
RUN_TIMESTAMP_FORMAT = "%Y%m%dT%H%M%SZ"


class TextRole(str, Enum):
    """Text roles this experiment fits."""

    ORIGINAL = "original"
    MIRROR = "mirror"
    JOINT = "joint"


ALLOWED_TEXT_ROLES = frozenset(role.value for role in TextRole)


def require_text_role(role: str) -> str:
    """Return ``role`` when it is original, mirror, or joint.

    Parameters
    ----------
    role
        Requested text role.

    Returns
    -------
    str
        The same role string.

    Raises
    ------
    ValueError
        If ``role`` is not in ``ALLOWED_TEXT_ROLES``.
    """
    if role not in ALLOWED_TEXT_ROLES:
        allowed = ", ".join(sorted(ALLOWED_TEXT_ROLES))
        raise ValueError(f"Unsupported text role {role!r}; allowed: {allowed}")
    return role


def _role_output_dir(kind: str, role: str) -> Path:
    """Return ``outputs/<kind>/<role>/`` after validating ``role``."""
    return EXPERIMENT_ROOT / "outputs" / kind / require_text_role(role)


def embeddings_dir(role: str) -> Path:
    """Return the Titan embedding cache directory for ``role``."""
    return _role_output_dir("embeddings", role)


def embeddings_minilm_dir(role: str) -> Path:
    """Return the MiniLM embedding cache directory for ``role``."""
    return _role_output_dir("embeddings_minilm", role)


def topics_dir(role: str) -> Path:
    """Return the topic-model output directory for ``role``."""
    return _role_output_dir("topics", role)


def labels_dir(role: str) -> Path:
    """Return the topic-label output directory for ``role``."""
    return _role_output_dir("labels", role)


def figures_dir(role: str) -> Path:
    """Return the figure output directory for ``role``."""
    return _role_output_dir("figures", role)


def analyses_dir() -> Path:
    """Return the cross-role and outcome analysis directory."""
    return EXPERIMENT_ROOT / "outputs" / "analyses"


def ablations_dir() -> Path:
    """Return the ablation output directory."""
    return EXPERIMENT_ROOT / "outputs" / "ablations"


def assignments_dir() -> Path:
    """Return the mirror-via-original assignment directory."""
    return EXPERIMENT_ROOT / "outputs" / "assignments" / "mirror_via_original"


def dedupe_report_path() -> Path:
    """Return the path of the dedupe report JSON."""
    return EXPERIMENT_ROOT / "outputs" / "dedupe_report.json"


def new_run_timestamp() -> str:
    """Return a UTC run stamp like ``20260924T050000Z``."""
    return datetime.now(timezone.utc).strftime(RUN_TIMESTAMP_FORMAT)
