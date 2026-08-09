"""Punctuation-density textual feature.

To run:

PYTHONPATH=. uv run python -c "from shared.textual_features.punctuation_density import PunctuationDensityMetric; print(PunctuationDensityMetric().calculate('Hello world!'))"
"""

from __future__ import annotations

from shared.textual_features.base import CalculateMetric
from shared.textual_features.text_utils import PUNCTUATION_RE, safe_divide


class PunctuationDensityMetric(CalculateMetric):
    """Punctuation per character."""

    @property
    def name(self) -> str:
        return "punctuation_density"

    def describe(self) -> str:
        return (
            "Punctuation per character: punctuation_count / char_count for the same string, "
            "using the punctuation and character definitions above. 0 if the string has length 0."
        )

    def calculate(self, text: str) -> float:
        """Return punctuation density for ``text``.

        Parameters
        ----------
        text
            Input post string.

        Returns
        -------
        float
            ``punctuation_count / char_count``, or 0.0 for empty text.
        """
        char_count = len(text)
        punct = float(len(PUNCTUATION_RE.findall(text)))
        return safe_divide(punct, float(char_count) if char_count else 0.0)
