"""Experiment path helpers.

Run from the repo root::

    PYTHONPATH=. uv run python -c "
    from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import paths
    print(paths.EXPERIMENT_ROOT)
    "
"""

from __future__ import annotations

from pathlib import Path


EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]


def cohort_dir(arm: str) -> Path:
    """Return the cohort output directory for one text arm."""
    raise NotImplementedError


def baselines_dir(arm: str) -> Path:
    """Return the baselines output directory for one text arm."""
    raise NotImplementedError


def discovery_run_dir(arm: str) -> Path:
    """Return the discovery outputs directory for one text arm."""
    raise NotImplementedError


def normalize_run_dir(arm: str) -> Path:
    """Return the normalize output directory for one text arm."""
    raise NotImplementedError


def operationalize_dir(arm: str) -> Path:
    """Return the operationalize output directory for one text arm."""
    raise NotImplementedError


def shared_label_dir() -> Path:
    """Return the shared label output directory."""
    raise NotImplementedError


def codebook_dir() -> Path:
    """Return the shared codebook output directory."""
    raise NotImplementedError


def self_consistency_dir() -> Path:
    """Return the shared self-consistency output directory."""
    raise NotImplementedError


def cost_log_path() -> Path:
    """Return the shared cost log path."""
    raise NotImplementedError


def post_split_dir() -> Path:
    """Return the committed post split directory."""
    raise NotImplementedError


def make_run_timestamp() -> str:
    """Return a new run timestamp folder name."""
    raise NotImplementedError


def latest_timestamp_subdir(parent: Path) -> Path:
    """Return the newest child directory under ``parent``."""
    raise NotImplementedError
