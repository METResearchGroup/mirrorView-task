"""Cost and runtime estimate tables for smoke runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EstimateRow:
    value_name: str
    low: float
    median: float
    high: float


def estimate_row(value_name: str, median: float) -> EstimateRow:
    raise NotImplementedError


def build_estimates(
    input_tokens: list[int],
    output_tokens: list[int],
    runtime_minutes: float,
    total_requests: int,
    usd_per_million_input: float,
    usd_per_million_output: float,
) -> list[EstimateRow]:
    raise NotImplementedError


def render_estimates_markdown(rows: list[EstimateRow]) -> str:
    raise NotImplementedError


def write_estimates(rows: list[EstimateRow], relative_key: str) -> Path:
    raise NotImplementedError


def require_estimates(relative_key: str) -> None:
    raise NotImplementedError
