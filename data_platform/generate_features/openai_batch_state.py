"""On-disk contract for the one in-flight OpenAI Batch job of a feature run.

The OpenAI engine writes this state before its first status poll so a later
process can reattach to the same provider job instead of submitting a new one.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def active_batch_state_path(run_dir: Path, feature_name: str) -> Path:
    raise NotImplementedError


def write_active_batch_state(run_dir: Path, feature_name: str, state: dict[str, Any]) -> Path:
    raise NotImplementedError


def load_active_batch_state(run_dir: Path, feature_name: str) -> dict[str, Any] | None:
    raise NotImplementedError


def clear_active_batch_state(run_dir: Path, feature_name: str) -> None:
    raise NotImplementedError
