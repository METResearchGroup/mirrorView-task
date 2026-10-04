"""Draw remove-threshold curves for the optimized-prompt Jev run.

Run from repo root::

    PYTHONPATH=. uv run python -m experiments.few_shot_jev_optimized_prompt_2026_10_04.src.plot_threshold_curves
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore

from experiments.few_shot_jev_optimized_prompt_2026_10_04.shared.config import OPTIMIZED_VARIANT
from experiments.zero_shot_jev_inference_2026_10_01.shared.constants import JEV_MODEL
from experiments.zero_shot_jev_inference_2026_10_01.shared.storage import build_predictions_prefix
from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import (
    PredictionRecord,
    Study2InputRecord,
    validate_prediction_record_identity,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.storage import (
    apply_lab_aws_credentials_when_unset,
    load_jsonl_records_under_prefix,
    parse_study2_input_jsonl_bytes,
)
from experiments.zero_shot_llm_inference_2026_09_30.src.step3_analysis.analyze import (
    ClassificationMetrics,
    build_classification_metrics,
    build_confusion_counts,
)

_RUN_ID = "study2-jev-optimized-prompt-2026-10-04"
_THRESHOLD_STEP = 0.05
_THRESHOLD_COUNT = 21
_LABEL_STRIDE = 2
_REPORTED_THRESHOLD = 0.50
_AXIS_MAX = 1.0
_Y_HEADROOM = 1.28
_Y_TICKS = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
_FIGURE_WIDTH = 8
_FIGURE_HEIGHT = 4.8
_LINE_WIDTH = 2
_MARKER_SIZE = 3.5
_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
_SLICE_COLORS = {
    "All": "#0072B2",
    "Unanimous": "#D55E00",
    "Split": "#009E73",
}
_EXPECTED_SLICE_COUNTS = {"All": 13987, "Unanimous": 4046, "Split": 9941}
_PUBLISHED_AT_HALF = {
    "All": {
        "f1": "0.542148",
        "accuracy": "0.739043",
        "recall": "0.728591",
        "precision": "0.431682",
    },
    "Unanimous": {
        "f1": "0.549451",
        "accuracy": "0.888532",
        "recall": "0.898693",
        "precision": "0.395683",
    },
    "Split": {
        "f1": "0.541099",
        "accuracy": "0.678201",
        "recall": "0.709023",
        "precision": "0.437486",
    },
}


@dataclass(frozen=True)
class MetricChart:
    """One curve file and the classification field it plots."""

    field: str
    ylabel: str
    filename: str


@dataclass(frozen=True)
class SliceRows:
    """Prepared pairs for one metric slice."""

    name: str
    color: str
    rows: tuple[Study2InputRecord, ...]


@dataclass(frozen=True)
class MetricSeries:
    """One slice line on one metric chart."""

    name: str
    color: str
    thresholds: tuple[float, ...]
    values: tuple[float, ...]


_CHARTS = (
    MetricChart("f1", "F1", "f1_by_remove_threshold.png"),
    MetricChart("recall", "Recall", "recall_by_remove_threshold.png"),
    MetricChart("accuracy", "Accuracy", "accuracy_by_remove_threshold.png"),
    MetricChart("precision", "Precision", "precision_by_remove_threshold.png"),
)


def main() -> None:
    """Load the production run and write one PNG per metric."""
    apply_lab_aws_credentials_when_unset()
    store = CampaignObjectStore(OPTIMIZED_VARIANT.s3_bucket, region_name="us-east-2")
    records = _load_records(store)
    probabilities = _load_probabilities(store, records)
    slices = _metric_slices(records)
    thresholds = _threshold_grid()
    _reject_published_half_mismatch(slices, probabilities)
    for chart in _CHARTS:
        series = _series_for_chart(slices, probabilities, thresholds, chart.field)
        _plot_chart(series, chart, _STATIC_DIR / chart.filename)
        print(f"wrote={_STATIC_DIR / chart.filename}")


def _threshold_grid() -> tuple[float, ...]:
    return tuple(round(index * _THRESHOLD_STEP, 2) for index in range(_THRESHOLD_COUNT))


def _load_records(store: CampaignObjectStore) -> tuple[Study2InputRecord, ...]:
    stored = store.get(OPTIMIZED_VARIANT.input_records_key)
    if stored is None:
        raise FileNotFoundError(OPTIMIZED_VARIANT.input_records_key)
    return tuple(parse_study2_input_jsonl_bytes(stored.body))


def _load_probabilities(
    store: CampaignObjectStore,
    records: tuple[Study2InputRecord, ...],
) -> dict[str, float]:
    known_ids = frozenset(record.post_id for record in records)
    batches = load_jsonl_records_under_prefix(
        store,
        build_predictions_prefix(_RUN_ID, variant=OPTIMIZED_VARIANT),
        PredictionRecord,
    )
    probabilities = _probabilities_from_batches(batches, known_ids)
    if set(probabilities) != known_ids:
        raise ValueError("prediction post ids do not match the prepared input")
    return probabilities


def _probabilities_from_batches(
    batches: list[tuple[str, list[PredictionRecord]]],
    known_ids: frozenset[str],
) -> dict[str, float]:
    probabilities: dict[str, float] = {}
    for _, batch in batches:
        for prediction in batch:
            _remember_prediction(probabilities, prediction, known_ids)
    return probabilities


def _remember_prediction(
    probabilities: dict[str, float],
    prediction: PredictionRecord,
    known_ids: frozenset[str],
) -> None:
    validate_prediction_record_identity(
        prediction,
        _RUN_ID,
        JEV_MODEL.folder_name,
        JEV_MODEL.model_id,
        known_ids,
    )
    if prediction.post_id in probabilities:
        raise ValueError(f"duplicate prediction post_id: {prediction.post_id}")
    probabilities[prediction.post_id] = prediction.p_remove


def _metric_slices(records: tuple[Study2InputRecord, ...]) -> tuple[SliceRows, ...]:
    excluded = frozenset(OPTIMIZED_VARIANT.metric_exclusion_post_ids)
    kept = tuple(record for record in records if record.post_id not in excluded)
    slices = (
        SliceRows("All", _SLICE_COLORS["All"], kept),
        SliceRows("Unanimous", _SLICE_COLORS["Unanimous"], _unanimous_rows(kept)),
        SliceRows("Split", _SLICE_COLORS["Split"], _split_rows(kept)),
    )
    _reject_slice_counts(slices)
    return slices


def _unanimous_rows(rows: tuple[Study2InputRecord, ...]) -> tuple[Study2InputRecord, ...]:
    return tuple(row for row in rows if row.is_unanimous)


def _split_rows(rows: tuple[Study2InputRecord, ...]) -> tuple[Study2InputRecord, ...]:
    return tuple(row for row in rows if not row.is_unanimous)


def _reject_slice_counts(slices: tuple[SliceRows, ...]) -> None:
    for slice_rows in slices:
        expected = _EXPECTED_SLICE_COUNTS[slice_rows.name]
        if len(slice_rows.rows) != expected:
            raise ValueError(f"{slice_rows.name} has {len(slice_rows.rows)} rows, expected {expected}")


def _series_for_chart(
    slices: tuple[SliceRows, ...],
    probabilities: dict[str, float],
    thresholds: tuple[float, ...],
    field: str,
) -> tuple[MetricSeries, ...]:
    return tuple(
        MetricSeries(
            slice_rows.name,
            slice_rows.color,
            thresholds,
            _values_for_slice(slice_rows.rows, probabilities, thresholds, field),
        )
        for slice_rows in slices
    )


def _values_for_slice(
    rows: tuple[Study2InputRecord, ...],
    probabilities: dict[str, float],
    thresholds: tuple[float, ...],
    field: str,
) -> tuple[float, ...]:
    return tuple(_metric_at(rows, probabilities, threshold, field) for threshold in thresholds)


def _metric_at(
    rows: tuple[Study2InputRecord, ...],
    probabilities: dict[str, float],
    threshold: float,
    field: str,
) -> float:
    predicted = {row.post_id: probabilities[row.post_id] >= threshold for row in rows}
    metrics = build_classification_metrics(build_confusion_counts(rows, predicted))
    return _metric_field(metrics, field)


def _metric_field(metrics: ClassificationMetrics, field: str) -> float:
    values = {
        "f1": metrics.f1,
        "recall": metrics.recall,
        "accuracy": metrics.accuracy,
        "precision": metrics.precision,
    }
    return values[field]


def _reject_published_half_mismatch(
    slices: tuple[SliceRows, ...],
    probabilities: dict[str, float],
) -> None:
    for slice_rows in slices:
        for field, expected in _PUBLISHED_AT_HALF[slice_rows.name].items():
            measured = _metric_at(slice_rows.rows, probabilities, _REPORTED_THRESHOLD, field)
            if f"{measured:.6f}" != expected:
                raise ValueError(f"{slice_rows.name} {field} at 0.50 is {measured:.6f}, expected {expected}")


def _plot_chart(series: tuple[MetricSeries, ...], chart: MetricChart, path: Path) -> None:
    figure, axis = plt.subplots(figsize=(_FIGURE_WIDTH, _FIGURE_HEIGHT))
    _draw_lines(axis, series)
    _label_thresholds(axis, series[0].thresholds)
    _style_axis(axis, chart.ylabel)
    _save_figure(figure, path)


def _draw_lines(axis: plt.Axes, series: tuple[MetricSeries, ...]) -> None:
    for item in series:
        axis.plot(
            item.thresholds,
            item.values,
            color=item.color,
            label=item.name,
            linewidth=_LINE_WIDTH,
            marker="o",
            markersize=_MARKER_SIZE,
        )


def _label_thresholds(axis: plt.Axes, thresholds: tuple[float, ...]) -> None:
    axis.set_xticks(list(thresholds))
    axis.set_xticklabels([_tick_label(index, value) for index, value in enumerate(thresholds)])


def _tick_label(index: int, value: float) -> str:
    if index % _LABEL_STRIDE == 0:
        return f"{value:.2f}"
    return ""


def _style_axis(axis: plt.Axes, ylabel: str) -> None:
    axis.set_xlim(0, _AXIS_MAX)
    axis.set_ylim(0, _Y_HEADROOM)
    axis.set_yticks(list(_Y_TICKS))
    axis.set_xlabel("Remove threshold")
    axis.set_ylabel(ylabel)
    axis.set_title(ylabel)
    axis.grid(True, axis="y", alpha=0.3)
    axis.legend(loc="upper right", frameon=True)


def _save_figure(figure: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


if __name__ == "__main__":
    main()
