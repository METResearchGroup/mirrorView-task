"""S3 key builders for the Jev experiment prefix.

JSON serialization, SHA-256, and immutable writes come from the issue 326
storage module. This module only names keys under this experiment.

Run from repo root::

    PYTHONPATH=. uv run python -c "from experiments.zero_shot_jev_inference_2026_10_01.shared.storage import build_run_prefix"
"""

from __future__ import annotations

from experiments.zero_shot_jev_inference_2026_10_01.shared.constants import (
    JEV_MODEL,
    S3_PREFIX,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.storage import (
    validate_path_segment,
)

_RUNS_SEGMENT = "runs"
_ANALYSIS_SEGMENT = "analysis"
_PREDICTIONS_SEGMENT = "predictions"
_FAILURES_SEGMENT = "failures"
_MANIFESTS_SEGMENT = "manifests"
_BATCH_FILE_PREFIX = "batch-"
_MANIFEST_FILE_PREFIX = "manifest-"
_SEQUENCE_WIDTH = 6
_JSONL_SUFFIX = ".jsonl"
_JSON_SUFFIX = ".json"


def build_run_prefix(run_id: str) -> str:
    """Return the Jev run folder prefix for ``run_id``.

    Parameters
    ----------
    run_id
        Safe path segment identifying the run.

    Returns
    -------
    str
        Prefix ending in ``jev_1_13_0/``.

    Raises
    ------
    ValueError
        When ``run_id`` is not a single safe path segment.
    """
    safe_run_id = validate_path_segment(run_id)
    return f"{S3_PREFIX}{_RUNS_SEGMENT}/{safe_run_id}/{JEV_MODEL.folder_name}/"


def build_predictions_prefix(run_id: str) -> str:
    """Return the predictions prefix for one Jev run."""
    return build_run_prefix(run_id) + f"{_PREDICTIONS_SEGMENT}/"


def build_failures_prefix(run_id: str) -> str:
    """Return the failures prefix for one Jev run."""
    return build_run_prefix(run_id) + f"{_FAILURES_SEGMENT}/"


def build_manifests_prefix(run_id: str) -> str:
    """Return the manifests prefix for one Jev run."""
    return build_run_prefix(run_id) + f"{_MANIFESTS_SEGMENT}/"


def build_analysis_prefix(run_id: str) -> str:
    """Return the analysis prefix for one run.

    Parameters
    ----------
    run_id
        Safe path segment identifying the run.

    Returns
    -------
    str
        Prefix ending in a slash.

    Raises
    ------
    ValueError
        When ``run_id`` is not a single safe path segment.
    """
    safe_run_id = validate_path_segment(run_id)
    return f"{S3_PREFIX}{_ANALYSIS_SEGMENT}/{safe_run_id}/"


def build_prediction_batch_key(run_id: str, sequence: int) -> str:
    """Return the immutable prediction batch key for ``sequence``."""
    return _build_batch_key(run_id, _PREDICTIONS_SEGMENT, sequence)


def build_failure_batch_key(run_id: str, sequence: int) -> str:
    """Return the immutable failure batch key for ``sequence``."""
    return _build_batch_key(run_id, _FAILURES_SEGMENT, sequence)


def build_manifest_key(run_id: str, sequence: int) -> str:
    """Return the immutable manifest key for ``sequence``."""
    _validate_sequence(sequence)
    filename = f"{_MANIFEST_FILE_PREFIX}{sequence:0{_SEQUENCE_WIDTH}d}{_JSON_SUFFIX}"
    return build_manifests_prefix(run_id) + filename


def _build_batch_key(run_id: str, artifact_segment: str, sequence: int) -> str:
    _validate_sequence(sequence)
    filename = f"{_BATCH_FILE_PREFIX}{sequence:0{_SEQUENCE_WIDTH}d}{_JSONL_SUFFIX}"
    return build_run_prefix(run_id) + f"{artifact_segment}/" + filename


def _validate_sequence(sequence: int) -> None:
    if sequence < 0:
        raise ValueError("sequence must be nonnegative")
