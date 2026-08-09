"""Readability metrics (thin re-exports from shared).

To run:

PYTHONPATH=. uv run python -c "from experiments.mirrors_content_analysis_2026_04_24.analysis.readability_complexity_analysis.metrics import DEFAULT_READABILITY_METRICS"
"""

from __future__ import annotations

from shared.textual_features.base import CalculateMetric
from shared.textual_features.flesch_kincaid_grade import FleschKincaidGradeMetric
from shared.textual_features.reading_ease import FleschReadingEaseMetric

DEFAULT_READABILITY_METRICS: tuple[CalculateMetric, ...] = (
    FleschKincaidGradeMetric(),
    FleschReadingEaseMetric(),
)

__all__ = [
    "CalculateMetric",
    "DEFAULT_READABILITY_METRICS",
    "FleschKincaidGradeMetric",
    "FleschReadingEaseMetric",
]
