"""Punctuation-count textual feature.

To run:

PYTHONPATH=. uv run python -c "from shared.textual_features.punctuation_count import PunctuationCountMetric; print(PunctuationCountMetric().calculate('Hello world!'))"
"""

from __future__ import annotations

from shared.textual_features.base import CalculateMetric
from shared.textual_features.text_utils import PUNCTUATION_RE


class PunctuationCountMetric(CalculateMetric):
    """Count of punctuation-like characters."""

    @property
    def name(self) -> str:
        return "punctuation_count"

    def describe(self) -> str:
        return (
            "Count of punctuation-like characters: each match of the regex [^\\w\\s] "
            "(not a word character, not whitespace) counts as one punctuation token."
        )

    def calculate(self, text: str) -> float:
        """Return punctuation count for ``text``.

        Parameters
        ----------
        text
            Input post string.

        Returns
        -------
        float
            Number of ``PUNCTUATION_RE`` matches.
        """
        return float(len(PUNCTUATION_RE.findall(text)))
