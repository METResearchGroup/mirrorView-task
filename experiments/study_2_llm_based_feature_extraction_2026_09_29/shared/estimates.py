"""Cost and runtime estimate tables for smoke runs."""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from pathlib import Path

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    ESTIMATE_BAND,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.storage import (
    download_artifact,
    local_path,
)


@dataclass(frozen=True)
class EstimateRow:
    value_name: str
    low: float
    median: float
    high: float


def estimate_row(value_name: str, median: float) -> EstimateRow:
    """Build one estimate row with symmetric low and high bands.

    Parameters
    ----------
    value_name
        Row label such as ``Runtime (minutes)``.
    median
        Central estimate before applying ``ESTIMATE_BAND``.

    Returns
    -------
    EstimateRow
        Low, median, and high values for the row.
    """
    low = median * (1.0 - ESTIMATE_BAND)
    high = median * (1.0 + ESTIMATE_BAND)
    return EstimateRow(value_name=value_name, low=low, median=median, high=high)


def build_estimates(
    input_tokens: list[int],
    output_tokens: list[int],
    runtime_minutes: float,
    total_requests: int,
    usd_per_million_input: float,
    usd_per_million_output: float,
) -> list[EstimateRow]:
    """Scale smoke medians to a full run and return the four estimate rows.

    Parameters
    ----------
    input_tokens
        Per-request input token counts from the smoke batch.
    output_tokens
        Per-request output token counts from the smoke batch.
    runtime_minutes
        Wall-clock minutes for the smoke batch.
    total_requests
        Full-run request count used to scale token medians.
    usd_per_million_input
        Batch input price per million tokens.
    usd_per_million_output
        Batch output price per million tokens.

    Returns
    -------
    list[EstimateRow]
        Rows for runtime, input tokens, output tokens, and price.

    Raises
    ------
    ValueError
        When either token list is empty.
    """
    if not input_tokens or not output_tokens:
        raise ValueError("token usage lists must not be empty")
    median_input = statistics.median(input_tokens)
    median_output = statistics.median(output_tokens)
    scaled_input = median_input * total_requests
    scaled_output = median_output * total_requests
    price_usd = (
        scaled_input * usd_per_million_input + scaled_output * usd_per_million_output
    ) / 1_000_000.0
    return [
        estimate_row("Runtime (minutes)", runtime_minutes),
        estimate_row("Input tokens", scaled_input),
        estimate_row("Output tokens", scaled_output),
        estimate_row("Price (USD)", price_usd),
    ]


def render_estimates_markdown(rows: list[EstimateRow]) -> str:
    """Render estimate rows as a Markdown table.

    Parameters
    ----------
    rows
        Estimate rows in display order.

    Returns
    -------
    str
        Markdown table with Value, Low, Median, and High columns.
    """
    lines = ["| Value | Low | Median | High |", "| --- | --- | --- | --- |"]
    for row in rows:
        if row.value_name == "Price (USD)":
            low = f"${row.low:,.2f}"
            median = f"${row.median:,.2f}"
            high = f"${row.high:,.2f}"
        elif row.value_name == "Runtime (minutes)":
            low = f"{row.low:.1f}"
            median = f"{row.median:.1f}"
            high = f"{row.high:.1f}"
        else:
            low = f"{row.low:,.0f}"
            median = f"{row.median:,.0f}"
            high = f"{row.high:,.0f}"
        lines.append(f"| {row.value_name} | {low} | {median} | {high} |")
    return "\n".join(lines)


def write_estimates(rows: list[EstimateRow], relative_key: str) -> Path:
    """Write estimate rows as JSON under the experiment outputs directory.

    Parameters
    ----------
    rows
        Rows to persist.
    relative_key
        Path under ``outputs/``.

    Returns
    -------
    pathlib.Path
        Local path that was written.
    """
    path = local_path(relative_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "value_name": row.value_name,
            "low": row.low,
            "median": row.median,
            "high": row.high,
        }
        for row in rows
    ]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def require_estimates(relative_key: str) -> None:
    """Ensure an estimates file exists locally or on S3.

    Parameters
    ----------
    relative_key
        Path under ``outputs/``.

    Raises
    ------
    FileNotFoundError
        When the artifact is missing locally and on S3.
    """
    download_artifact(relative_key)
