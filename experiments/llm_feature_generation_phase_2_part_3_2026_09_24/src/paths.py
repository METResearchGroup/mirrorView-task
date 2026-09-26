"""Experiment path helpers.

Run from the repo root::

    PYTHONPATH=. uv run python -c "
    from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import paths
    print(paths.EXPERIMENT_ROOT)
    "
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.constants import (
    COST_LOG_PATH,
    METADATA_FILENAME,
    PARTICIPANT_FILTER_ALL,
    RUN_TIMESTAMP_FORMAT,
)

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_DIRNAME = "outputs"
COHORT_DIRNAME = "cohort"
DATA_DIRNAME = "data"
POST_SPLIT_DIRNAME = "post_split"
SHARED_DIRNAME = "shared"


def cohort_dir(arm: str) -> Path:
    """Return the cohort output directory for one text arm."""
    return EXPERIMENT_ROOT / OUTPUTS_DIRNAME / arm / COHORT_DIRNAME


def baselines_dir(arm: str) -> Path:
    """Return the baselines output directory for one text arm."""
    return EXPERIMENT_ROOT / OUTPUTS_DIRNAME / arm / "baselines"


def discovery_run_dir(arm: str) -> Path:
    """Return the discovery outputs directory for one text arm."""
    return EXPERIMENT_ROOT / OUTPUTS_DIRNAME / arm / "discovery" / "outputs"


def normalize_run_dir(arm: str) -> Path:
    """Return the normalize output directory for one text arm."""
    return EXPERIMENT_ROOT / OUTPUTS_DIRNAME / arm / "normalize"


def operationalize_dir(arm: str) -> Path:
    """Return the operationalize output directory for one text arm."""
    return EXPERIMENT_ROOT / OUTPUTS_DIRNAME / arm / "operationalize"


def shared_label_dir() -> Path:
    """Return the shared label output directory."""
    return EXPERIMENT_ROOT / OUTPUTS_DIRNAME / SHARED_DIRNAME / "label"


def codebook_dir() -> Path:
    """Return the shared codebook output directory."""
    return EXPERIMENT_ROOT / OUTPUTS_DIRNAME / SHARED_DIRNAME / "codebook"


def self_consistency_dir() -> Path:
    """Return the shared self-consistency output directory."""
    return EXPERIMENT_ROOT / OUTPUTS_DIRNAME / SHARED_DIRNAME / "self_consistency"


def cost_log_path() -> Path:
    """Return the shared cost log path."""
    return EXPERIMENT_ROOT / COST_LOG_PATH


def post_split_dir() -> Path:
    """Return the committed post split directory."""
    return EXPERIMENT_ROOT / DATA_DIRNAME / POST_SPLIT_DIRNAME


def make_run_timestamp() -> str:
    """Return a new run timestamp folder name."""
    return datetime.now().strftime(RUN_TIMESTAMP_FORMAT)


def latest_cohort_run_dir(
    arm: str,
    participant_filter: str = PARTICIPANT_FILTER_ALL,
) -> Path:
    """Return the newest cohort run whose metadata matches ``participant_filter``.

    Parameters
    ----------
    arm
        Text arm under ``outputs/<arm>/cohort``.
    participant_filter
        Value of ``participant_filter`` in run ``metadata.json``.

    Returns
    -------
    Path
        Newest matching cohort run directory by timestamp name.

    Raises
    ------
    FileNotFoundError
        When no matching cohort run exists.
    """
    parent = cohort_dir(arm)
    if not parent.is_dir():
        raise FileNotFoundError(f"Directory not found: {parent}")
    matches: list[Path] = []
    for child in parent.iterdir():
        if not child.is_dir():
            continue
        metadata_path = child / METADATA_FILENAME
        if not metadata_path.is_file():
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("participant_filter") == participant_filter:
            matches.append(child)
    if not matches:
        raise FileNotFoundError(
            f"No cohort run with participant_filter={participant_filter} under {parent}"
        )
    return sorted(matches, key=lambda path: path.name)[-1]


def latest_timestamp_subdir(parent: Path) -> Path:
    """Return the newest child directory under ``parent``.

    Parameters
    ----------
    parent
        Directory that contains timestamped run folders.

    Returns
    -------
    Path
        Latest child directory by name sort.

    Raises
    ------
    FileNotFoundError
        When parent is missing or has no child directories.
    """
    if not parent.is_dir():
        raise FileNotFoundError(f"Directory not found: {parent}")
    children = [path for path in parent.iterdir() if path.is_dir()]
    if not children:
        raise FileNotFoundError(f"No timestamp subdirectories under {parent}")
    return sorted(children, key=lambda path: path.name)[-1]
