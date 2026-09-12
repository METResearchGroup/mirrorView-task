"""Scoring helpers for experiments 1 through 4."""

from __future__ import annotations

from dataclasses import dataclass


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
    raise NotImplementedError


def pooled_metrics(gold: list[int], pred: list[int]) -> PooledMetricBundle:
    """Return pooled metrics plus baseline remove rate."""
    raise NotImplementedError


def slice_tables(
    user_rows: list[UserScoreRow],
    trial_rows: list[TrialScoreRow],
) -> dict[str, dict[str, MetricBundle | PooledMetricBundle]]:
    """Build party, toxicity, and stance metric tables."""
    raise NotImplementedError
