"""LiteLLM structured completion client with spend logging.

Run from the repo root::

    PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.llm_client \\
      --probe
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel


class SpendCapExceeded(Exception):
    """Raised when a call would exceed the cumulative spend cap."""


def make_run_timestamp() -> str:
    """Return a per-call timestamp string for artifact filenames."""
    raise NotImplementedError


def read_cumulative_cost_usd() -> float:
    """Return cumulative spend from the shared cost log."""
    raise NotImplementedError


def append_cost_log(
    *,
    stage: str,
    arm: str | None,
    model: str,
    input_tokens: int,
    output_tokens: int,
    reasoning_tokens: int,
    cost_usd: float,
) -> float:
    """Append one cost log line and return the new cumulative total."""
    raise NotImplementedError


def complete_structured(
    messages: list[dict[str, str]],
    response_model: type[BaseModel],
    *,
    stage: str,
    arm: str | None,
    call_index: int,
    output_dir: Path,
    run_metadata: dict[str, Any],
) -> BaseModel:
    """Run one structured LiteLLM completion and write per-call artifacts."""
    raise NotImplementedError
