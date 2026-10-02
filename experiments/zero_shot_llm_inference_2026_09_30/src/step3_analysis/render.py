"""Deterministic Markdown rendering for Study 2 zero-shot analysis tables.

Run from repo root::

    PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step3_analysis.analyze --help
"""

from __future__ import annotations

from experiments.zero_shot_llm_inference_2026_09_30.shared.constants import (
    MODEL_REGISTRY,
    get_model_definition_by_folder,
)
from experiments.zero_shot_llm_inference_2026_09_30.src.step3_analysis.analyze import (
    AnalysisDataset,
    AnalysisTables,
    LabelCountRow,
    ModelMetricRow,
    SplitRemoveVoteCountRow,
    _DATASET_ORDER,
    _LABEL_ORDER,
    _METRIC_DECIMAL_PLACES,
    _SPLIT_REMOVE_VOTE_VALUES,
)

_DATASET_HEADINGS = {
    AnalysisDataset.ALL: "### All five-labeler posts",
    AnalysisDataset.UNANIMOUS: "### Unanimous posts",
    AnalysisDataset.SPLIT: "### Split posts",
}

_DATASET_DISPLAY = {
    AnalysisDataset.ALL: "all",
    AnalysisDataset.UNANIMOUS: "unanimous",
    AnalysisDataset.SPLIT: "split",
}


def render_results_fragment(tables: AnalysisTables) -> str:
    """Render the fixed results fragment from completed analysis tables.

    Parameters
    ----------
    tables
        Completed label, vote, and metric tables.

    Returns
    -------
    str
        Deterministic Markdown fragment with the fixed headings and tables.
    """
    sections = [
        _render_human_label_section(_sorted_label_counts(tables.label_counts)),
        _render_split_vote_section(_sorted_split_vote_counts(tables.split_remove_vote_counts)),
        _render_model_metrics_section(_sorted_model_metrics(tables.model_metrics)),
    ]
    return "\n\n".join(sections) + "\n"


def _sorted_label_counts(rows: tuple[LabelCountRow, ...]) -> tuple[LabelCountRow, ...]:
    order = {
        (dataset, label): index
        for index, (dataset, label) in enumerate(
            (dataset, label)
            for dataset in _DATASET_ORDER
            for label in _LABEL_ORDER
        )
    }
    return tuple(sorted(rows, key=lambda row: order[(row.dataset, row.label)]))


def _sorted_split_vote_counts(
    rows: tuple[SplitRemoveVoteCountRow, ...],
) -> tuple[SplitRemoveVoteCountRow, ...]:
    order = {vote: index for index, vote in enumerate(_SPLIT_REMOVE_VOTE_VALUES)}
    return tuple(sorted(rows, key=lambda row: order[row.remove_votes]))


def _sorted_model_metrics(rows: tuple[ModelMetricRow, ...]) -> tuple[ModelMetricRow, ...]:
    model_order = {model.folder_name: index for index, model in enumerate(MODEL_REGISTRY)}
    dataset_order = {dataset: index for index, dataset in enumerate(_DATASET_ORDER)}
    return tuple(
        sorted(rows, key=lambda row: (dataset_order[row.dataset], model_order[row.model_folder]))
    )


def _render_human_label_section(rows: tuple[LabelCountRow, ...]) -> str:
    header = "## Human label distribution\n\n| Dataset | Label | Count | Proportion |\n| --- | --- | ---: | ---: |"
    body = "\n".join(_human_label_row(row) for row in rows)
    return f"{header}\n{body}"


def _human_label_row(row: LabelCountRow) -> str:
    dataset = _DATASET_DISPLAY[row.dataset]
    label = row.label.value
    count = _format_integer(row.count)
    proportion = _format_proportion(row.proportion)
    return f"| {dataset} | {label} | {count} | {proportion} |"


def _render_split_vote_section(rows: tuple[SplitRemoveVoteCountRow, ...]) -> str:
    header = (
        "## Split remove-vote distribution\n\n"
        "| Remove votes | Count | Proportion |\n| ---: | ---: | ---: |"
    )
    body = "\n".join(_split_vote_row(row) for row in rows)
    return f"{header}\n{body}"


def _split_vote_row(row: SplitRemoveVoteCountRow) -> str:
    return (
        f"| {row.remove_votes} | {_format_integer(row.count)} | "
        f"{_format_proportion(row.proportion)} |"
    )


def _render_model_metrics_section(rows: tuple[ModelMetricRow, ...]) -> str:
    parts = ["## Model metrics"]
    for dataset in _DATASET_ORDER:
        parts.append(_DATASET_HEADINGS[dataset])
        parts.append(_model_metrics_table(rows, dataset))
    return "\n\n".join(parts)


def _model_metrics_table(rows: tuple[ModelMetricRow, ...], dataset: AnalysisDataset) -> str:
    header = "| Model | N | F1 | Accuracy | Recall | Precision |\n| --- | ---: | ---: | ---: | ---: | ---: |"
    dataset_rows = [row for row in rows if row.dataset == dataset]
    body = "\n".join(_model_metric_row(row) for row in dataset_rows)
    return f"{header}\n{body}"


def _model_metric_row(row: ModelMetricRow) -> str:
    display_name = get_model_definition_by_folder(row.model_folder).display_name
    return (
        f"| {display_name} | {_format_integer(row.sample_count)} | "
        f"{_format_metric(row.f1)} | {_format_metric(row.accuracy)} | "
        f"{_format_metric(row.recall)} | {_format_metric(row.precision)} |"
    )


def _format_integer(value: int) -> str:
    return f"{value:,}"


def _format_proportion(value: float) -> str:
    return _format_metric(value)


def _format_metric(value: float) -> str:
    return f"{value:.{_METRIC_DECIMAL_PLACES}f}"
