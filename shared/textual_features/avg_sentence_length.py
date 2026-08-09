"""Average sentence length textual feature.

To run:

PYTHONPATH=. uv run python -c "from shared.textual_features.avg_sentence_length import AvgSentenceLengthMetric; print(AvgSentenceLengthMetric().calculate('Hello world!'))"
"""

from __future__ import annotations

from shared.textual_features.base import CalculateMetric
from shared.textual_features.text_utils import SENTENCE_SPLIT_RE, WORD_RE, safe_divide


class AvgSentenceLengthMetric(CalculateMetric):
    """Mean words per sentence."""

    @property
    def name(self) -> str:
        return "avg_sentence_length"

    def describe(self) -> str:
        return (
            "Mean words per sentence for this post. Computed as word_count / sentence_count "
            "using the same word and sentence definitions as the separate word and sentence metrics; "
            "0 if sentence_count is 0 (avoids division by zero)."
        )

    def calculate(self, text: str) -> float:
        """Return average sentence length for ``text``.

        Parameters
        ----------
        text
            Input post string.

        Returns
        -------
        float
            ``word_count / sentence_count``, or 0.0 when there are no sentences.
        """
        word_count = float(len(WORD_RE.findall(text)))
        parts = [part.strip() for part in SENTENCE_SPLIT_RE.split(text) if part.strip()]
        sentence_count = float(len(parts))
        return safe_divide(word_count, sentence_count)
