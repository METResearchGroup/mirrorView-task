"""Flesch reading-ease textual feature.

To run:

PYTHONPATH=. uv run python -c "from shared.textual_features.reading_ease import FleschReadingEaseMetric; print(FleschReadingEaseMetric().calculate('Hello world.'))"
"""

from __future__ import annotations

from shared.textual_features.base import CalculateMetric
from shared.textual_features.text_utils import readability_counts, safe_divide

FLESCH_READING_EASE_INTERCEPT = 206.835
FLESCH_READING_EASE_WORDS_PER_SENTENCE_WEIGHT = 1.015
FLESCH_READING_EASE_SYLLABLES_PER_WORD_WEIGHT = 84.6


class FleschReadingEaseMetric(CalculateMetric):
    """Flesch Reading Ease score."""

    @property
    def name(self) -> str:
        return "flesch_reading_ease"

    def describe(self) -> str:
        return (
            "Flesch Reading Ease: 206.835 - 1.015*(words/sentences) - "
            "84.6*(syllables/words), using spaCy sentence and token boundaries."
        )

    def calculate(self, text: str) -> float:
        """Return Flesch reading ease for ``text``.

        Parameters
        ----------
        text
            Input post string.

        Returns
        -------
        float
            Reading-ease score, or 0.0 when there are no alphabetic words.
        """
        words, sentences, syllables = readability_counts(text)
        if words == 0:
            return 0.0
        return float(
            FLESCH_READING_EASE_INTERCEPT
            - FLESCH_READING_EASE_WORDS_PER_SENTENCE_WEIGHT
            * safe_divide(float(words), float(sentences))
            - FLESCH_READING_EASE_SYLLABLES_PER_WORD_WEIGHT
            * safe_divide(float(syllables), float(words))
        )
