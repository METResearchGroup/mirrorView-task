"""Classification metrics for keep/remove Jev baseline evaluation.

Run from the repo root:

    PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_metrics.py -q
"""

from __future__ import annotations

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
    tn: int
    fp: int
    fn: int
    tp: int


@dataclass(frozen=True)
class ClassificationMetrics:
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
    keep_all_f1: float
    remove_all_f1: float
    prevalence_random_f1_mean: float
    prevalence_random_f1_std: float


@dataclass(frozen=True)
class SubgroupMetrics:
    subgroup_name: str
    subgroup_value: str
    metrics: ClassificationMetrics


@dataclass(frozen=True)
class LatencyPercentiles:
    p50_ms: float
    p90_ms: float
    p99_ms: float


@dataclass(frozen=True)
class CostSummary:
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


def subgroup_metrics(
    frame: pd.DataFrame,
    *,
    threshold: float = DEFAULT_THRESHOLD,
) -> list[SubgroupMetrics]:
    """Emit metrics for stance, toxicity, unanimous, and remove_share quartiles."""
    raise NotImplementedError


def spearman_remove_share(
    remove_share: list[float],
    p_remove: list[float],
) -> float:
    """Spearman correlation between human remove vote share and P(remove)."""
    raise NotImplementedError


def latency_summary(
    request_latencies_ms: list[float],
    post_latencies_ms: list[float],
) -> dict[str, LatencyPercentiles]:
    """Keys: request, post."""
    raise NotImplementedError


def build_results_payload(
    *,
    ablation_id: str,
    split_metrics: dict[SplitName, ClassificationMetrics],
    dev_tuned_test_metrics: ClassificationMetrics,
    dev_tuned_threshold: float,
    trivial: TrivialBaselineMetrics,
    subgroups: list[SubgroupMetrics],
    spearman: float,
    latency: dict[str, LatencyPercentiles],
    cost: CostSummary,
    wall_time_s: float,
) -> dict[str, Any]:
    """JSON-serializable dict written to results.json."""
    raise NotImplementedError


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
