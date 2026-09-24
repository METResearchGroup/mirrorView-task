"""Classification metrics for keep/remove Jev baseline evaluation.

Run from the repo root:

    PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_metrics.py -q
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Literal

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared import latency

SplitName = Literal["test", "dev", "gepa_pool", "full"]

DEFAULT_THRESHOLD = 0.5
DEFAULT_THRESHOLD_GRID = [round(value, 2) for value in np.arange(0.05, 1.0, 0.05)]
PREVALENCE_RANDOM_SEED = 20260924
PREVALENCE_RANDOM_DRAWS = 100


@dataclass(frozen=True)
class ConfusionCounts:
    """Confusion matrix cell counts for binary keep/remove classification."""

    tn: int
    fp: int
    fn: int
    tp: int


@dataclass(frozen=True)
class ClassificationMetrics:
    """Classification summary with threshold, confusion counts, and sample size."""

    accuracy: float
    precision: float
    recall: float
    f1: float
    balanced_accuracy: float
    roc_auc: float
    pr_auc: float
    confusion: ConfusionCounts
    threshold: float
    n: int


@dataclass(frozen=True)
class TrivialBaselineMetrics:
    """F1 scores for keep-all, remove-all, and prevalence-random baselines."""

    keep_all_f1: float
    remove_all_f1: float
    prevalence_random_f1_mean: float
    prevalence_random_f1_std: float


@dataclass(frozen=True)
class SubgroupMetrics:
    """Classification metrics for one named subgroup slice."""

    subgroup_name: str
    subgroup_value: str
    metrics: ClassificationMetrics


@dataclass(frozen=True)
class LatencyPercentiles:
    """Request or per-post latency percentiles in milliseconds."""

    p50_ms: float
    p90_ms: float
    p99_ms: float


@dataclass(frozen=True)
class CostSummary:
    """Aggregated token usage and estimated USD cost."""

    input_tokens: int
    output_tokens: int
    cost_usd: float


def _confusion_counts(y_true: list[int], y_pred: list[int]) -> ConfusionCounts:
    matrix = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = matrix.ravel().tolist()
    return ConfusionCounts(tn=int(tn), fp=int(fp), fn=int(fn), tp=int(tp))


def _maybe_metric(metric_fn: Any) -> float:
    try:
        return float(metric_fn())
    except ValueError:
        return float("nan")


def hard_label_metrics(
    y_true: list[int],
    y_pred: list[int],
    *,
    threshold: float = DEFAULT_THRESHOLD,
) -> ClassificationMetrics:
    """F1, accuracy, precision, recall with positive class remove."""
    y_true_arr = [int(value) for value in y_true]
    y_pred_arr = [int(value) for value in y_pred]
    confusion = _confusion_counts(y_true_arr, y_pred_arr)
    return ClassificationMetrics(
        accuracy=float(accuracy_score(y_true_arr, y_pred_arr)),
        precision=float(precision_score(y_true_arr, y_pred_arr, zero_division=0)),
        recall=float(recall_score(y_true_arr, y_pred_arr, zero_division=0)),
        f1=float(f1_score(y_true_arr, y_pred_arr, zero_division=0)),
        balanced_accuracy=float(balanced_accuracy_score(y_true_arr, y_pred_arr)),
        roc_auc=float("nan"),
        pr_auc=float("nan"),
        confusion=confusion,
        threshold=threshold,
        n=len(y_true_arr),
    )


def probability_metrics(
    y_true: list[int],
    p_remove: list[float],
    *,
    threshold: float = DEFAULT_THRESHOLD,
) -> ClassificationMetrics:
    """Derive y_pred from p_remove and threshold; compute full classification metrics."""
    y_true_arr = [int(value) for value in y_true]
    scores = [float(value) for value in p_remove]
    y_pred_arr = [1 if score >= threshold else 0 for score in scores]
    confusion = _confusion_counts(y_true_arr, y_pred_arr)
    return ClassificationMetrics(
        accuracy=float(accuracy_score(y_true_arr, y_pred_arr)),
        precision=float(precision_score(y_true_arr, y_pred_arr, zero_division=0)),
        recall=float(recall_score(y_true_arr, y_pred_arr, zero_division=0)),
        f1=float(f1_score(y_true_arr, y_pred_arr, zero_division=0)),
        balanced_accuracy=float(balanced_accuracy_score(y_true_arr, y_pred_arr)),
        roc_auc=_maybe_metric(lambda: roc_auc_score(y_true_arr, scores)),
        pr_auc=_maybe_metric(lambda: average_precision_score(y_true_arr, scores)),
        confusion=confusion,
        threshold=threshold,
        n=len(y_true_arr),
    )


def tune_threshold_for_f1(
    y_true: list[int],
    p_remove: list[float],
    *,
    grid: list[float] | None = None,
) -> tuple[float, float]:
    """Return (best_threshold, best_f1)."""
    thresholds = grid if grid is not None else DEFAULT_THRESHOLD_GRID
    best_threshold = thresholds[0]
    best_f1 = -1.0
    for threshold in thresholds:
        metrics = probability_metrics(y_true, p_remove, threshold=threshold)
        if metrics.f1 > best_f1:
            best_f1 = metrics.f1
            best_threshold = threshold
    return best_threshold, best_f1


def trivial_baselines(
    y_true: list[int],
    *,
    prevalence_random_seed: int = PREVALENCE_RANDOM_SEED,
    prevalence_random_draws: int = PREVALENCE_RANDOM_DRAWS,
) -> TrivialBaselineMetrics:
    """keep-all, remove-all, prevalence-random F1 baselines."""
    y_true_arr = [int(value) for value in y_true]
    keep_all = hard_label_metrics(y_true_arr, [0] * len(y_true_arr))
    remove_all = hard_label_metrics(y_true_arr, [1] * len(y_true_arr))
    prevalence = sum(y_true_arr) / len(y_true_arr) if y_true_arr else 0.0
    rng = np.random.default_rng(prevalence_random_seed)
    random_f1_scores: list[float] = []
    for _ in range(prevalence_random_draws):
        random_preds = (rng.random(len(y_true_arr)) < prevalence).astype(int).tolist()
        random_f1_scores.append(
            f1_score(y_true_arr, random_preds, zero_division=0)
        )
    return TrivialBaselineMetrics(
        keep_all_f1=keep_all.f1,
        remove_all_f1=remove_all.f1,
        prevalence_random_f1_mean=float(np.mean(random_f1_scores)),
        prevalence_random_f1_std=float(np.std(random_f1_scores)),
    )


def _metrics_for_frame(
    frame: pd.DataFrame,
    *,
    threshold: float,
) -> ClassificationMetrics:
    return probability_metrics(
        frame["keep_remove_label"].astype(int).tolist(),
        frame["p_remove"].astype(float).tolist(),
        threshold=threshold,
    )


def _append_subgroup_rows(
    rows: list[SubgroupMetrics],
    frame: pd.DataFrame,
    subgroup_name: str,
    column: str,
    *,
    threshold: float,
) -> None:
    for value in sorted(frame[column].dropna().unique()):
        subset = frame.loc[frame[column] == value]
        if subset.empty:
            continue
        rows.append(
            SubgroupMetrics(
                subgroup_name=subgroup_name,
                subgroup_value=str(value),
                metrics=_metrics_for_frame(subset, threshold=threshold),
            )
        )


def subgroup_metrics(
    frame: pd.DataFrame,
    *,
    threshold: float = DEFAULT_THRESHOLD,
) -> list[SubgroupMetrics]:
    """Emit metrics for stance, toxicity, unanimous, and remove_share quartiles."""
    rows: list[SubgroupMetrics] = []
    working = frame.copy()
    _append_subgroup_rows(rows, working, "stance", "sampled_stance", threshold=threshold)
    _append_subgroup_rows(rows, working, "toxicity", "sample_toxicity_type", threshold=threshold)
    working["unanimous_label"] = working["is_unanimous"].map(
        {True: "unanimous", False: "non_unanimous"}
    )
    _append_subgroup_rows(rows, working, "unanimous", "unanimous_label", threshold=threshold)
    quartile_labels = pd.qcut(
        working["remove_share"].astype(float),
        q=4,
        duplicates="drop",
    )
    working = working.assign(remove_share_quartile=quartile_labels.astype(str))
    _append_subgroup_rows(
        rows,
        working,
        "remove_share_quartile",
        "remove_share_quartile",
        threshold=threshold,
    )
    return rows


def union_cohort_subgroups(
    frame: pd.DataFrame,
    *,
    threshold: float = DEFAULT_THRESHOLD,
) -> list[SubgroupMetrics]:
    """Emit union-only subgroup slices for study-part coverage and Part 3 overlap."""
    rows: list[SubgroupMetrics] = []
    working = frame.copy()
    if "study_part_coverage" in working.columns:
        _append_subgroup_rows(
            rows,
            working,
            "study_part_coverage",
            "study_part_coverage",
            threshold=threshold,
        )
    if "in_part3_cohort_a" in working.columns:
        working["in_part3_cohort_a_label"] = working["in_part3_cohort_a"].map(
            {True: "true", False: "false"}
        )
        _append_subgroup_rows(
            rows,
            working,
            "in_part3_cohort_a",
            "in_part3_cohort_a_label",
            threshold=threshold,
        )
    if "label_changed_vs_part3" in working.columns:
        working["label_changed_vs_part3_label"] = working["label_changed_vs_part3"].map(
            {True: "true", False: "false"}
        )
        _append_subgroup_rows(
            rows,
            working,
            "label_changed_vs_part3",
            "label_changed_vs_part3_label",
            threshold=threshold,
        )
    return rows


def spearman_remove_share(
    remove_share: list[float],
    p_remove: list[float],
) -> float:
    """Spearman correlation between human remove vote share and P(remove)."""
    if len(remove_share) < 2 or len(p_remove) < 2:
        return float("nan")
    if len(set(remove_share)) < 2 or len(set(p_remove)) < 2:
        return float("nan")
    result = spearmanr(remove_share, p_remove)
    correlation = result.correlation
    if correlation is None or math.isnan(correlation):
        return float("nan")
    return float(correlation)


def latency_summary(
    request_latencies_ms: list[float],
    post_latencies_ms: list[float],
) -> dict[str, LatencyPercentiles]:
    """Keys: request, post."""
    return {
        "request": LatencyPercentiles(
            p50_ms=latency.percentile_ms(request_latencies_ms, 0.5),
            p90_ms=latency.percentile_ms(request_latencies_ms, 0.9),
            p99_ms=latency.percentile_ms(request_latencies_ms, 0.99),
        ),
        "post": LatencyPercentiles(
            p50_ms=latency.percentile_ms(post_latencies_ms, 0.5),
            p90_ms=latency.percentile_ms(post_latencies_ms, 0.9),
            p99_ms=latency.percentile_ms(post_latencies_ms, 0.99),
        ),
    }


def build_results_payload(
    *,
    ablation_id: str,
    split_metrics: dict[SplitName, ClassificationMetrics],
    dev_tuned_test_metrics: ClassificationMetrics | None,
    dev_tuned_threshold: float,
    trivial: TrivialBaselineMetrics,
    subgroups: list[SubgroupMetrics],
    spearman: float,
    latency: dict[str, LatencyPercentiles],
    cost: CostSummary,
    wall_time_s: float,
) -> dict[str, Any]:
    """JSON-serializable dict written to results.json."""
    return {
        "ablation_id": ablation_id,
        "headline_split": "test",
        "secondary_split": "full",
        "metrics_at_0_5": {
            split_name: _classification_metrics_to_dict(metrics)
            for split_name, metrics in split_metrics.items()
            if split_name in {"test", "full"}
        },
        "split_metrics": {
            split_name: _classification_metrics_to_dict(metrics)
            for split_name, metrics in split_metrics.items()
        },
        "dev_tuned_threshold": dev_tuned_threshold,
        "dev_tuned_test_metrics": (
            None
            if dev_tuned_test_metrics is None
            else _classification_metrics_to_dict(dev_tuned_test_metrics)
        ),
        "trivial_baselines": _trivial_baselines_to_dict(trivial),
        "subgroups": _subgroup_metrics_to_dict(subgroups),
        "spearman_remove_share": spearman,
        "latency": _latency_to_dict(latency),
        "cost": _cost_to_dict(cost),
        "wall_time_s": wall_time_s,
    }


def _classification_metrics_to_dict(metrics: ClassificationMetrics) -> dict[str, Any]:
    payload = asdict(metrics)
    payload["confusion"] = asdict(metrics.confusion)
    return payload


def _trivial_baselines_to_dict(trivial: TrivialBaselineMetrics) -> dict[str, float]:
    return asdict(trivial)


def _subgroup_metrics_to_dict(subgroups: list[SubgroupMetrics]) -> list[dict[str, Any]]:
    return [
        {
            "subgroup_name": subgroup.subgroup_name,
            "subgroup_value": subgroup.subgroup_value,
            "metrics": _classification_metrics_to_dict(subgroup.metrics),
        }
        for subgroup in subgroups
    ]


def _latency_to_dict(latency_payload: dict[str, LatencyPercentiles]) -> dict[str, dict[str, float]]:
    return {key: asdict(value) for key, value in latency_payload.items()}


def _cost_to_dict(cost: CostSummary) -> dict[str, float | int]:
    return asdict(cost)
