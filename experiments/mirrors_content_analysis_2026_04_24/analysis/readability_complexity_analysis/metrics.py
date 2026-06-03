from __future__ import annotations

import re
from functools import lru_cache

import spacy

from experiments.mirrors_content_analysis_2026_04_24.analysis.analysis_utils import safe_divide
from experiments.mirrors_content_analysis_2026_04_24.analysis.interfaces import CalculateMetric

VOWEL_GROUP_RE = re.compile(r"[aeiouy]+", re.IGNORECASE)
NON_LETTER_RE = re.compile(r"[^a-z]")


@lru_cache(maxsize=1)
def _nlp() -> spacy.language.Language:
    """Minimal English pipeline for deterministic token/sentence boundaries."""
    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")
    return nlp


def _count_syllables(word: str) -> int:
    w = NON_LETTER_RE.sub("", word.lower())
    if not w:
        return 0
    groups = VOWEL_GROUP_RE.findall(w)
    syllables = len(groups)
    if w.endswith("e") and syllables > 1:
        syllables -= 1
    return max(1, syllables)


def _readability_counts(text: str) -> tuple[int, int, int]:
    doc = _nlp()(text)
    words = [token.text for token in doc if token.is_alpha]
    sentence_count = sum(1 for sent in doc.sents if sent.text.strip())
    if sentence_count == 0:
        sentence_count = 1
    word_count = len(words)
    syllable_count = sum(_count_syllables(word) for word in words)
    return word_count, sentence_count, syllable_count


class FleschKincaidGradeMetric(CalculateMetric):
    @property
    def name(self) -> str:
        return "flesch_kincaid_grade"

    def describe(self) -> str:
        return (
            "Flesch-Kincaid Grade Level: 0.39*(words/sentences) + "
            "11.8*(syllables/words) - 15.59, using spaCy sentence and token boundaries."
        )

    def calculate(self, text: str) -> float:
        words, sentences, syllables = _readability_counts(text)
        if words == 0:
            return 0.0
        return float(
            0.39 * safe_divide(float(words), float(sentences))
            + 11.8 * safe_divide(float(syllables), float(words))
            - 15.59
        )


class FleschReadingEaseMetric(CalculateMetric):
    @property
    def name(self) -> str:
        return "flesch_reading_ease"

    def describe(self) -> str:
        return (
            "Flesch Reading Ease: 206.835 - 1.015*(words/sentences) - "
            "84.6*(syllables/words), using spaCy sentence and token boundaries."
        )

    def calculate(self, text: str) -> float:
        words, sentences, syllables = _readability_counts(text)
        if words == 0:
            return 0.0
        return float(
            206.835
            - 1.015 * safe_divide(float(words), float(sentences))
            - 84.6 * safe_divide(float(syllables), float(words))
        )


DEFAULT_READABILITY_METRICS: tuple[CalculateMetric, ...] = (
    FleschKincaidGradeMetric(),
    FleschReadingEaseMetric(),
)
