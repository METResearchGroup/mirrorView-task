"""Character-count textual feature.

To run:

PYTHONPATH=. uv run python -c "from shared.textual_features.char_count import CharCountMetric; print(CharCountMetric().calculate('Hello world!'))"
"""

from __future__ import annotations

from shared.textual_features.base import CalculateMetric


class CharCountMetric(CalculateMetric):
    """Post length in characters."""

    @property
    def name(self) -> str:
        return "char_count"

    def describe(self) -> str:
        return (
            "Post length in characters. Counts every codepoint in the string after normalization "
            "(including spaces, punctuation, and line breaks). Formula: float(len(text))."
        )

    def calculate(self, text: str) -> float:
        """Return character count for ``text``.

        Parameters
        ----------
        text
            Input post string.

        Returns
        -------
        float
            ``float(len(text))``.
        """
        return float(len(text))
