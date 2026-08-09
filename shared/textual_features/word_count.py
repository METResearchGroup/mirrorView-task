"""Word-count textual feature.

To run:

PYTHONPATH=. uv run python -c "from shared.textual_features.word_count import WordCountMetric; print(WordCountMetric().calculate('Hello world!'))"
"""

from __future__ import annotations

from shared.textual_features.base import CalculateMetric
from shared.textual_features.text_utils import WORD_RE


class WordCountMetric(CalculateMetric):
    """Approximate word count via regex tokenization."""

    @property
    def name(self) -> str:
        return "word_count"

    def describe(self) -> str:
        return (
            "Approximate word count via regex tokenization: count how many times the pattern "
            r"\b\w+\b matches (word characters bounded by word boundaries). "
            "Same notion as many simple NLP word counts; not full Unicode word segmentation."
        )

    def calculate(self, text: str) -> float:
        """Return word count for ``text``.

        Parameters
        ----------
        text
            Input post string.

        Returns
        -------
        float
            Number of ``WORD_RE`` matches.
        """
        return float(len(WORD_RE.findall(text)))
