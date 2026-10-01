"""Deterministic Markdown rendering for Study 2 zero-shot analysis tables.

Run from repo root::

    PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step3_analysis.analyze --help
"""

from __future__ import annotations

from experiments.zero_shot_llm_inference_2026_09_30.src.step3_analysis.analyze import (
    AnalysisTables,
)


def render_results_fragment(tables: AnalysisTables) -> str:
    """Render the fixed results fragment from completed analysis tables."""
    return ""
