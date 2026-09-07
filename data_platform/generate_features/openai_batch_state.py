"""On-disk contract for the one in-flight OpenAI Batch job of a feature run.

The OpenAI engine writes this state before its first status poll so a later
process can reattach to the same provider job instead of submitting a new one.
"""

from __future__ import annotations

import json
import os
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
    return run_dir / f"{feature_name}{ACTIVE_BATCH_STATE_SUFFIX}"


def write_active_batch_state(run_dir: Path, feature_name: str, state: dict[str, Any]) -> Path:
    """Replace the state file in one step and return its path.

    Raises
    ------
    ValueError
        When a field from ``ACTIVE_BATCH_STATE_FIELDS`` is missing or
        ``state["state"]`` is not one of ``ACTIVE_BATCH_STATES``.
    """
    missing = [field for field in ACTIVE_BATCH_STATE_FIELDS if field not in state]
    if missing:
        raise ValueError(f"active batch state is missing fields: {missing}")
    if state["state"] not in ACTIVE_BATCH_STATES:
        raise ValueError(
            f"active batch state must be one of {ACTIVE_BATCH_STATES}, got {state['state']!r}"
        )
    run_dir.mkdir(parents=True, exist_ok=True)
    path = active_batch_state_path(run_dir, feature_name)
    tmp_path = path.with_name(f"{path.name}.tmp")
    tmp_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)
    return path


def load_active_batch_state(run_dir: Path, feature_name: str) -> dict[str, Any] | None:
    """Return the saved state, or None when no job state exists for the feature."""
    path = active_batch_state_path(run_dir, feature_name)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def clear_active_batch_state(run_dir: Path, feature_name: str) -> None:
    """Delete the state file. A missing file is not an error."""
    active_batch_state_path(run_dir, feature_name).unlink(missing_ok=True)
