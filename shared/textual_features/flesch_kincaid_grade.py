"""Flesch–Kincaid grade textual feature.

To run:

PYTHONPATH=. uv run python -c "from shared.textual_features.flesch_kincaid_grade import FleschKincaidGradeMetric; print(FleschKincaidGradeMetric().calculate('Hello world.'))"
"""

from __future__ import annotations

from shared.textual_features.base import CalculateMetric
from shared.textual_features.text_utils import readability_counts, safe_divide

FLESCH_KINCAID_WORDS_PER_SENTENCE_WEIGHT = 0.39
FLESCH_KINCAID_SYLLABLES_PER_WORD_WEIGHT = 11.8
FLESCH_KINCAID_INTERCEPT = 15.59


class FleschKincaidGradeMetric(CalculateMetric):
    """Flesch–Kincaid Grade Level."""

    @property
    def name(self) -> str:
        return "flesch_kincaid_grade"

    def describe(self) -> str:
        return (
            "Flesch-Kincaid Grade Level: 0.39*(words/sentences) + "
            "11.8*(syllables/words) - 15.59, using spaCy sentence and token boundaries."
        )

    def calculate(self, text: str) -> float:
        """Return Flesch–Kincaid grade for ``text``.

        Parameters
        ----------
        text
            Input post string.

        Returns
        -------
        float
            Grade level, or 0.0 when there are no alphabetic words.
        """
        words, sentences, syllables = readability_counts(text)
        if words == 0:
            return 0.0
        return float(
            FLESCH_KINCAID_WORDS_PER_SENTENCE_WEIGHT
            * safe_divide(float(words), float(sentences))
            + FLESCH_KINCAID_SYLLABLES_PER_WORD_WEIGHT
            * safe_divide(float(syllables), float(words))
            - FLESCH_KINCAID_INTERCEPT
        )
