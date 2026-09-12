"""Scoring helpers for experiments 1 through 4."""

from __future__ import annotations

from dataclasses import dataclass

from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
)

PARTY_GROUPS = ("democrat", "republican")
STANCE_VALUES = ("left", "right")
TOXICITY_VALUES = (
    "sample_low_toxicity",
    "sample_middle_toxicity",
    "sample_high_toxicity",
)


@dataclass(frozen=True)
class MetricBundle:
    """Accuracy, precision, recall, and F1 for one slice."""

    accuracy: float
    precision: float
    recall: float
    f1: float


@dataclass(frozen=True)
class PooledMetricBundle(MetricBundle):
    """Pooled metrics plus baseline remove rate."""

    baseline_remove_rate: float


@dataclass(frozen=True)
class UserScoreRow:
    """One user's gold and predicted labels."""

    prolific_id: str
    party_group: str
    gold: tuple[int, ...]
    pred: tuple[int, ...]


@dataclass(frozen=True)
class TrialScoreRow:
    """One trial's gold and predicted labels."""

    prolific_id: str
    sampled_stance: str
    sample_toxicity_type: str
    gold: int
    pred: int


def user_metrics(gold: list[int], pred: list[int]) -> MetricBundle:
    """Return user-level metrics with remove as the positive class."""
    return MetricBundle(
        accuracy=float(accuracy_score(gold, pred)),
        precision=float(precision_score(gold, pred, zero_division=0)),
        recall=float(recall_score(gold, pred, zero_division=0)),
        f1=float(f1_score(gold, pred, zero_division=0)),
    )


def pooled_metrics(gold: list[int], pred: list[int]) -> PooledMetricBundle:
    """Return pooled metrics plus baseline remove rate."""
    metrics = user_metrics(gold, pred)
    return PooledMetricBundle(
        accuracy=metrics.accuracy,
        precision=metrics.precision,
        recall=metrics.recall,
        f1=metrics.f1,
        baseline_remove_rate=float(sum(gold) / len(gold)),
    )


def slice_tables(
    user_rows: list[UserScoreRow],
    trial_rows: list[TrialScoreRow],
) -> dict[str, dict[str, MetricBundle | PooledMetricBundle]]:
    """Build party, toxicity, and stance metric tables."""
    return {
        "party": _party_table(user_rows),
        "toxicity": _trial_table(trial_rows, "sample_toxicity_type", TOXICITY_VALUES),
        "stance": _trial_table(trial_rows, "sampled_stance", STANCE_VALUES),
    }


def _party_table(user_rows: list[UserScoreRow]) -> dict[str, MetricBundle]:
    table: dict[str, MetricBundle] = {}
    for party in PARTY_GROUPS:
        rows = [row for row in user_rows if row.party_group == party]
        gold = [value for row in rows for value in row.gold]
        pred = [value for row in rows for value in row.pred]
        table[party] = user_metrics(gold, pred) if gold else _zero_metrics()
    return table


def _trial_table(
    trial_rows: list[TrialScoreRow],
    field_name: str,
    values: tuple[str, ...],
) -> dict[str, PooledMetricBundle]:
    table: dict[str, PooledMetricBundle] = {}
    for value in values:
        rows = [row for row in trial_rows if getattr(row, field_name) == value]
        gold = [row.gold for row in rows]
        pred = [row.pred for row in rows]
        table[value] = pooled_metrics(gold, pred) if gold else _zero_pooled_metrics()
    return table


def _zero_metrics() -> MetricBundle:
    return MetricBundle(accuracy=0.0, precision=0.0, recall=0.0, f1=0.0)


def _zero_pooled_metrics() -> PooledMetricBundle:
    return PooledMetricBundle(
        accuracy=0.0,
        precision=0.0,
        recall=0.0,
        f1=0.0,
        baseline_remove_rate=0.0,
    )
