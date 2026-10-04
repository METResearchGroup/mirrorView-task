"""Markdown tables for the Jev Study 2 analysis bundle.

Run from repo root::

    PYTHONPATH=. uv run python -m experiments.zero_shot_jev_inference_2026_10_01.src.step3_analysis.analyze --help
"""

from __future__ import annotations

from dataclasses import dataclass

from experiments.zero_shot_jev_inference_2026_10_01.shared.constants import JEV_MODEL
from experiments.zero_shot_llm_inference_2026_09_30.src.step3_analysis.analyze import (
    AnalysisDataset,
    LabelCountRow,
    ModelMetricRow,
    SplitRemoveVoteCountRow,
)


@dataclass(frozen=True)
class UsageRow:
    """Token totals and dollar cost for one Jev run."""

    model: str
    predictions: int
    input_tokens: int
    output_tokens: int
    usd: float

_DATASET_ORDER = (
    AnalysisDataset.ALL,
    AnalysisDataset.UNANIMOUS,
    AnalysisDataset.SPLIT,
)
_DATASET_HEADINGS = {
    AnalysisDataset.ALL: "### All five-labeler posts",
    AnalysisDataset.UNANIMOUS: "### Unanimous posts",
    AnalysisDataset.SPLIT: "### Split posts",
}
_METRIC_DECIMAL_PLACES = 6
_USD_DECIMAL_PLACES = 6


def render_results_fragment(
    label_counts: tuple[LabelCountRow, ...],
    split_votes: tuple[SplitRemoveVoteCountRow, ...],
    metrics: tuple[ModelMetricRow, ...],
    usage: UsageRow,
) -> str:
    """Render the fixed results fragment, including Jev token cost.

    Parameters
    ----------
    label_counts
        Human label counts in dataset and label order.
    split_votes
        Split remove-vote counts for votes one through four.
    metrics
        One metric row per dataset for the Jev model.
    usage
        Token totals and dollar cost for the run.

    Returns
    -------
    str
        Markdown fragment with the required headings, ending in a newline.
    """
    sections = [
        _render_label_section(label_counts),
        _render_split_section(split_votes),
        _render_metric_section(metrics),
        _render_usage_section(usage),
    ]
    return "\n\n".join(sections) + "\n"


def _render_label_section(rows: tuple[LabelCountRow, ...]) -> str:
    header = (
        "## Human label distribution\n\n"
        "| Dataset | Label | Count | Proportion |\n| --- | --- | ---: | ---: |"
    )
    body = "\n".join(_label_row(row) for row in rows)
    return f"{header}\n{body}"


def _label_row(row: LabelCountRow) -> str:
    return (
        f"| {row.dataset.value} | {row.label.value} | {_integer(row.count)} | "
        f"{_decimal(row.proportion)} |"
    )


def _render_split_section(rows: tuple[SplitRemoveVoteCountRow, ...]) -> str:
    header = (
        "## Split remove-vote distribution\n\n"
        "| Remove votes | Count | Proportion |\n| ---: | ---: | ---: |"
    )
    body = "\n".join(
        f"| {row.remove_votes} | {_integer(row.count)} | {_decimal(row.proportion)} |"
        for row in rows
    )
    return f"{header}\n{body}"


def _render_metric_section(rows: tuple[ModelMetricRow, ...]) -> str:
    parts = ["## Model metrics"]
    for dataset in _DATASET_ORDER:
        parts.append(_DATASET_HEADINGS[dataset])
        parts.append(_metric_table(rows, dataset))
    return "\n\n".join(parts)


def _metric_table(rows: tuple[ModelMetricRow, ...], dataset: AnalysisDataset) -> str:
    header = "| Model | N | F1 | Accuracy | Recall | Precision |\n| --- | ---: | ---: | ---: | ---: | ---: |"
    body = "\n".join(_metric_row(row) for row in rows if row.dataset is dataset)
    return f"{header}\n{body}"


def _metric_row(row: ModelMetricRow) -> str:
    return (
        f"| {JEV_MODEL.display_name} | {_integer(row.sample_count)} | "
        f"{_decimal(row.f1)} | {_decimal(row.accuracy)} | "
        f"{_decimal(row.recall)} | {_decimal(row.precision)} |"
    )


def _render_usage_section(usage: UsageRow) -> str:
    header = (
        "## Jev usage\n\n"
        "| Model | Predictions | Input tokens | Output tokens | USD |\n"
        "| --- | ---: | ---: | ---: | ---: |"
    )
    usd = f"{usage.usd:.{_USD_DECIMAL_PLACES}f}"
    row = (
        f"| {JEV_MODEL.display_name} | {_integer(usage.predictions)} | "
        f"{_integer(usage.input_tokens)} | {_integer(usage.output_tokens)} | {usd} |"
    )
    return f"{header}\n{row}"


def _integer(value: int) -> str:
    return f"{value:,}"


def _decimal(value: float) -> str:
    return f"{value:.{_METRIC_DECIMAL_PLACES}f}"
