"""On-disk contract for the one in-flight OpenAI Batch job of a feature run.

The OpenAI engine writes this state before its first status poll so a later
process can reattach to the same provider job instead of submitting a new one.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

ACTIVE_BATCH_STATE_SUFFIX = ".active_openai_batch.json"
ACTIVE_BATCH_STATES = ("polling", "writing", "terminal")
ACTIVE_BATCH_STATE_FIELDS = (
    "input_file_id",
    "batch_id",
    "logical_batch_index",
    "pending_source_record_ids",
    "attempt_count",
    "state",
    "campaign_id",
    "feature_name",
    "submitted_at",
)


def active_batch_state_path(run_dir: Path, feature_name: str) -> Path:
    """Return ``{run_dir}/{feature_name}.active_openai_batch.json``."""
    raise NotImplementedError


def write_active_batch_state(run_dir: Path, feature_name: str, state: dict[str, Any]) -> Path:
    """Replace the state file in one step and return its path.

    Raises
    ------
    ValueError
        When a field from ``ACTIVE_BATCH_STATE_FIELDS`` is missing or
        ``state["state"]`` is not one of ``ACTIVE_BATCH_STATES``.
    """
    raise NotImplementedError


def load_active_batch_state(run_dir: Path, feature_name: str) -> dict[str, Any] | None:
    """Return the saved state, or None when no job state exists for the feature."""
    raise NotImplementedError


def clear_active_batch_state(run_dir: Path, feature_name: str) -> None:
    """Delete the state file. A missing file is not an error."""
    raise NotImplementedError
