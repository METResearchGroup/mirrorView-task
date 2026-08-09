"""Sentence-count textual feature.

To run:

PYTHONPATH=. uv run python -c "from shared.textual_features.sentence_count import SentenceCountMetric; print(SentenceCountMetric().calculate('Hello world!'))"
"""

from __future__ import annotations

from shared.textual_features.base import CalculateMetric
from shared.textual_features.text_utils import SENTENCE_SPLIT_RE


class SentenceCountMetric(CalculateMetric):
    """Sentence count by splitting on ., !, or ?."""

    @property
    def name(self) -> str:
        return "sentence_count"

    def describe(self) -> str:
        return (
            "Sentence count by splitting on one-or-more occurrences of ., !, or ?. "
            "Non-empty trimmed segments after the split are counted; empty runs are ignored."
        )

    def calculate(self, text: str) -> float:
        """Return sentence count for ``text``.

        Parameters
        ----------
        text
            Input post string.

        Returns
        -------
        float
            Number of non-empty segments after sentence-boundary split.
        """
        parts = [part.strip() for part in SENTENCE_SPLIT_RE.split(text) if part.strip()]
        return float(len(parts))
