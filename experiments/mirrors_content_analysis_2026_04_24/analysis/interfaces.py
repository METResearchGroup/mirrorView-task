"""Protocols/interfaces shared by analysis modules.

To run:

PYTHONPATH=. uv run python -c "from experiments.mirrors_content_analysis_2026_04_24.analysis.interfaces import CalculateMetric"
"""

from __future__ import annotations

from shared.textual_features.base import CalculateMetric

__all__ = ["CalculateMetric"]
